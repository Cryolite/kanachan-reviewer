#!/usr/bin/env python3

from typing import Optional, List, Dict
import yaml
import jsonschema


_REDIS_CONFIG_SHCEMA = {
    'type': 'object',
    'properties': {
        'host': {
            'type': 'string'
        },
        'port': {
            'type': 'integer',
            'minimum': 1,
            'maximum': 65535
        }
    },
    'additionalProperties': False
}

_S3_CONFIG_SCHEMA = {
    'type': 'object',
    'required': [
        'bucket_name',
        'authentication_email_key_prefix'
    ],
    'properties': {
        'bucket_name': {
            'type': 'string'
        },
        'authentication_email_key_prefix': {
            'type': 'string'
        }
    },
    'additionalProperties': False
}

_YOSTAR_LOGIN_CONFIG_SCHEMA = {
    'type': 'object',
    'required': [
        'email_addresses'
    ],
    'properties': {
        'email_addresses': {
            'oneOf': [
                {
                    'type': 'string'
                },
                {
                    'type': 'array',
                    'items': {
                        'type': 'string'
                    },
                    'minItems': 1,
                    'uniqueItems': True
                }
            ]
        }
    },
    'additionalProperties': False
}

_LOGGING_TO_FILE_CONFIG_SCHEMA = {
    'type': 'object',
    'required': [
        'path'
    ],
    'properties': {
        'path': {
            'type': 'string'
        },
        'max_bytes': {
            'type': 'integer',
            'minimum': 0
        },
        'backup_count': {
            'type': 'integer',
            'minimum': 0
        }
    },
    'additionalProperties': False
}

_LOGGING_TO_REDIS_CONFIG_SCHEMA = {
    'type': 'object',
    'required': [
        'key'
    ],
    'properties': {
        'key': {
            'type': 'string'
        },
        'max_entries': {
            'type': 'integer',
            'minimum': 0
        }
    },
    'additionalProperties': False
}

_LOGGING_CONFIG_SCHEMA = {
    'type': 'object',
    'properties': {
        'level': {
            'enum': [
                'DEBUG',
                'INFO',
                'WARNING',
                'ERROR',
                'CRITICAL'
            ]
        },
        'file': _LOGGING_TO_FILE_CONFIG_SCHEMA,
        'redis': _LOGGING_TO_REDIS_CONFIG_SCHEMA
    },
    'additionalProperties': False
}

_CONFIG_SCHEMA = {
    'type': 'object',
    'required': [
        's3',
        'yostar_login'
    ],
    'properties': {
        'redis': _REDIS_CONFIG_SHCEMA,
        's3': _S3_CONFIG_SCHEMA,
        'yostar_login': _YOSTAR_LOGIN_CONFIG_SCHEMA,
        'sniffer': {
            'type': 'object',
            'required': [
                'logging'
            ],
            'properties': {
                'logging': _LOGGING_CONFIG_SCHEMA
            },
            'additionalProperties': False
        },
        'fetcher': {
            'type': 'object',
            'required': [
                'logging'
            ],
            'properties': {
                'logging': _LOGGING_CONFIG_SCHEMA
            },
            'additionalProperties': False
        },
        'analyzer': {
            'type': 'object',
            'required': [
                'logging'
            ],
            'properties': {
                'logging': _LOGGING_CONFIG_SCHEMA
            },
            'additionalProperties': False
        }
    },
    'additionalProperties': False
}


Config = Dict[
    str,
    Dict[str, str | int | List[str] | Dict[str, str | Dict[str, str | int]]]
]

_CONFIG: Optional[Config] = None


def get_config() -> Config:
    global _CONFIG # pylint: disable=global-statement
    if _CONFIG is not None:
        return _CONFIG

    with open('config.yaml', encoding='UTF-8') as fp:
        _CONFIG = yaml.load(fp, Loader=yaml.Loader) # type: ignore
    jsonschema.validate(instance=_CONFIG, schema=_CONFIG_SCHEMA) # type: ignore
    if _CONFIG is None:
        raise RuntimeError('An invalid config file.')

    if 'redis' not in _CONFIG:
        _CONFIG['redis'] = {
            'host': 'redis',
            'port': 6379
        }
    if 'host' not in _CONFIG['redis']:
        _CONFIG['redis']['host'] = 'redis'
    if 'port' not in _CONFIG['redis']:
        _CONFIG['redis']['port'] = 6379

    if 'sniffer' in _CONFIG:
        if 'level' not in _CONFIG['sniffer']['logging']: # type: ignore
            _CONFIG['sniffer']['logging']['level'] = 'INFO' # type: ignore
        if 'file' in _CONFIG['sniffer']['logging']: # type: ignore
            if 'max_bytes' not in _CONFIG['sniffer']['logging']['file']: # type: ignore
                _CONFIG['sniffer']['logging']['file']['max_bytes'] = 10485760 # type: ignore
            if 'backup_count' not in _CONFIG['sniffer']['logging']['file']: # type: ignore
                _CONFIG['sniffer']['logging']['file']['backup_count'] = 10 # type: ignore
        if 'redis' in _CONFIG['sniffer']['logging']: # type: ignore
            if 'max_entries' not in _CONFIG['sniffer']['logging']['redis']: # type: ignore
                _CONFIG['sniffer']['logging']['redis']['max_entries'] = 1024 # type: ignore

    if 'fetcher' in _CONFIG:
        if 'level' not in _CONFIG['fetcher']['logging']: # type: ignore
            _CONFIG['fetcher']['logging']['level'] = 'INFO' # type: ignore
        if 'file' in _CONFIG['fetcher']['logging']: # type: ignore
            if 'max_bytes' not in _CONFIG['fetcher']['logging']['file']: # type: ignore
                _CONFIG['fetcher']['logging']['file']['max_bytes'] = 10485760 # type: ignore
            if 'backup_count' not in _CONFIG['fetcher']['logging']['file']: # type: ignore
                _CONFIG['fetcher']['logging']['file']['backup_count'] = 10 # type: ignore
        if 'redis' in _CONFIG['fetcher']['logging']: # type: ignore
            if 'max_entries' not in _CONFIG['fetcher']['logging']['redis']: # type: ignore
                _CONFIG['fetcher']['logging']['redis']['max_entries'] = 1024 # type: ignore

    if 'analyzer' in _CONFIG:
        if 'level' not in _CONFIG['analyzer']['logging']: # type: ignore
            _CONFIG['analyzer']['logging']['level'] = 'INFO' # type: ignore
        if 'file' in _CONFIG['analyzer']['logging']: # type: ignore
            if 'max_bytes' not in _CONFIG['analyzer']['logging']['file']: # type: ignore
                _CONFIG['analyzer']['logging']['file']['max_bytes'] = 10485760 # type: ignore
            if 'backup_count' not in _CONFIG['analyzer']['logging']['file']: # type: ignore
                _CONFIG['analyzer']['logging']['file']['backup_count'] = 10 # type: ignore
        if 'redis' in _CONFIG['analyzer']['logging']: # type: ignore
            if 'max_entries' not in _CONFIG['analyzer']['logging']['redis']: # type: ignore
                _CONFIG['analyzer']['logging']['redis']['max_entries'] = 1024 # type: ignore

    return _CONFIG
