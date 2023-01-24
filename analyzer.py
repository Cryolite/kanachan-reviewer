#!/usr/bin/env python3

import datetime
import logging
import json
from kanachan_reviewer.config import get_config
from kanachan_reviewer.redis import Redis
import kanachan_reviewer.logging as logging_
from kanachan_reviewer.mahjongsoul_pb2 import Wrapper, ResGameRecord


_CONFIG = get_config()


_REDIS_HOST = _CONFIG['redis']['host']
assert isinstance(_REDIS_HOST, str)
_REDIS_PORT = _CONFIG['redis']['port']
assert isinstance(_REDIS_PORT, int)
_REDIS = Redis(_REDIS_HOST, _REDIS_PORT)


def _analyze(game_record: ResGameRecord) -> object:
    return {}


def _main() -> None:
    process_rank = _REDIS.postincr('analyzer-process-rank')
    logging_.initialize('analyzer', process_rank, _REDIS, _CONFIG)

    while True:
        wrapped_data = _REDIS.blpop('game-records')
        assert isinstance(wrapped_data, bytes)
        wrapper = Wrapper()
        wrapper.ParseFromString(wrapped_data[3:])
        assert wrapper.name == '' # pylint: disable=no-member

        game_record = ResGameRecord()
        game_record.ParseFromString(wrapper.data) # pylint: disable=no-member
        assert game_record.error.code == 0 # pylint: disable=no-member
        uuid = game_record.head.uuid # pylint: disable=no-member
        logging.info('%s: A game record arrived.', uuid)

        review = _analyze(game_record)
        review_with_timestamp = {
            'error_code': 0,
            'review': review,
            'timestamp': int(datetime.datetime.now(datetime.timezone.utc).timestamp())
        }
        review_with_timestamp_json = json.dumps(review_with_timestamp)
        _REDIS.hsetnx('reviews', uuid, review_with_timestamp_json)
        logging.info('%s: Completed the review.', uuid)


if __name__ == '__main__':
    while True:
        try:
            _main()
        except: # pylint: disable=bare-except
            logging.exception('Abort with an exception.')
