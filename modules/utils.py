import hashlib
import logging
import os

import pandas as pd
import tzlocal


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
    logger.debug(f"toTimestamp: date={date}, time={time}")
    datetime_local = pd.to_datetime(f"{date} {time}")
    local_timezone = tzlocal.get_localzone()
    logger.debug(f"Timezone locale: {local_timezone}")
    datetime_utc = datetime_local.tz_localize(local_timezone).tz_convert("UTC")
    timestamp = datetime_utc.timestamp()
    logger.debug(
        f"timestamp={timestamp} [local_time={datetime_local}, utc_time={datetime_utc}]"
    )
    return timestamp


def toTimestamp_B(date: str, time: str = "") -> float:
    # date if formated as ISO 8601
    # convert to a datetime object, convert to UTC and then to epoch timestamp
    if time:
        date = f"{date}T{time}"
    logger.debug(f"toTimestamp: date={date}")
    datetime_local = pd.to_datetime(date)
    local_timezone = tzlocal.get_localzone()
    logger.debug(f"Timezone locale: {local_timezone}")
    datetime_utc = datetime_local.tz_localize(local_timezone).tz_convert("UTC")
    timestamp = datetime_utc.timestamp()
    logger.debug(
        f"timestamp={timestamp} [local_time={datetime_local}, utc_time={datetime_utc}]"
    )
    return timestamp


def get_file_hash(filename):
    """Calculate MD5 hash of file"""
    md5_hash = hashlib.md5()
    with open(filename, "rb") as f:
        # Read file in chunks to handle large files
        for chunk in iter(lambda: f.read(4096), b""):
            md5_hash.update(chunk)
    return md5_hash.hexdigest()


def listfilesrecursive(directory, fileslist=None):
    # list all files in directory recurcively

    if fileslist is None:
        fileslist = []

    items = os.listdir(directory)
    # logger.debug(f"list directory {directory}: {items}")
    for item in items:
        path = os.path.join(directory, item)
        if os.path.isdir(path):
            # logger.debug(f"{path} is a directory.")
            listfilesrecursive(path, fileslist)
        else:
            # logger.debug(f"Add file {path}")
            fileslist.append(path)
    # logger.debug(f"Return {fileslist}")
    return fileslist


def debug_prefix(input_str: str, flag=False) -> str:
    """Add debug prefix to string if flag is True"""
    if flag:
        return f"debug_{input_str}"
    return input_str


def dataframe_diff(df1, df2):
    """Find rows that are different between two DataFrames"""
    comparison_df = df1.merge(df2, indicator=True, how="outer")
    logger.debug("comparison_df:\n%s", comparison_df.to_string())
    diff_df = comparison_df[comparison_df["_merge"] != "both"]
    return diff_df