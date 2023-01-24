#!/usr/bin/env python3

import logging
from kanachan_reviewer.redis import Redis


class RedisLogHandler(logging.Handler):
    def __init__(self, redis: Redis, key: str, max_entries: int) -> None:
        super().__init__()

        self.__redis = redis
        self.__key = key
        self.__max_entries = max_entries

    def emit(self, record: logging.LogRecord) -> None:
        message = super().format(record)
        self.__redis.rpush(self.__key, message)

        if self.__max_entries == 0:
            return

        while self.__redis.llen(self.__key) > self.__max_entries:
            self.__redis.lpop(self.__key)
