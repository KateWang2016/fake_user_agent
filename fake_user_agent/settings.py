"""Setting static data."""

import os
import re
import tempfile
import logging

from fake_user_agent import __version__
from fake_user_agent import log 

logger = logging.getLogger(__name__)

TEMP_DIR = tempfile.gettempdir()   

def find_tempfile(dir):
    for _, _, files in os.walk(dir):
        for f in files:
            match = re.search(r'^fake_useragent_', f)
            if match:
                logger.debug(f"{f} is found")
                return os.path.join(dir, f)

    logger.debug("No cache is found")
    return "" 

TEMP_FILE = find_tempfile(TEMP_DIR)

DB = os.path.join(TEMP_DIR, "fake_useragent_{version}.json".format(version=__version__))

BROWSER_BASE_PAGE = "http://useragentstring.com/pages/useragentstring.php?name={browser}"

BROWSERS = {
    "chrome": 80.7,
    "edge": 5.6,
    "firefox": 6.1,
    "safari": 3.7,
    "opera": 2.4,
}

SHORTCUTS = {
    "internet explorer": "edge",
    "ie": "edge",
    "google": "chrome",
    "googlechrome": "chrome",
    "ff": "firefox",
}

BROWSERS_COUNT_LIMIT = 50

HTTP_TIMEOUT = 10


