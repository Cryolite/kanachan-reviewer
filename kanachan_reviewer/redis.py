#!/usr/bin/env python3

from types import NoneType
from typing import Union, Optional, List, Dict
import redis


class Redis(object):
    def __init__(self, host: str, port: int) -> None:
        self.__redis = redis.StrictRedis(host, port)

    def postincr(self, name: str) -> int:
        result = int(self.__redis.incr(name)) # type: ignore
        assert result >= 1
        return result - 1

    def rpush(self, name: str, value: Union[str, bytes, memoryview]) -> int:
        if isinstance(value, str):
            value = value.encode('UTF-8')
        result = self.__redis.rpush(name, value)
        assert isinstance(result, int)
        return result

    def lpop(self, name: str) -> Optional[bytes]:
        result = self.__redis.lpop(name) # type: ignore
        assert isinstance(result, (bytes, NoneType))
        return result

    def blpop(self, name: str, timeout: int=0) -> Optional[bytes]:
        result: List[bytes | None] = self.__redis.blpop([name], timeout) # type: ignore
        if len(result) not in (1, 2):
            raise RuntimeError(f'{str(result)}: Failed to execute `blpop`.')
        if len(result) == 1:
            assert result[0] is None
            return None
        if result[0] != name.encode('UTF-8'):
            raise RuntimeError(f'{result[0]} != {name.encode("UTF-8")}')
        return result[1]

    def llen(self, name: str) -> int:
        result = self.__redis.llen(name)
        assert isinstance(result, int)
        return result

    def hset(self, name: str, key: str, value: Union[str, bytes, memoryview]) -> None:
        if isinstance(value, str):
            value = value.encode('UTF-8')
        result = self.__redis.hset(name, key, value) # type: ignore
        assert isinstance(result, int)
        assert result == 1

    def hsetnx(self, name: str, key: str, value: Union[str, bytes, memoryview]) -> bool:
        if isinstance(value, str):
            value = value.encode('UTF-8')
        result: int = self.__redis.hsetnx(name, key, value) # type: ignore
        return result == 1

    def hget(self, name: str, key: str) -> Optional[bytes]:
        result = self.__redis.hget(name, key)
        assert isinstance(result, (bytes, NoneType))
        return result

    def hgetall(self, name: str) -> Dict[str, bytes]:
        results: Dict[str, bytes] = self.__redis.hgetall(name) # type: ignore
        for key, value in results.items():
            assert isinstance(key, str)
            assert isinstance(value, bytes)
        return results
