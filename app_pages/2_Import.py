import traceback
import streamlit as st
import io
import os
import configparser
import logging
from modules import walletVision
from PIL import Image

logger = logging.getLogger(__name__)

def decodeImg(image_bytes) -> bytes:
    image_file = io.BytesIO(image_bytes)
    with processImg.open(image_file) as img:
        maxsize = 1280
        img.thumbnail((maxsize, maxsize), processImg.LANCZOS)
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
                        "Ethereum": "0.1425784 ETH",
                        "Bitcoin": "0.00771977 BTC",
                        "SwissBorg": "768.701597 BORG",
                        "Avalanche": "5.3228182 AVAX",
                        "Solana": "1.8795602 SOL",
                        "Polygon": "145.30894 MATIC",
                        "Optimism": "43.905634 OP",
                        "Polkadot": "14.1384258974 DOT",
                        "Cosmos": "8.213727 ATOM",
                    }
                else:
                    with st.spinner("Extracting data..."):
                        try:
                            message_json, tokens = walletVision.extract_crypto(imagefile, config["DEFAULT"]["openai_token"])
                        except KeyError as ke:
                            st.error("Error: " + type(ke).__name__ + " - " + str(ke))
                            st.error("Please set your settings in the settings page")
                            traceback.print_exc()
                            st.stop()
                        except Exception as e:
                            st.error("Error: " + str(e))
                            traceback.print_exc()
                            st.stop()
                
                st.write(message_json)
                st.balloons()

def processCSV(file) -> str:
    st.write(file.getvalue().decode("utf-8"))

configfilepath = "./data/settings.ini"
if not os.path.exists(configfilepath):
    st.error("Please set your settings in the settings page")
    st.stop()

config = configparser.ConfigParser()
config.read(configfilepath)

try:
    debugflag = (True if config["DEFAULT"]["debug"] == "True" else False)
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

