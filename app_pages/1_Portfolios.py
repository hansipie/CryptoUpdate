import streamlit as st
import pandas as pd
import logging
from modules import portfolio as pf
from modules.process import clean_price, get_current_price


logger = logging.getLogger(__name__)

st.title("Portfolios")


@st.fragment
@st.dialog("Add new portfolio")
def add_new_portfolio():
    name = st.text_input("Name")
    if st.button("Submit"):
        logger.debug(f"Adding portfolio {name}")
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
    token = st.selectbox("Token", list(st.session_state.portfolios[name].keys()))
    if st.button("Submit"):
        g_portfolios.delete_token(name, token)
        # Close dialog
        st.rerun()


@st.cache_data
def makedf(data: dict) -> pd.DataFrame:
    logger.debug(f"makedf - Data: {data}")
    df = pd.DataFrame(data).T
    df.index.name = "Token"
    # rename column amount and convert to float
    df.rename(columns={"amount": "Amount"}, inplace=True)
    df["Amount"] = df.apply(lambda row: clean_price(row["Amount"]), axis=1)
    # Ajouter une colonne "Value" basée sur le cours actuel
    df["Value(€)"] = df.apply(
        lambda row: round(clean_price(row["Amount"]) * get_current_price(row.name), 2),
        axis=1,
    )

    return df


def portfolioUI(tabs: list):
    logger.debug(f"portfolioUI - Tabs: {tabs}")

    tabs_widget = st.tabs(tabs)

    for i, tab in enumerate(tabs_widget):
        with tab:
            data = st.session_state.portfolios[tabs[i]]
            logger.debug(f"Data: {data}")
            if data:  # Only create DataFrame if data exists
                df = makedf(data)
                updated_data = st.data_editor(df, use_container_width=True)
                if not updated_data.equals(df):
                    # Convert updated DataFrame back to storage format
                    st.session_state.portfolios[tabs[i]] = updated_data.to_dict(
                        orient="index"
                    )
                    g_portfolios.save()
                    logger.debug("## Rerun ##")
                    st.rerun()
            else:
                st.write("No data available")

            buttons_col1, buttons_col2, buttons_col3 = st.columns(3)
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

    with st.expander("Debug"):
        st.write(st.session_state)

g_portfolios = pf.Portfolios()

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
