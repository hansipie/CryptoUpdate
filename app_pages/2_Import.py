from json import loads, dumps
import traceback
import streamlit as st
import io
import os
import configparser
import logging
import pandas as pd
from modules import aiprocessing
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

def extract_gui(input: any):
    submit_button = st.form_submit_button(
        label="Extract data",
        help="Extract data from the image.",
        use_container_width=True,
    )
    if submit_button:
        with st.spinner("Extracting data..."):
            try:
                if isinstance(input, bytes):
                    message_json, _ = aiprocessing.extract_from_img(
                        input, config["DEFAULT"]["openai_token"]
                    )
                    st.session_state.import_output = pd.DataFrame.from_dict(loads(message_json).get("assets"))
                elif isinstance(input, pd.DataFrame):
                    message_json, _ = aiprocessing.extract_from_df(
                        input, config["DEFAULT"]["openai_token"]
                    )
                    st.session_state.import_output = pd.DataFrame.from_dict(loads(message_json).get("assets"))
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
        
        st.dataframe(st.session_state.import_output, use_container_width=True)
        st.balloons()


def processImg(file):
    imagefile = decodeImg(file.getvalue())
    st.session_state.import_input = imagefile
    st.session_state.import_output = None

    with st.form(key="extract_form"):
        col_img, col_json = st.columns(2)
        with col_img:
            st.image(imagefile)
        with col_json:
            extract_gui(imagefile)

def processCSV(file) -> str:
    st.session_state.import_input = pd.read_csv(file)
    
    with st.form(key="extract_form"):
        col_input, col_output = st.columns(2)
        with col_input:
            st.dataframe(st.session_state.import_input, use_container_width=True)
        with col_output:
            extract_gui(st.session_state.import_input)

# session state variable
if "import_input" not in st.session_state:
    st.session_state.import_input = None
if "import_output" not in st.session_state:
    st.session_state.import_output = None
if "import_type" not in st.session_state:
    st.session_state.import_type = None

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
    st.session_state.import_type = file.type

    if st.session_state.import_type == "application/vnd.ms-excel":
        logger.debug("CSV file detected")
        processCSV(file)
    else:
        logger.debug("Image file detected")
        processImg(file)

elif st.session_state.import_input is not None:

    with st.form(key="extract_form"):
        col_input, col_output = st.columns(2)
        with col_input:
            if st.session_state.import_type == "application/vnd.ms-excel":
                st.dataframe(st.session_state.import_input, use_container_width=True)
            else:
                st.image(st.session_state.import_input)
        with col_output:
            extract_gui(st.session_state.import_input)




# Display session state variables
with st.expander("type:"):
    st.write(st.session_state.import_type)
with st.expander("Input:"):
    st.write(st.session_state.import_input)
with st.expander("Output:"):
    st.write(st.session_state.import_output)