#!/usr/bin/env python3

import re
import datetime
import logging
from logging.handlers import RotatingFileHandler
import json
from typing import (NoReturn, Dict, Union,)
import wsproto.frame_protocol
from mitmproxy.http import HTTPFlow
from kanachan_reviewer.config import get_config
from kanachan_reviewer.redis import Redis
from kanachan_reviewer.redis_log_handler import RedisLogHandler
from kanachan_reviewer.mahjongsoul_pb2 import Wrapper, ReqGameRecord, ResGameRecord


_CONFIG = get_config()


_REDIS_HOST = _CONFIG['redis']['host']
assert isinstance(_REDIS_HOST, str)
_REDIS_PORT = _CONFIG['redis']['port']
assert isinstance(_REDIS_PORT, int)
_REDIS = Redis(_REDIS_HOST, _REDIS_PORT)


_LOGGER = logging.Logger('sniffer')
if 'sniffer' in _CONFIG:
    _LOG_CONFIG = _CONFIG['sniffer']['logging']
    assert isinstance(_LOG_CONFIG, dict)
    if 'file' in _LOG_CONFIG:
        _FILE_LOG_CONFIG = _LOG_CONFIG['file']
        assert isinstance(_FILE_LOG_CONFIG, dict)
        _FILE_LOG_PATH = _FILE_LOG_CONFIG['path']
        assert isinstance(_FILE_LOG_PATH, str)
        _FILE_LOG_MAX_BYTES = _FILE_LOG_CONFIG['max_bytes']
        assert isinstance(_FILE_LOG_MAX_BYTES, int)
        _FILE_LOG_BACKUP_COUNT = _FILE_LOG_CONFIG['backup_count']
        assert isinstance(_FILE_LOG_BACKUP_COUNT, int)
        _FILE_LOG_HANDLER = RotatingFileHandler(
            _FILE_LOG_PATH, maxBytes=_FILE_LOG_MAX_BYTES, backupCount=_FILE_LOG_BACKUP_COUNT,
            encoding='UTF-8', delay=True)
        _LOGGER.addHandler(_FILE_LOG_HANDLER)
    if 'redis' in _LOG_CONFIG:
        _REDIS_LOG_CONFIG = _LOG_CONFIG['redis']
        assert isinstance(_REDIS_LOG_CONFIG, dict)
        _REDIS_LOG_KEY = _REDIS_LOG_CONFIG['key']
        assert isinstance(_REDIS_LOG_KEY, str)
        _REDIS_LOG_MAX_ENTRIES = _REDIS_LOG_CONFIG['max_entries']
        assert isinstance(_REDIS_LOG_MAX_ENTRIES, int)
        _REDIS_LOG_HANDLER = RedisLogHandler(_REDIS, _REDIS_LOG_KEY, _REDIS_LOG_MAX_ENTRIES)
        _LOGGER.addHandler(_REDIS_LOG_HANDLER)
    _LOG_LEVEL = _LOG_CONFIG['level']
    assert isinstance(_LOG_LEVEL, str)
    _LOGGER.setLevel(_LOG_LEVEL)


_WebsocketMessage = Dict[str, Union[str, bytes]]
_WEBSOCKET_MESSAGE_QUEUE: Dict[int, _WebsocketMessage] = {}


def _logging_info(message: str, *args: object) -> None:
    logging.info(message, *args)
    _LOGGER.info(message, *args)


def _logging_warning(message: str, *args: object) -> None:
    logging.warning(message, *args)
    _LOGGER.warning(message, *args)


def _logging_error(message: str, *args: object) -> None:
    logging.error(message, *args)
    _LOGGER.error(message, *args)


def _logging_exception(message: str, *args: object) -> None:
    logging.exception(message, *args)
    _LOGGER.exception(message, *args)


def _raise_error(message: str) -> NoReturn:
    _logging_error(message)
    raise RuntimeError(message)


