#!/usr/bin/env python3

from selenium.webdriver.chrome.options import Options
from selenium.webdriver import Chrome


def _main() -> None:
    options = Options()
    options.headless = True
    options.add_argument('--no-sandbox') # type: ignore
    options.add_argument('--disable-dev-shm-usage') # type: ignore
    options.add_argument('--ignore-certificate-errors') # type: ignore
    options.add_argument('--window-size=800,600') # type: ignore
    with Chrome(options=options) as driver:
        driver.get('https://www.google.com/')


if __name__ == '__main__':
    _main()
