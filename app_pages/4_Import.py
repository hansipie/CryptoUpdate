import io
import logging
import traceback
from json import loads

import pandas as pd
import streamlit as st
from PIL import Image

from modules import aiprocessing
from modules.database import portfolios as pf


logging.getLogger("PIL").setLevel(logging.WARNING)
logger = logging.getLogger(__name__)


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
        use_container_width=True,
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
                    input_data, st.session_state.settings["openai_token"]
                )
                output = pd.DataFrame.from_dict(loads(message_json).get("assets"))
            elif isinstance(input_data, pd.DataFrame):
                message_json, _ = aiprocessing.extract_from_df(
                    input_data, st.session_state.settings["openai_token"]
                )
                output = pd.DataFrame.from_dict(loads(message_json).get("assets"))
            else:
                raise ValueError("Invalid input type")
        except (ValueError, KeyError, TypeError) as e:
            st.error("Unexpected error: " + str(e))
            traceback.print_exc()
            st.stop()

    output["select"] = False
    return output


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
    tokens = {}
    for _, row in df.iterrows():
        if row["select"]:
            data = row.to_dict()
            logger.debug("Saving data: %s", data)
            tokens[data["symbol"]] = {"amount": data["amount"]}
            if action == "Set":
                g_portfolio.set_token(portfolio, data["symbol"], data["amount"])
            elif action == "Add":
                g_portfolio.set_token_add(portfolio, data["symbol"], data["amount"])
    st.toast("Data successfully saved", icon=":material/check:")


def processImg(input_file) -> bytes:
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
def processCSV(input_file) -> pd.DataFrame:
    """Process uploaded CSV file.

    Args:
        input_file: Uploaded CSV file object

    Returns:
        DataFrame containing file contents
    """
    logger.debug("Processing CSV")
    return pd.read_csv(input_file)


def drawUI():
    """Draw the import interface UI components.

    Shows input preview and extraction controls.
    """
    col_input, col_output = st.columns(2)
    with col_input:
        if st.session_state.import_page["type"] == "application/vnd.ms-excel":
            st.dataframe(
                st.session_state.import_page["input"],
                column_config={
                    "amount": st.column_config.NumberColumn(format="%.8g"),
                },
                use_container_width=True,
            )
        else:
            st.image(st.session_state.import_page["input"])
    with col_output:
        if st.session_state.import_page["output"] is None:
            logger.debug("Data not extracted yet")
            if st.button(
                "Extract Data", use_container_width=True, icon=":material/table:"
            ):
                output = extract(st.session_state.import_page["input"])
                data_ui(output)
        else:
            logger.debug("Data already extracted")
            st.button(
                "Extract Data",
                use_container_width=True,
                disabled=True,
                icon=":material/table:",
            )
            data_ui(st.session_state.import_page["output"])


def cleanSessionState():
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
    "Upload a file", type=["png", "jpg", "jpeg", "csv"], on_change=cleanSessionState
)

if file is None:
    if st.session_state.import_page["input"] is not None:
        logger.debug("Data already imported")
        if st.button("Clear Data", use_container_width=True, icon=":material/delete:"):
            cleanSessionState()
        else:
            drawUI()
    else:
        logger.debug("No file uploaded")
        cleanSessionState()
else:
    logger.debug("File: %s - file type: %s", file.name, file.type)

    if file.type == "application/vnd.ms-excel":
        logger.debug("CSV file detectimport_pageed")
        input_file = processCSV(file)
    else:
        logger.debug("Image file detected")
        input_file = processImg(file)
    st.session_state.import_page["type"] = file.type
    st.session_state.import_page["input"] = input_file
    drawUI()

logger.debug("## ended ##")
