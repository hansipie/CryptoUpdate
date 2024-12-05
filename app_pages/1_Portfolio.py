import streamlit as st
import os
import configparser
import pandas as pd
import logging
from modules import portfolio as pf


logger = logging.getLogger(__name__)

st.title("Portfolio")


@st.fragment
@st.dialog("Add new portfolio")
def add_new_portfolio():
    name = st.text_input("Name")
    if st.button("Submit"):
        g_portfolios.add(name)
        # Close dialog
        st.rerun()


@st.fragment
@st.dialog("Danger Zone")
def danger_zone(name: str):
    st.write(f"Delete portfolio {name}?")
    confirm = st.text_input("Type 'delete' to confirm")
    if st.button("Delete") and confirm == "delete":
        g_portfolios.delete(name)
        st.rerun()


@st.fragment
@st.dialog("Add Token")
def add_token(name: str):
    st.write(f"Add token to {name}")
    token = st.text_input("Token")
    token = token.upper()
    amount = st.number_input("Amount", min_value=0.0, format="%.8f")
    if st.button("Submit"):
        g_portfolios.add_token(name, token, amount)
        # Close dialog
        st.rerun()


@st.fragment
@st.dialog("Delete Token")
def delete_token(name: str):
    st.write(f"Delete token from {name}")
    token = st.selectbox(
        "Token", list(st.session_state.portfolios[name].keys())
    )
    if st.button("Submit"):
        g_portfolios.delete_token(name, token)
        # Close dialog
        st.rerun()


def portfolioUI(tabs: list):
    logger.debug(f"portfolioUI - Tabs: {tabs}")

    tabs_widget = st.tabs(tabs)

    for i, tab in enumerate(tabs_widget):
        data = st.session_state.portfolios[tabs[i]]
        logger.debug(f"Data: {data}")
        if data:  # Only create DataFrame if data exists
            df = pd.DataFrame.from_dict(data, orient="index")
            updated_data = tab.data_editor(df)
            if not updated_data.equals(df):
                # Convert updated DataFrame back to storage format
                st.session_state.portfolios[tabs[i]] = updated_data.to_dict(orient="index")
                g_portfolios.save()
                logger.debug("## Rerun ##")
                st.rerun()
            else:
                logger.debug("## No Rerun ##")
        else:
            tab.write("No data available")

        buttons_col1, buttons_col2, buttons_col3 = tab.columns(3)
        with buttons_col1:
            if st.button(
                "Add Token",
                key=f"addT_{i}",
                use_container_width=True,
                icon=":material/add:",
            ):
                add_token(tabs[i])
        with buttons_col2:
            if st.button(
                "Delete Token",
                key=f"deleteT_{i}",
                use_container_width=True,
                icon=":material/delete:",
            ):
                delete_token(tabs[i])
        with buttons_col3:
            if st.button(
                "Danger Zone",
                key=f"dangerZ_{i}",
                use_container_width=True,
                type="primary",
                icon=":material/destruction:",
            ):
                danger_zone(tabs[i])
    st.write(st.session_state)

logger.debug("#### Start Render ####")

g_portfolios = pf.Portfolio()

# Add new portfolio dialog
if st.sidebar.button(
    "Add new portfolio", key="add_new_portfolio", icon=":material/note_add:"
):
    add_new_portfolio()

# Display portfolios
tabs = []
for _, section in enumerate(st.session_state.portfolios):
    tabs.append(section)

if len(tabs) > 0:
    try:
        portfolioUI(tabs)
    except Exception as e:
        st.error(f"Error: {str(e)}")

logger.debug("#### End Render ####")
