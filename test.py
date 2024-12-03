import streamlit as st

st.title("My Awesome App")

@st.fragment()
def toggle_and_text():
    cols = st.columns(2)
    cols[0].toggle("Toggle")
    cols[1].text_area("Enter text")

@st.fragment()
def filter_and_file():
    cols = st.columns(2)
    cols[0].checkbox("Filter")
    cols[1].file_uploader("Upload image")

toggle_and_text()
cols = st.columns(2)
cols[0].selectbox("Select", [1,2,3], None)
cols[1].button("Update")
filter_and_file()
