import traceback
import streamlit as st
import pandas as pd
import logging
from modules.database.portfolios import Portfolios
from modules.tools import update_database, create_portfolio_dataframe


logger = logging.getLogger(__name__)

st.title("Portfolios")


@st.dialog("Add new portfolio")
def add_new_portfolio():
    name = st.text_input("Name")
    if st.button("Submit"):
        logger.debug(f"Adding portfolio {name}")
        g_portfolios.add_portfolio(name)
        # Close dialog
        st.rerun()


@st.dialog("Danger Zone")
def danger_zone(name: str):
    st.write(f"Delete portfolio {name}?")
    confirm = st.text_input("Type 'delete' to confirm")
    if st.button("Delete") and confirm == "delete":
        g_portfolios.delete_portfolio(name)
        st.rerun()


@st.dialog("Rename portfolio")
def rename_portfolio(name: str):
    new_name = st.text_input("New name")
    if st.button("Submit"):
        g_portfolios.rename(name, new_name)
        st.rerun()


@st.dialog("Add Token")
def add_token(name: str):
    st.write(f"Add token to {name}")
    token = st.text_input("Token")
    token = token.upper()
    amount = st.number_input("Amount", min_value=0.0, format="%.8f")
    if st.button("Submit"):
        g_portfolios.set_token_add(name, token, amount)
        # Close dialog
        st.rerun()


@st.dialog("Delete Token")
def delete_token(name: str):
    st.write(f"Delete token from {name}")
    tokens = st.multiselect(
        "Token(s)",
        g_portfolios.get_tokens(name),
        placeholder="Select a token",
    )
    if st.button("Submit"):
        for token in tokens:
            g_portfolios.delete_token(name, token)
        # Close dialog
        st.rerun()


def portfolioUI(tabs: list):
    logger.debug(f"portfolioUI - Tabs: {tabs}")

    tabs_widget = st.tabs(tabs)

    for i, tab in enumerate(tabs_widget):
        with tab:
            pf = g_portfolios.get_portfolio(tabs[i])
            df = create_portfolio_dataframe(pf)
            if not df.empty:  # Only create DataFrame if data exists
                balance = df["value(€)"].sum()
                st.write(f"Total value: €{round(balance, 2)}")
                height = (len(df) * 35) + 38
                logger.debug(f"Dataframe:\n{df}")
                updated_data = st.data_editor(
                    df,
                    use_container_width=True,
                    height=height,
                    column_config={
                        "amount": st.column_config.NumberColumn(format="%.8g"),
                    },
                )
                if not updated_data.equals(df):
                    g_portfolios.update_portfolio(
                        {tabs[i]: updated_data.to_dict(orient="index")}
                    )
                    logger.debug("## Rerun ##")
                    st.rerun()
                else:
                    logger.debug("## No Rerun ##")
            else:
                st.write("No data available")

            buttons_col1, buttons_col2, buttons_col3, buttons_col4 = st.columns(4)
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
                    "Rename Portfolio",
                    key=f"rename_{i}",
                    use_container_width=True,
                    icon=":material/edit:",
                ):
                    rename_portfolio(tabs[i])
            with buttons_col4:
                if st.button(
                    "Danger Zone",
                    key=f"dangerZ_{i}",
                    use_container_width=True,
                    type="primary",
                    icon=":material/destruction:",
                ):
                    danger_zone(tabs[i])


def update():
    try:
        update_database(
            st.session_state.dbfile, st.session_state.settings["coinmarketcap_token"]
        )
        st.toast("Prices updated", icon=":material/check:")
        st.rerun()
    except Exception as e:
        st.error(f"Update Error: {str(e)}")


def load_portfolios(dbfile: str) -> Portfolios:
    return Portfolios(dbfile)


@st.fragment
def execute_search():
    df_search = pd.DataFrame.from_dict(
        g_portfolios.get_token_by_portfolio(st.session_state.search_target),
        orient="index",
        columns=["Amount"],
    )
    df_search.sort_index(inplace=True)
    logger.debug(f"Search result:\n{df_search}")
    st.dataframe(df_search, use_container_width=True)


g_portfolios = load_portfolios(st.session_state.dbfile)

with st.sidebar:
    # Add new portfolio dialog
    if st.button(
        "Add new portfolio",
        key="add_new_portfolio",
        icon=":material/note_add:",
        use_container_width=True,
    ):
        add_new_portfolio()

    # Update prices
    if st.button(
        "Update prices",
        key="update_prices",
        icon=":material/update:",
        use_container_width=True,
    ):
        update()

    st.divider()

    # search bar

    tokens = g_portfolios.aggregate_portfolios().keys()
    if st.selectbox(
        "Search", tokens, index=None, label_visibility="collapsed", key="search_target"
    ):
        execute_search()

# Display portfolios
tabs = g_portfolios.get_portfolio_names()
logger.debug(f"Portfolios: {tabs}")

try:
    portfolioUI(tabs)
except Exception as e:
    st.error(f"UI Error: {str(e)}")
    traceback.print_exc()
