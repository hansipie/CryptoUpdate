import streamlit as st
import io

from time import sleep
from dotenv import load_dotenv
from modules import walletVision
from PIL import Image


def processImg(image_bytes) -> bytes:
    image_file = io.BytesIO(image_bytes)
    with Image.open(image_file) as img:
        maxsize = 1280
        img.thumbnail((maxsize, maxsize), Image.LANCZOS)
        img_bytes = io.BytesIO()
        img.save(img_bytes, format="PNG")
        return img_bytes.getvalue()


load_dotenv()

st.set_page_config(layout="wide")
st.title("Import")

file = st.file_uploader("Upload a file", type=["png", "jpg", "jpeg"])
if file is not None:
    imagefile = processImg(file.getvalue())
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
                with st.spinner("Extracting data..."):
                    message_json, tokens = walletVision.extract_crypto(imagefile)
                st.write(message_json)
                st.balloons()
