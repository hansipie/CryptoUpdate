import hashlib
import logging
import os

import pandas as pd
import tzlocal
from dateutil import parser


logger = logging.getLogger(__name__)


def __find_linear_function(x1, y1, x2, y2):
    # Calculer la pente a
    a = (y2 - y1) / (x2 - x1)
    # Calculer l'ordonnée à l'origine b
    b = y1 - a * x1
    return a, b


def interpolate(x1, y1, x2, y2, x):
    if x1 == x2 or y1 == y2:
        return y1
    if x1 > x2:
        x1, x2 = x2, x1
        y1, y2 = y2, y1
    if x < x1 or x > x2:
        raise ValueError(f"x={x} is out of range [{x1}, {x2}]")
    a, b = __find_linear_function(x1, y1, x2, y2)
    return a * x + b


def toTimestamp_A(date, time):
    # date if formated as yyyy-mm-dd, time as hh:mm:00
    # merge them to a datetime object, convert to UTC and then to epoch timestamp
    logger.debug("toTimestamp: date=%s, time=%s", date, time)
    datetime_local = pd.to_datetime(f"{date} {time}")
    local_timezone = tzlocal.get_localzone()
    logger.debug("Timezone locale: %s", local_timezone)
    datetime_utc = datetime_local.tz_localize(local_timezone).tz_convert("UTC")
    timestamp = datetime_utc.timestamp()
    logger.debug(
        "timestamp=%s [local_time=%s, utc_time=%s]",
        timestamp,
        datetime_local,
        datetime_utc,
    )
    return timestamp


def toTimestamp_B(date: str, time: str = "", utc=False) -> float:
    # date if formated as ISO 8601
    # convert to a datetime object, convert to UTC and then to epoch timestamp
    if time:
        datetime_in = f"{date} {time}"
    else:
        datetime_in = date

    logger.debug("toTimestamp: date=%s", datetime_in)

    try:
        datetime_formated = parser.parse(datetime_in)
        logger.debug("Parsed datetime: %s", datetime_formated)
    except Exception as e:
        logger.error("Error parsing date: %s", e)
        raise

    if utc:
        datetime_utc = datetime_formated
    else:
        datetime_local = pd.to_datetime(datetime_formated)
        logger.debug("Local datetime: %s", datetime_local)
        local_timezone = tzlocal.get_localzone()
        logger.debug("Timezone locale: %s", local_timezone)
        datetime_utc = datetime_local.tz_localize(local_timezone).tz_convert("UTC")

    timestamp = datetime_utc.timestamp()
    logger.debug(
        "timestamp=%s [local_time=%s, utc_time=%s]",
        timestamp,
        datetime_formated,
        datetime_utc,
    )
    return timestamp


def fromTimestamp(timestamp: int) -> str:
    # convert epoch timestamp to a datetime object in UTC
    datetime_utc = pd.Timestamp.fromtimestamp(timestamp, tz="UTC")
    return datetime_utc.strftime("%Y-%m-%dT%H:%M:%SZ")


def get_file_hash(filename):
    """Calculate MD5 hash of file"""
    md5_hash = hashlib.md5()
    with open(filename, "rb") as f:
        # Read file in chunks to handle large files
        for chunk in iter(lambda: f.read(4096), b""):
            md5_hash.update(chunk)
    return md5_hash.hexdigest()


def list_files_recursive(directory, fileslist=None):
    """Recursively list all files in a directory"""
    if fileslist is None:
        fileslist = []

    items = os.listdir(directory)
    for item in items:
        path = os.path.join(directory, item)
        if os.path.isdir(path):
            list_files_recursive(path, fileslist)
        else:
            fileslist.append(path)
    return fileslist


def debug_prefix(input_str: str, flag=False) -> str:
    """Add debug prefix to string if flag is True"""
    if flag:
        return f"debug_{input_str}"
    return input_str


def dataframe_diff(df1, df2):
    """Find rows that are different between two DataFrames"""
    comparison_df = df1.merge(df2, indicator=True, how="outer")
    logger.debug("comparison_df:\n%s", comparison_df)
    diff_df = comparison_df[comparison_df["_merge"] != "both"]
    return diff_df
