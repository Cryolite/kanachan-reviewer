#!/usr/bin/env python3

import datetime
import random
import pathlib
import time
import logging
import json
from typing import Dict
import sys
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.proxy import Proxy
from selenium.webdriver.common.desired_capabilities import DesiredCapabilities
from selenium.webdriver import Chrome
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.remote.webelement import WebElement
from selenium.common.exceptions import UnexpectedAlertPresentException
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as ec
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver import ActionChains
from kanachan_reviewer.config import get_config
from kanachan_reviewer.redis import Redis
import kanachan_reviewer.logging as logging_
from kanachan_reviewer.yostar_login import YostarLogin


_CONFIG = get_config()


_REDIS_HOST = _CONFIG['redis']['host']
assert isinstance(_REDIS_HOST, str)
_REDIS_PORT = _CONFIG['redis']['port']
assert isinstance(_REDIS_PORT, int)
_REDIS = Redis(_REDIS_HOST, _REDIS_PORT)


_BROWSER_RESTART_INTERVAL = 60


def _click_canvas_within(
        driver: WebDriver, canvas: WebElement,
        left: int, top: int, width: int, height: int) -> None:
    center_x = left + width / 2.0
    center_y = top + height / 2.0

    x_sigma = width / 4.0
    while True:
        x = int(random.normalvariate(center_x, x_sigma)) # pylint: disable=invalid-name
        if left <= x and x < left + width:
            break

    y_sigma = height / 4.0
    while True:
        y = int(random.normalvariate(center_y, y_sigma)) # pylint: disable=invalid-name
        if top <= y and y < top + height:
            break

    rect: Dict[str, int] = canvas.rect # type: ignore
    x -= rect['width'] / 2 # pylint: disable=invalid-name
    y -= rect['height'] / 2 # pylint: disable=invalid-name

    ActionChains(driver).move_to_element_with_offset(canvas, x, y).click().perform() # type: ignore


_SCREENSHOT_PREFIX = pathlib.Path('/var/log/kanachan-reviewer')


def _get_screenshot(process_rank: int, driver: WebDriver, name: str) -> None:
    prefix = _SCREENSHOT_PREFIX / f'fetcher.{process_rank}'
    if not prefix.exists():
        prefix.mkdir(exist_ok=True)
    if not prefix.is_dir():
        raise RuntimeError(f'`{prefix}` is not a directory.')
    screenshot_path = prefix / name
    driver.get_screenshot_as_file(str(screenshot_path)) # type: ignore


def _wait_for_page_to_present(driver: WebDriver) -> WebElement:
    canvas: WebElement = WebDriverWait(driver, 60).until( # type: ignore
        ec.visibility_of_element_located((By.ID, 'layaCanvas'))) # type: ignore
    time.sleep(15)
    return canvas


def _fetch(process_rank: int, email_address: str, driver: WebDriver) -> None:
    driver.get('https://game.mahjongsoul.com/')
    canvas = _wait_for_page_to_present(driver)
    _get_screenshot(process_rank, driver, '00-load-page.png')

    s3_bucket_name = _CONFIG['s3']['bucket_name']
    assert isinstance(s3_bucket_name, str)
    s3_key_prefix = _CONFIG['s3']['authentication_email_key_prefix']
    assert isinstance(s3_key_prefix, str)
    yostar_login = YostarLogin(email_address, s3_bucket_name, s3_key_prefix)

    # Click the "login" button.
    _click_canvas_within(driver, canvas, 540, 177, 167, 38)
    time.sleep(1)
    _get_screenshot(process_rank, driver, '01-click-login-button.png')

    # Click the "mail address" form to focus it.
    _click_canvas_within(driver, canvas, 145, 154, 291, 30)
    time.sleep(1)

    email_address = yostar_login.get_email_address()

    # Input the email address to the "mail address" form.
    ActionChains(driver).send_keys(email_address).perform() # type: ignore
    time.sleep(1)
    _get_screenshot(process_rank, driver, '02-input-email-address.png')

    # Click the "get auth code" button.
    start_time = datetime.datetime.now(tz=datetime.timezone.utc)
    _click_canvas_within(driver, canvas, 351, 206, 86, 36)
    time.sleep(1)
    _get_screenshot(process_rank, driver, '03-click-get-code-button.png')

    # Click the "confirm" button.
    _click_canvas_within(driver, canvas, 378, 273, 60, 23)
    time.sleep(1)
    _get_screenshot(process_rank, driver, '04-click-confirm-button.png')

    # Click the "auth code" form to focus it.
    _click_canvas_within(driver, canvas, 144, 211, 196, 30)
    time.sleep(1)

    auth_code = yostar_login.get_auth_code(start_time, datetime.timedelta(minutes=1))

    # Input the auth code to the "auth code" form.
    ActionChains(driver).send_keys(auth_code).perform() # type: ignore
    time.sleep(1)
    _get_screenshot(process_rank, driver, '05-input-auth-code.png')

    # Click the "login" button.
    _click_canvas_within(driver, canvas, 209, 293, 163, 37)

    time.sleep(120)

    _get_screenshot(process_rank, driver, '06-lobby.png')

    logging.info('Ready.')

    while True:
        encoded_uuid = _REDIS.blpop('game-record-requests')
        assert isinstance(encoded_uuid, bytes)
        uuid = encoded_uuid.decode('UTF-8')
        logging.info('%s: A request arrived.', uuid)

        if _REDIS.hget('reviews', uuid) is not None:
            logging.info('%s: Analysis cached.', uuid)
            continue

        if _REDIS.hget('game-record-fetched', uuid) is not None:
            logging.info('%s: Analysis in progress.', uuid)
            continue

        driver.get(f'https://game.mahjongsoul.com/?paipu={uuid}')

        for _ in range(60):
            if _REDIS.hget('game-record-fetched', uuid) is not None:
                logging.info('%s: Fetched the game record.', uuid)
                break
            time.sleep(1)


