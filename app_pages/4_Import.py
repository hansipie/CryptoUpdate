from json import loads
import traceback
import streamlit as st
import io
import logging
import pandas as pd
from modules import aiprocessing
from modules.database import portfolios as pf
from modules.database.operations import operations
from modules.database.swaps import swaps
from PIL import Image

logging.getLogger("PIL").setLevel(logging.WARNING)


logger = logging.getLogger(__name__)


@st.cache_data
def decodeImg(image_bytes) -> bytes:
    logger.debug("Decoding image")
    image_file = io.BytesIO(image_bytes)
    with Image.open(image_file) as img:
        maxsize = 768
        img.thumbnail((maxsize, maxsize), Image.LANCZOS)
        img_bytes = io.BytesIO()
        img.save(img_bytes, format="PNG")
    logger.debug("Image decoded: " + str(len(img_bytes.getvalue())) + " bytes")
    return img_bytes.getvalue()


@st.fragment
def dataUI(df: pd.DataFrame) -> pd.DataFrame:
    # add column for portfolios
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
        saveData(st.session_state.import_page["output"], portfolios, action)

    logger.debug("Fragment ended")


def extract(input: any) -> pd.DataFrame:
    logger.debug("Extracting data")
    output = None
    with st.spinner("Extracting data..."):
        try:
            if isinstance(input, bytes):
                message_json, _ = aiprocessing.extract_from_img(
                    input, st.session_state.settings["openai_token"]
                )
                output = pd.DataFrame.from_dict(loads(message_json).get("assets"))
            elif isinstance(input, pd.DataFrame):
                message_json, _ = aiprocessing.extract_from_df(
                    input, st.session_state.settings["openai_token"]
                )
                output = pd.DataFrame.from_dict(loads(message_json).get("assets"))
            else:
                raise ValueError("Invalid input type")
        except KeyError as ke:
            st.error("Error: " + type(ke).__name__ + " - " + str(ke))
            st.error("Please set your settings in the settings page")
            traceback.print_exc()
            st.stop()
        except Exception as e:
            st.error("Error: " + str(e))
            traceback.print_exc()
            st.stop()

    output["select"] = False
    return output


def saveData(df: pd.DataFrame, portfolio: str = None, action: str = "Set"):
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
            logger.debug(f"Saving data: {data}")
            tokens[data["symbol"]] = {"amount": data["amount"]}
            if action == "Set":
                g_portfolio.set_token(portfolio, data["symbol"], data["amount"])
            elif action == "Add":
                g_portfolio.set_token_add(portfolio, data["symbol"], data["amount"])
    st.toast("Data successfully saved", icon="✔️")


def processImg(file) -> bytes:
    logger.debug("Processing image")
    ret = decodeImg(file.getvalue())
    logger.debug("Image processed")
    return ret


@st.cache_data
def processCSV(file) -> pd.DataFrame:
    logger.debug("Processing CSV")
    return pd.read_csv(file)


def drawUI():
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
                dataUI(output)
        else:
            logger.debug("Data already extracted")
            st.button(
                "Extract Data",
                use_container_width=True,
                disabled=True,
                icon=":material/table:",
            )
            dataUI(st.session_state.import_page["output"])


def cleanSessionState():
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

g_portfolio = pf.Portfolios()

st.title("Import")

ai_tab, tests_tab = st.tabs(["AI", "Test"])

with ai_tab:
    file = st.file_uploader(
        "Upload a file", type=["png", "jpg", "jpeg", "csv"], on_change=cleanSessionState
    )

    if file is None:
        if st.session_state.import_page["input"] is not None:
            logger.debug("Data already imported")
            if st.button(
                "Clear Data", use_container_width=True, icon=":material/delete:"
            ):
                cleanSessionState()
            else:
                drawUI()
        else:
            logger.debug("No file uploaded")
            cleanSessionState()
    else:
        logger.debug(f"File: {file.name} - file type: {file.type}")

        if file.type == "application/vnd.ms-excel":
            logger.debug("CSV file detectimport_pageed")
            input = processCSV(file)
        else:
            logger.debug("Image file detected")
            input = processImg(file)
        st.session_state.import_page["type"] = file.type
        st.session_state.import_page["input"] = input
        drawUI()

with tests_tab:
    file = st.file_uploader("Upload Swap file", type=["csv"])
    if file is not None:
        df = pd.read_csv(file)

        # clean up column names
        df.columns = df.columns.str.strip().str.lower().str.replace(" ", "")

        df.sort_values(by="timestamp", inplace=True)
        st.dataframe(df)

        if st.button("Import"):
            swaps = swaps()
            for index, row in df.iterrows():
                logger.debug(f"\n{row}")
                swaps.insert(
                    row["timestamp"],
                    row["token_from"],
                    row["amount_from"],
                    None,
                    row["token_to"],
                    row["amount_to"],
                    None,
                )
            st.success("Import successfully completed")

    st.divider()

    file = st.file_uploader("Upload Buy file", type=["csv"])
    if file is not None:
        df = pd.read_csv(file)

        # Conversion de la date en timestamp
        if "Creation Date" in df.columns:
            df["Timestamp"] = (
                pd.to_datetime(df["Creation Date"], format="%B %d, %Y %I:%M %p").astype(
                    "int64"
                )
                // 10**9
            )

        # Nettoyage de la colonne Dashboard
        if "Dashboard" in df.columns:
            df["Dashboard"] = (
                df["Dashboard"].str.replace(r"\s*\([^)]*\)", "", regex=True).str.strip()
            )

        # Nettoyage de la colonne Value HT (€)
        if "Value HT (€)" in df.columns:
            df["Value HT (€)"] = df["Value HT (€)"].str.replace("€", "").astype(float)

        df.sort_values(by="Timestamp", inplace=True)
        st.dataframe(df)

        if st.button("Import"):
            operation = operations()
            for index, row in df.iterrows():
                operation.insert(
                    "buy",
                    row["Value HT (€)"],
                    row["Coins Amount"],
                    "EUR",
                    row["Dashboard"],
                    row["Timestamp"],
                    None,
                )
            st.success("Import successfully completed")

logger.debug("## ended ##")
