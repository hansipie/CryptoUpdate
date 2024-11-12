from json import loads, dumps
import traceback
import streamlit as st
import io
import os
import configparser
import logging
import pandas as pd
from modules import walletVision
from PIL import Image

logger = logging.getLogger(__name__)


def decodeImg(image_bytes) -> bytes:
    image_file = io.BytesIO(image_bytes)
    with Image.open(image_file) as img:
        maxsize = 768
        img.thumbnail((maxsize, maxsize), Image.LANCZOS)
        img_bytes = io.BytesIO()
        img.save(img_bytes, format="PNG")
    return img_bytes.getvalue()


def processImg(file):
    imagefile = decodeImg(file.getvalue())
    with st.form(key="my_form"):
        col_img, col_json = st.columns(2)
        with col_img:
            st.image(imagefile)
        with col_json:
            submit_button = st.form_submit_button(
                label="Extract data",
                help="Extract data from the image.",
                use_container_width=True,
            )
            if submit_button:
                if debugflag:
                    message_json = {
                        "Best Blockchains": "€ 2,130.18",
                        "Solana": {"value": "€ 1,991.66", "amount": "10.59116226 SOL"},
                        "Bitcoin": {"value": "€ 1,802.29", "amount": "0.02522609 BTC"},
                        "USD Coin": {"value": "€ 997.42", "amount": "1,068.6508 USDC"},
                        "Ethereum": {"value": "€ 979.92", "amount": "0.3468965 ETH"},
                        "SwissBorg": {
                            "value": "€ 411.99",
                            "amount": "2,262.907403 BORG",
                        },
                        "Golden": "€ 344.89",
                        "Xborg": {"value": "€ 262.94", "amount": "1,096.309539 XBG"},
                    }
                else:
                    with st.spinner("Extracting data..."):
                        try:
                            message_json, tokens = walletVision.extract_crypto(
                                imagefile, config["DEFAULT"]["openai_token"]
                            )
                        except KeyError as ke:
                            st.error("Error: " + type(ke).__name__ + " - " + str(ke))
                            st.error("Please set your settings in the settings page")
                            traceback.print_exc()
                            st.stop()
                        except Exception as e:
                            st.error("Error: " + str(e))
                            traceback.print_exc()
                            st.stop()
                
                st.json(message_json)
                st.balloons()


def processCSV(file) -> str:
    df = pd.read_csv(file)

    with st.form(key="my_form"):
        col_data, col_json = st.columns(2)
        with col_data:
            st.data_editor(df, hide_index=True, use_container_width=True)
        with col_json:
            submit_button = st.form_submit_button(
                label="Extract data",
                help="Extract data from the dataframe.",
                use_container_width=True,
            )
            if submit_button:
                with st.spinner("Extracting data..."):
                    message_json = df.to_json(orient="records")

                st.json(message_json)
                st.balloons()


configfilepath = "./data/settings.ini"
if not os.path.exists(configfilepath):
    st.error("Please set your settings in the settings page")
    st.stop()

config = configparser.ConfigParser()
config.read(configfilepath)

try:
    debugflag = True if config["DEFAULT"]["debug"] == "True" else False
except KeyError:
    debugflag = False

st.title("Import")

file = st.file_uploader("Upload a file", type=["png", "jpg", "jpeg", "csv"])

if file is not None:
    logger.debug(f"File: {file} - file type: {file.type}")
    if file.type == "application/vnd.ms-excel":
        st.write("CSV file detected")
        processCSV(file)
    else:
        st.write("Image file detected")
        processImg(file)
