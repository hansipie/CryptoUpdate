import io
import logging
import math
from json import loads

import pandas as pd
import streamlit as st
from PIL import Image

from modules import aiprocessing
from modules.database import portfolios as pf


logging.getLogger("PIL").setLevel(logging.WARNING)
logger = logging.getLogger(__name__)

MAX_UPLOAD_BYTES = 10 * 1024 * 1024


@st.cache_data
def decode_img(image_bytes) -> bytes:
    logger.debug("Decoding image")
    image_file = io.BytesIO(image_bytes)
    with Image.open(image_file) as img:
        maxsize = 768
        img.thumbnail((maxsize, maxsize), Image.Resampling.LANCZOS)
        img_bytes = io.BytesIO()
        img.save(img_bytes, format="PNG")
    logger.debug("Image decoded: %f bytes", len(img_bytes.getvalue()))
    return img_bytes.getvalue()


@st.fragment
def data_ui(df: pd.DataFrame) -> pd.DataFrame:
    logger.debug("Displaying data")
    st.session_state.import_page["output"] = st.data_editor(
        df,
        width="stretch",
    )

    col_pfolios, col_action = st.columns([0.8, 0.2], vertical_alignment="center")
    with col_pfolios:
        portfolios = st.selectbox(
            "Portfolios",
            g_portfolio.get_portfolio_names(),
            index=None,
            placeholder="Select a portfolio",
        )
    with col_action:
        action = st.segmented_control("Actions", ["Set", "Add"], default="Set")
    if st.button("Save", key="save", icon=":material/save:"):
        save_data(st.session_state.import_page["output"], portfolios, action)

    logger.debug("Fragment ended")


def extract(input_data: any) -> pd.DataFrame:
    """Extract structured data from input using AI processing.

    Args:
        input: Image bytes or DataFrame to process

    Returns:
        DataFrame containing extracted asset data

    Raises:
        ValueError: If input type is not supported
    """
    logger.debug("Extracting data")
    output = None
    with st.spinner("Extracting data...", show_time=True):
        try:
            if isinstance(input_data, bytes):
                message_json, _ = aiprocessing.extract_from_img(
                    input_data,
                    st.session_state.settings["ai_apitoken"],
                    model=st.session_state.settings.get("ai_model"),
                )
            elif isinstance(input_data, pd.DataFrame):
                message_json, _ = aiprocessing.extract_from_df(
                    input_data,
                    st.session_state.settings["ai_apitoken"],
                    model=st.session_state.settings.get("ai_model"),
                )
            else:
                raise ValueError("Invalid input type")
            # call_ai logs API failures and returns None instead of raising
            if message_json is None:
                raise ValueError("The AI service returned no usable answer")
            assets = loads(message_json).get("assets")
            if not assets:
                raise ValueError("No asset found in the AI answer")
            output = pd.DataFrame(assets)
            if not {"symbol", "amount"} <= set(output.columns):
                raise ValueError("The AI answer has no symbol/amount columns")
        except (ValueError, KeyError, TypeError) as e:
            st.error("Unexpected error: " + str(e))
            logger.exception("Extraction failed")
            st.stop()

    output["select"] = False
    return output


def _is_valid_amount(symbol: str, amount: float, action: str) -> bool:
    """Check an extracted row: a model produced it, never trust it blindly.

    Only an "Add" may be negative (a manual correction in the editor).
    """
    if not symbol or symbol == "NAN" or pd.isna(amount) or not math.isfinite(amount):
        return False
    return action != "Set" or amount >= 0


def save_data(df: pd.DataFrame, portfolio: str = None, action: str = "Set"):
    """Save imported data to selected portfolio.

    Args:
        df: DataFrame containing token data
        portfolio: Name of target portfolio
        action: Operation type ('Set' or 'Add')
    """
    if portfolio is None:
        st.error("Please select a portfolio")
        return
    if not action:
        st.error("Please select an action")
        return
    saved = 0
    skipped = []
    for _, row in df.iterrows():
        if not row["select"]:
            continue
        symbol = str(row["symbol"]).strip().upper()
        amount = pd.to_numeric(row["amount"], errors="coerce")
        if not _is_valid_amount(symbol, amount, action):
            skipped.append(f"{row['symbol']} ({row['amount']})")
            continue
        logger.debug("Saving data: %s %s", symbol, amount)
        if action == "Set":
            g_portfolio.set_token(portfolio, symbol, float(amount))
        elif action == "Add":
            g_portfolio.set_token_add(portfolio, symbol, float(amount))
        saved += 1
    if skipped:
        st.warning("Skipped invalid rows: " + ", ".join(skipped))
    if not saved:
        return
    st.toast("Data successfully saved", icon=":material/check:")


