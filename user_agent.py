import sys
import os
import json
import random
import asyncio
import aiohttp
from urllib.parse import quote_plus
from lxml import etree  # type: ignore

import logging
logging.basicConfig(
    format="%(asctime)s %(levelname)s %(name)s.%(filename)s[%(lineno)d] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    level=logging.INFO,
)
logger = logging.getLogger(__package__)


VERSION = "2.3.0"
BACKUP_FILE = "fake_useragent.json"
FIXED_UA = "Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/29.0.1547.62 Safari/537.36"

BROWSERS = ['chrome', 'edge', 'firefox', 'safari', 'opera']
RANDOM_CUM_WEIGHTS = [80, 86, 93, 97, 100]


def call_on_error(error, url, attempt, op):
    attempt += 1
    logger.debug(f"{op} {url} {attempt} times")
    if attempt == 3:
        logger.debug(f"Maximum {op} reached: {error.__class__.__name__}: {error}")
    return attempt


async def parse(browser, session):
    base_page = "http://useragentstring.com/pages/useragentstring.php?name={browser}"
    url = base_page.format(browser=quote_plus(browser))
    attempt = 0
    result = None
    while True:
        try:
            async with session.get(url, headers={"User-Agent": FIXED_UA}, ssl=False) as resp:
                result = await resp.text()
                break
        except aiohttp.ServerTimeoutError as error:
            attempt = call_on_error(error, url, attempt, "FETCHING")
            if attempt == 3:
                break
            else:
                continue
        except Exception as error:
            logger.debug(f'FETCHING {url} failed: {error.__class__.__name__}: {error}')
            break

    if result is None: 
        return (browser, None)

    lxml_element = etree.HTML(result)
    browser_num = 50
    versions = lxml_element.xpath('//*[@id="liste"]/ul/li/a/text()')[:browser_num]
    if not versions:
        logger.debug("Nothing parsed out. Check if the website has changed.")
        return (browser, None)

    logger.debug(f"{url} has been parsed successfully.")
    return (browser, versions)


def die(file_path, error, op):
    logger.error(f'{op} <{file_path}> failed: {error.__class__.__name__}: {error}')
    sys.exit(1)


async def dump(cache_path):
    async with aiohttp.ClientSession() as session:
        tasks = []
        for browser in BROWSERS:
            tasks.append(parse(browser, session))
        results = await asyncio.gather(*tasks)

    if not results:
        logger.error("Nothing parsed out. Check if the website has changed. Quit out.")
        sys.exit(1)

    all_browsers = {}
    for result in results:
        if result[1] is None: 
            logger.error('Nothing parsed out from "{result[0]}". Quit out.')
            sys.exit(1)
        all_browsers[result[0]] = result[1] 

    dumped = json.dumps(all_browsers)

    dir_name = os.path.dirname(cache_path)
    if dir_name != "" and dir_name != ".":
        cache_path = os.path.expanduser(os.path.expandvars(cache_path))
        dir_name = os.path.dirname(cache_path)
        if not os.path.exists(dir_name):
            try:
                logger.debug(f'CREATING directory <{dir_name}>')
                os.makedirs(dir_name, exist_ok=True)
            except Exception as error:
                die(cache_path, error, "WRITING")
    try:
        with open(cache_path, encoding="utf-8", mode="wt") as f:
            f.write(dumped)
    except Exception as error:
            die(cache_path, error, "WRITING")
    logger.debug(f"Data has been stored in <{cache_path}>\n")


def remove(cache_path):
    dir_name = os.path.dirname(cache_path)
    if dir_name != "" and dir_name != ".":
        cache_path = os.path.expanduser(os.path.expandvars(cache_path))
        dir_name = os.path.dirname(cache_path)
        if not os.path.exists(dir_name):
            die(cache_path, error, "REMOVING")
    try:
        os.remove(cache_path)
    except Exception as error:
        die(cache_path, error, "REMOVING")
    logger.debug(f"<{cache_path}> has been removed successfully.\n")


def load_and_random(browser, cache_path):
    try:
        with open(cache_path, encoding="utf-8") as f:
            data = f.read()
    except Exception as error:
        logger.debug(f'Opening <{cache_path}> failed: {error.__class__.__name__}: {error}')
        logger.debug(f'Resort to a fixed useragent: {FIXED_UA}')
        return FIXED_UA
    else:
        logger.debug(f"Read <{cache_path}> successfully.")
        ua = random.choice(json.loads(data)[browser])
        logger.debug(f'Randomized a useragent from <{cache_path}>')
        return ua


async def main(browser=None, use_cache=True, cache_path=BACKUP_FILE):
    if browser is None:
        logger.debug("A browser will be randomly given.")
        browser = random.choices(BROWSERS, weights=RANDOM_CUM_WEIGHTS, k=1)[0]
        logger.debug(f'Got "{browser}"')
    else:
        logger.debug(f'You gave "{browser}"')
        browser = browser.strip().lower()
        if browser not in BROWSERS:
            new_browser = random.choices(BROWSERS, weights=RANDOM_CUM_WEIGHTS, k=1)[0]
            logger.debug(f'"{browser}" not supported, should be one of {BROWSERS}. Randomized "{new_browser}"')

    if not use_cache:
        async with aiohttp.ClientSession() as session:
            (browser, versions) = await parse(browser, session)
            if versions is None:
                logger.debug("Reading backup data ...")
                return load_and_random(browser, cache_path)
            else:
                ua = random.choice(versions)
                logger.debug("Randomized a useragent without using cache.")
                return ua 
    else:
        return load_and_random(browser, cache_path)


def user_agent(browser=None, use_cache=True, cache_path=BACKUP_FILE):
    return asyncio.run(main(browser, use_cache, cache_path))


async def aio_user_agent(browser=None, use_cache=True, cache_path=BACKUP_FILE):
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = None

    if loop is not None and loop.is_running():
        return await loop.create_task(main(browser, use_cache, cache_path))
    else:
        return asyncio.run(main(browser, use_cache, cache_path))


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Randomly generate a valid useragent for faking a browser.")
    parser.add_argument("browser", nargs="?", default="", help="supported values: chrome, edge, firefox, safari, opera. (case insensitive)")
    parser.add_argument("-d", "--debug", action="store_true", help="randomize a useragent in debug mode")
    parser.add_argument("-n", "--nocache", action="store_true", help="randomize a useragent by fetching the web")
    parser.add_argument("-l", "--loadcache", nargs=1, help="load up to date useragent versions to specified file path")
    parser.add_argument("-r", "--removecache", nargs=1, help="remove a cache file at the specified file path")
    parser.add_argument("-v", "--version", action="store_true", help="print the current version of the program")
    args = parser.parse_args()
    try:
        if args.version:
            print("fake_user_agent " + VERSION)
            sys.exit()
        if args.debug:
            logger.setLevel(logging.DEBUG)
        if args.loadcache:
            asyncio.run(dump(args.loadcache[0]))
            sys.exit()
        if args.removecache:
            remove(args.removecache[0])
            sys.exit()
        
        browser = None if not args.browser else args.browser
        use_cache = False if args.nocache else True
        result = asyncio.run(main(browser, use_cache))
        print(result)

    except KeyboardInterrupt:
        print("\nStopped by user.")