def _main() -> None:
    encoded_initializer_json = _REDIS.blpop('fetcher-initializers')
    assert isinstance(encoded_initializer_json, bytes)
    initializer_json = encoded_initializer_json.decode('UTF-8')
    initializer = json.loads(initializer_json)
    process_rank = initializer['process_rank']
    email_address = initializer['email_address']

    logging_.initialize('fetcher', process_rank, _REDIS, _CONFIG)

    for screenshot_path in (_SCREENSHOT_PREFIX / f'fetcher.{process_rank}').glob('*.png'):
        screenshot_path.unlink()
        logging.info('Deleted an old screenshot `%s`.', screenshot_path)

    options = Options()
    options.headless = True
    options.add_argument('--no-sandbox') # type: ignore
    options.add_argument('--disable-dev-shm-usage') # type: ignore
    options.add_argument('--window-size=800,600') # type: ignore

    proxy = Proxy()
    proxy.http_proxy = 'localhost:8080'
    proxy.ssl_proxy = 'localhost:8080'
    capabilities = DesiredCapabilities.CHROME.copy()
    proxy.add_to_capabilities(capabilities) # type: ignore

    # If the user agent contains the string `HeadlessChrome`,
    # the browser is rejected from the login process of Mahjong Soul.
    # Therefore, it is necessary to spoof the user agent.
    with Chrome(options=options, desired_capabilities=capabilities) as driver:
        driver.get('https://www.google.com/')
        user_agent: str = driver.execute_script('return navigator.userAgent') # type: ignore
        user_agent = user_agent.replace('HeadlessChrome', 'Chrome')
    options.add_argument(f'--user-agent={user_agent}') # type: ignore

    while True:
        with Chrome(options=options, desired_capabilities=capabilities) as driver:
            try:
                _fetch(process_rank, email_address, driver)
                sys.exit()
            except UnexpectedAlertPresentException as exception:
                if exception.alert_text == 'Laya3D init error,must support webGL!':
                    logging.warning(
                        '`Laya3D init error` occurred. So, restarting the browser after'
                        ' %s-seconds sleep...', _BROWSER_RESTART_INTERVAL)
                    time.sleep(_BROWSER_RESTART_INTERVAL)
                    continue
                if exception.alert_text == 'open failed':
                    logging.warning(
                        '`open failed` occurred. So, restarting the browser after %s-seconds'
                        ' sleep...', _BROWSER_RESTART_INTERVAL)
                    time.sleep(_BROWSER_RESTART_INTERVAL)
                    continue
                _get_screenshot(process_rank, driver, '99-エラー.png')
                logging.exception('Abort with an unhandled exception.')
                raise
            except Exception: # pylint: disable=broad-except
                _get_screenshot(process_rank, driver, '99-エラー.png')
                logging.exception('Abort with an unhandled exception.')
                logging.warning(
                    'Restarting the browser after %s-seconds sleep...', _BROWSER_RESTART_INTERVAL)
                time.sleep(_BROWSER_RESTART_INTERVAL)
                continue


if __name__ == '__main__':
    _main()