def process_img(input_file) -> bytes:
    """Process uploaded image file.

    Args:
        input_file: Uploaded image file object

    Returns:
        Processed image bytes
    """
    logger.debug("Processing image")
    ret = decode_img(input_file.getvalue())
    logger.debug("Image processed")
    return ret


@st.cache_data
def process_csv(input_file) -> pd.DataFrame:
    """Process uploaded CSV file.

    Args:
        input_file: Uploaded CSV file object

    Returns:
        DataFrame containing file contents
    """
    logger.debug("Processing CSV")
    return pd.read_csv(input_file)


def draw_ui():
    """Draw the import interface UI components.

    Shows input preview and extraction controls.
    """
    col_input, col_output = st.columns(2)
    with col_input:
        if isinstance(st.session_state.import_page["input"], pd.DataFrame):
            st.dataframe(
                st.session_state.import_page["input"],
                column_config={
                    "amount": st.column_config.NumberColumn(format="%.8g"),
                },
                width="stretch",
            )
        else:
            st.image(st.session_state.import_page["input"])
    with col_output:
        if st.session_state.import_page["output"] is None:
            logger.debug("Data not extracted yet")
            if st.button("Extract Data", width="stretch", icon=":material/table:"):
                output = extract(st.session_state.import_page["input"])
                data_ui(output)
        else:
            logger.debug("Data already extracted")
            st.button(
                "Extract Data",
                width="stretch",
                disabled=True,
                icon=":material/table:",
            )
            data_ui(st.session_state.import_page["output"])


def clean_session_state():
    """Reset the import page session state variables."""
    logger.debug("Cleaning session state")
    st.session_state.import_page["input"] = None
    st.session_state.import_page["output"] = None
    st.session_state.import_page["type"] = None


logger.debug("## started ##")

# Initialize session state with a proper nested structure
if "import_page" not in st.session_state:
    st.session_state.import_page = {}
if "input" not in st.session_state.import_page:
    st.session_state.import_page["input"] = None
if "output" not in st.session_state.import_page:
    st.session_state.import_page["output"] = None
if "type" not in st.session_state.import_page:
    st.session_state.import_page["type"] = None

g_portfolio = pf.Portfolios(st.session_state.settings["dbfile"])

st.title("Import")

file = st.file_uploader(
    "Upload a file", type=["png", "jpg", "jpeg", "csv"], on_change=clean_session_state
)

if file is None:
    if st.session_state.import_page["input"] is not None:
        logger.debug("Data already imported")
        if st.button("Clear Data", width="stretch", icon=":material/delete:"):
            clean_session_state()
        else:
            draw_ui()
    else:
        logger.debug("No file uploaded")
        clean_session_state()
else:
    logger.debug("File: %s - file type: %s", file.name, file.type)

    if file.size > MAX_UPLOAD_BYTES:
        st.error(f"File too large (max {MAX_UPLOAD_BYTES // (1024 * 1024)} MB)")
        st.stop()
    try:
        if file.type == "text/csv" or file.name.endswith(".csv"):
            logger.debug("CSV file detected")
            input_file = process_csv(file)
        else:
            logger.debug("Image file detected")
            input_file = process_img(file)
    except (
        OSError,
        ValueError,
        pd.errors.ParserError,
        pd.errors.EmptyDataError,
        Image.DecompressionBombError,
    ) as e:
        logger.exception("Unreadable upload")
        st.error(f"Cannot read this file: {e}")
        st.stop()
    st.session_state.import_page["type"] = file.type
    st.session_state.import_page["input"] = input_file
    draw_ui()

logger.debug("## ended ##")
