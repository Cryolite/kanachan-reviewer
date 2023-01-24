#!/usr/bin/env python3

from pathlib import Path
import logging
from logging.handlers import RotatingFileHandler
from typing import Optional, List, Dict
import sys
from kanachan_reviewer.config import Config
from kanachan_reviewer.redis import Redis
from kanachan_reviewer.redis_log_handler import RedisLogHandler


_INITIALIZED = False


def initialize(service_name: str, process_rank: Optional[int], redis: Redis, config: Config) -> None:
    global _INITIALIZED # pylint: disable=global-statement
    if _INITIALIZED:
        return

    if service_name not in config:
        _INITIALIZED = True # type: ignore
        return
    ServiceConfig = Dict[str, Dict[str, str | Dict[str, str | int]]]
    service_config: ServiceConfig = config[service_name] # type: ignore
    service_logging_config = service_config['logging']

    handlers: List[logging.Handler] = []

    console_handler = logging.StreamHandler(sys.stdout)
    handlers.append(console_handler)

    if 'file' in service_logging_config:
        log_file_config: Dict[str, str | int] = service_logging_config['file'] # type: ignore
        log_file_path_str = log_file_config['path']
        assert isinstance(log_file_path_str, str)
        if process_rank is None:
            log_file_path_str = log_file_path_str.format('')
        else:
            log_file_path_str = log_file_path_str.format(f'.{process_rank}')
        log_file_path = Path(log_file_path_str)
        log_file_path.parent.mkdir(parents=True, exist_ok=True)
        if log_file_path.exists() and not log_file_path.is_file():
            raise RuntimeError(f'{log_file_path}: Not a file.')

        log_file_max_bytes = log_file_config['max_bytes']
        assert isinstance(log_file_max_bytes, int)
        log_file_backup_count = log_file_config['backup_count']
        assert isinstance(log_file_backup_count, int)

        file_handler = RotatingFileHandler(
            log_file_path, maxBytes=log_file_max_bytes,
            backupCount=log_file_backup_count, delay=True)
        handlers.append(file_handler)

    if 'redis' in service_logging_config:
        redis_logging_config: Dict[str, str | int] = service_logging_config['redis'] # type: ignore
        redis_logging_key = redis_logging_config['key']
        assert isinstance(redis_logging_key, str)
        redis_logging_max_entries = redis_logging_config['max_entries']
        assert isinstance(redis_logging_max_entries, int)
        redis_handler = RedisLogHandler(redis, redis_logging_key, redis_logging_max_entries)
        handlers.append(redis_handler)

    log_format = '%(asctime)s:%(filename)s:%(funcName)s:%(lineno)d:%(levelname)s: %(message)s'
    level = service_logging_config['level']
    assert isinstance(level, str)
    logging.basicConfig(format=log_format, level=level, handlers=handlers)

    _INITIALIZED = True # type: ignore
