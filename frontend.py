import re
import time
import logging
import json
from http import HTTPStatus
from typing import List, Dict
from flask import (Flask, Response,)
from kanachan_reviewer.config import get_config
from kanachan_reviewer.redis import Redis


app = Flask(__name__)


_TIMEOUT = 60


_CONFIG = get_config()


_REDIS_HOST = _CONFIG['redis']['host']
assert isinstance(_REDIS_HOST, str)
_REDIS_PORT = _CONFIG['redis']['port']
assert isinstance(_REDIS_PORT, int)
_REDIS = Redis(_REDIS_HOST, _REDIS_PORT)


# Initialize fetchers.
_EMAIL_ADDRESSES: List[str] = _CONFIG['yostar_login']['email_addresses'] # type: ignore
for i, email_address in enumerate(_EMAIL_ADDRESSES):
    process_info = {
        'process_rank': i,
        'email_address': email_address
    }
    process_info_json = json.dumps(process_info, separators=(',', ':'))
    _REDIS.rpush('fetcher-initializers', process_info_json)


@app.route('/')
def top_page():
    return Response(status=HTTPStatus.OK)


@app.route('/<uuid>')
def analyze(uuid: str):
    match = re.search('^\\d{6}-[0-9A-Fa-f]{8}(?:-[0-9A-Fa-f]{4}){3}-[0-9A-Fa-f]{12}$', uuid)
    if match is None:
        return Response(status=HTTPStatus.NOT_FOUND)

    _REDIS.rpush('game-record-requests', uuid)
    logging.info('%s: Requested a review.', uuid)

    review_encoded = None
    for _ in range(_TIMEOUT):
        review_encoded = _REDIS.hget('reviews', uuid)
        if review_encoded is not None:
            logging.info('%s: The review arrived.', uuid)
            break
        time.sleep(1)

    if review_encoded is None:
        logging.info('%s: The review timed out.', uuid)
        return Response(status=HTTPStatus.REQUEST_TIMEOUT)

    review_with_timestamp_json = review_encoded.decode('UTF-8')
    review_with_timestamp: Dict[str, object] = json.loads(review_with_timestamp_json)
    error_code = review_with_timestamp['error_code']
    if error_code == 1203:
        logging.info('%s: No game is found.', uuid)
        return Response(status=HTTPStatus.NOT_FOUND)
    if error_code != 0:
        logging.info('%s: An unknown error code `%s`.', uuid, error_code)
        return Response(status=HTTPStatus.BAD_REQUEST)

    review = review_with_timestamp['review']
    review_json = json.dumps(review)
    response = Response(response=review_json, status=HTTPStatus.OK, mimetype='application/json')
    return response