def _websocket_message(flow: HTTPFlow) -> None:
    if flow.request.url not in ('https://mjjpgs.mahjongsoul.com:9663/',):
        return

    if flow.websocket is None:
        _raise_error('`flow.websocket` is None.')
    if len(flow.websocket.messages) == 0:
        _raise_error('`len(flow.websocket.messages)` == 0')
    message = flow.websocket.messages[-1]

    if message.type != wsproto.frame_protocol.Opcode.BINARY:
        _raise_error(f'{message.type}: An unsupported WebSocket message type.')

    if message.from_client:
        direction = 'outbound'
    else:
        direction = 'inbound'

    content = message.content

    match = re.search(b'^(?:\x01|\x02..)\n.(.*?)\x12', content, flags=re.DOTALL)
    if match is not None:
        type_ = content[0]
        assert type_ in [1, 2]

        number = None
        if type_ == 2:
            number = int.from_bytes(content[1:3], byteorder='little')

        name = match.group(1).decode('UTF-8')

        if type_ == 2:
            # Handle a request message that expects a response message.
            # Enqueue the message until the corresponding responce message arrives.
            assert isinstance(number, int)
            if number in _WEBSOCKET_MESSAGE_QUEUE:
                prev_request = _WEBSOCKET_MESSAGE_QUEUE[number]
                _logging_warning(
'''There is not any response message for the following WebSocket request message:
  direction: %s
  content: %s''', prev_request['direction'], prev_request['request'])

            _WEBSOCKET_MESSAGE_QUEUE[number] = {
                'direction': direction,
                'name': name,
                'request': content
            }

        return

    # Handle a response message.
    # Search the corresponding request message in the queue.
    match = re.search(b'^\x03..\n\x00\x12', content, flags=re.DOTALL)
    if match is None:
        _raise_error(
            f'''An unknown WebSocket message:
  direction: {direction}
  content: {content}''')

    number = int.from_bytes(content[1:3], byteorder='little')
    if number not in _WEBSOCKET_MESSAGE_QUEUE:
        _raise_error(
            f'''An WebSocket response message that does not match to any request message:
  direction: {direction}
  content: {content}''')

    request_direction = _WEBSOCKET_MESSAGE_QUEUE[number]['direction']
    name = _WEBSOCKET_MESSAGE_QUEUE[number]['name']
    request_binary = _WEBSOCKET_MESSAGE_QUEUE[number]['request']
    assert isinstance(request_binary, bytes)
    del _WEBSOCKET_MESSAGE_QUEUE[number]

    if request_direction == 'inbound':
        if direction == 'inbound':
            _raise_error('Both request and response WebSocket messages are inbound.')
        assert direction == 'outbound'
    else:
        assert request_direction == 'outbound'
        if direction == 'outbound':
            _raise_error('Both request and response WebSocket messages are outbound.')
        assert direction == 'inbound'

    if request_direction == 'outbound' and name == '.lq.Lobby.fetchGameRecord':
        wrapper = Wrapper()
        wrapper.ParseFromString(content[3:])
        if wrapper.name != '': # pylint: disable=no-member
            _logging_error('An invalid message.')
            return

        game_record = ResGameRecord()
        game_record.ParseFromString(wrapper.data) # pylint: disable=no-member
        error_code = game_record.error.code # pylint: disable=no-member
        if error_code != 0:
            wrapper.ParseFromString(request_binary[3:])
            assert wrapper.name == name # pylint: disable=no-member

            request = ReqGameRecord()
            request.ParseFromString(wrapper.data) # pylint: disable=no-member
            uuid = request.game_uuid # pylint: disable=no-member

            timestamp = str(int(datetime.datetime.now(datetime.timezone.utc).timestamp()))
            review = {
                'error_code': error_code,
                'timestamp': timestamp
            }
            review_json = json.dumps(review, separators=(',', ':'))
            _REDIS.hset('reviews', uuid, review_json)

            return
        uuid = game_record.head.uuid # pylint: disable=no-member

        _REDIS.rpush('game-records', content)
        _logging_info('%s: Sniffered.', uuid)

        return

    if request_direction == 'outbound' and name == '.lq.Lobby.readGameRecord':
        wrapper = Wrapper()
        wrapper.ParseFromString(request_binary[3:])
        assert wrapper.name == '.lq.Lobby.readGameRecord' # pylint: disable=no-member

        request = ReqGameRecord()
        request.ParseFromString(wrapper.data) # pylint: disable=no-member
        uuid = request.game_uuid # pylint: disable=no-member

        timestamp = str(int(datetime.datetime.now(datetime.timezone.utc).timestamp()))
        _REDIS.hset('game-record-fetched', uuid, timestamp)

        return


def websocket_message(flow: HTTPFlow) -> None:
    try:
        _websocket_message(flow)
    except: # pylint: disable=bare-except
        _logging_exception('Abort with an exception.')
