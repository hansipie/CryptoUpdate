import hashlib
import logging
import os

import pandas as pd
import tzlocal
from dateutil import parser


logger = logging.getLogger(__name__)


def _find_linear_function(x1, y1, x2, y2):
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
    a, b = _find_linear_function(x1, y1, x2, y2)
    return a * x + b


def to_timestamp_a(date, time):
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


def to_timestamp_b(date: str, time: str = "", utc=False) -> float:
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


def from_timestamp(timestamp: int) -> str:
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
    left_df = df1.copy()
    right_df = df2.copy()

    if list(left_df.columns) != list(right_df.columns):
        all_columns = sorted(set(left_df.columns).union(right_df.columns))
        left_df = left_df.reindex(columns=all_columns)
        right_df = right_df.reindex(columns=all_columns)

    left_df["_source"] = "left"
    right_df["_source"] = "right"
    combined_df = pd.concat([left_df, right_df], ignore_index=True)

    row_columns = [col for col in combined_df.columns if col != "_source"]
    combined_df["_count"] = 1

    # Compare row multiplicities by source without using outer merge.
    comparison_df = (
        combined_df.pivot_table(
            index=row_columns,
            columns="_source",
            values="_count",
            aggfunc="sum",
            fill_value=0,
        )
        .reset_index()
        .rename_axis(columns=None)
    )

    if "left" not in comparison_df.columns:
        comparison_df["left"] = 0
    if "right" not in comparison_df.columns:
        comparison_df["right"] = 0

    comparison_df["left"] = comparison_df["left"].astype(int)
    comparison_df["right"] = comparison_df["right"].astype(int)

    left_only_repeats = (comparison_df["left"] - comparison_df["right"]).clip(lower=0)
    right_only_repeats = (comparison_df["right"] - comparison_df["left"]).clip(lower=0)

    diff_parts = []

    if left_only_repeats.sum() > 0:
        left_only_df = comparison_df.loc[
            comparison_df.index.repeat(left_only_repeats), row_columns
        ].copy()
        left_only_df["_merge"] = "left_only"
        diff_parts.append(left_only_df)

    if right_only_repeats.sum() > 0:
        right_only_df = comparison_df.loc[
            comparison_df.index.repeat(right_only_repeats), row_columns
        ].copy()
        right_only_df["_merge"] = "right_only"
        diff_parts.append(right_only_df)

    if not diff_parts:
        return pd.DataFrame(columns=row_columns + ["_merge"])

    diff_df = pd.concat(diff_parts, ignore_index=True)
    logger.debug("comparison_df:\n%s", comparison_df)
    logger.debug("diff_df:\n%s", diff_df)
    return diff_df
