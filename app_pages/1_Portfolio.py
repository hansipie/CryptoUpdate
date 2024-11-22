import streamlit as st
import os
import configparser
import pandas as pd
import json

st.title("Portfolio")

@st.fragment
@st.dialog("Add new portfolio")
def add_new_portfolio():
    st.write("Add new portfolio")
    name = st.text_input("Name")
    description = st.text_input("Description")
    if st.button("Submit"):
        # Add new portfolio to session state
        st.session_state.portfolios[name] = {
            "description": description,
            "data": "{}"  # Initialize as empty JSON string
        }
        # Add new portfolio to ini file
        portfolio_config[name] = {
            "description": description,
            "data": "{}"  # Initialize as empty JSON string
        }
        with open(portfolio_ini_path, 'w') as portfoliofile:
            portfolio_config.write(portfoliofile)
        # Close dialog
        st.rerun()

@st.fragment
@st.dialog("Danger Zone")
def danger_zone(name : str):
    st.write(f"Delete portfolio {name}?")
    confirm = st.text_input("Type 'delete' to confirm")
    if st.button("Delete") and confirm == "delete":
        # Delete portfolio from session state
        st.session_state.portfolios.pop(name)
        # Delete portfolio from ini file
        portfolio_config.remove_section(name)
        with open(portfolio_ini_path, 'w') as file:
            portfolio_config.write(file)
        # Close dialog
        st.rerun()

@st.fragment
@st.dialog("Add Token")
def add_token(name : str):
    st.write(f"Add token to {name}")
    token = st.text_input("Token")
    amount = st.number_input("Amount", min_value=0.0, format="%.8f")
    if st.button("Submit"):
        # Parse the JSON string to dict before converting to DataFrame
        data = json.loads(st.session_state.portfolios[name]["data"])
        if data:
            df = pd.DataFrame.from_dict(data, orient="index")
        else:
            # Create empty DataFrame with Amount column
            df = pd.DataFrame(columns=['Amount'])
        # Add new token to DataFrame
        df.loc[token, 'Amount'] = amount
        # Convert updated DataFrame back to JSON string for storage
        st.session_state.portfolios[name]["data"] = json.dumps(df.to_dict(orient="index"))
        portfolio_config[name]["data"] = st.session_state.portfolios[name]["data"]
        with open(portfolio_ini_path, 'w') as file:
            portfolio_config.write(file)
        # Close dialog
        st.rerun()

@st.fragment
@st.dialog("Delete Token")
def delete_token(name : str):
    st.write(f"Delete token from {name}")
    token = st.selectbox("Token", list(json.loads(st.session_state.portfolios[name]["data"]).keys()))
    if st.button("Submit"):
        # Parse the JSON string to dict before converting to DataFrame
        data = json.loads(st.session_state.portfolios[name]["data"])
        df = pd.DataFrame.from_dict(data, orient="index")
        # Delete token from DataFrame
        df = df.drop(token)
        # Convert updated DataFrame back to JSON string for storage
        st.session_state.portfolios[name]["data"] = json.dumps(df.to_dict(orient="index"))
        portfolio_config[name]["data"] = st.session_state.portfolios[name]["data"]
        with open(portfolio_ini_path, 'w') as file:
            portfolio_config.write(file)
        # Close dialog
        st.rerun()

# Load portfolios from ini file
if not os.path.exists("./data"):
    os.makedirs("./data")
portfolio_ini_path = "./data/portfolio.ini"
portfolio_config = configparser.ConfigParser()
if not os.path.exists(portfolio_ini_path):
    with open(portfolio_ini_path, 'w') as file:
        portfolio_config.write(file)
else:
    portfolio_config.read(portfolio_ini_path)

# Load portfolios from session state
if "portfolios" not in st.session_state:
    st.session_state.portfolios = {}
    for section in portfolio_config.sections():
        st.session_state.portfolios[section] = {
            "description": portfolio_config[section]["description"],
            "data": portfolio_config[section]["data"]
        }

# Add new portfolio dialog
if st.sidebar.button("Add new portfolio"):
    add_new_portfolio()

# Display portfolios
tabs = []
for _, section in enumerate(st.session_state.portfolios):
    tabs.append(section)

if len(tabs) > 0:
    try:   
        tabs_widget = st.tabs(tabs)
        for i, tab in enumerate(tabs_widget):
            tab.write(st.session_state.portfolios[tabs[i]]["description"])
            # Parse the JSON string to dict before converting to DataFrame
            data = json.loads(st.session_state.portfolios[tabs[i]]["data"])
            if data:  # Only create DataFrame if data exists
                df = pd.DataFrame.from_dict(data, orient="index")
                updated_data = tab.data_editor(df)
                # Convert updated DataFrame back to JSON string for storage
                st.session_state.portfolios[tabs[i]]["data"] = json.dumps(updated_data.to_dict(orient="index"))
                portfolio_config[tabs[i]]["data"] = st.session_state.portfolios[tabs[i]]["data"]
                with open(portfolio_ini_path, 'w') as file:
                    portfolio_config.write(file)
            else:
                tab.write("No data available")
            
            if tab.button("Add Token", key=f"addT_{i}"):
                add_token(tabs[i])
            if tab.button("Delete Token", key=f"deleteT_{i}"):
                delete_token(tabs[i])
            if tab.button("Danger Zone", key=f"dangerZ_{i}"):
                danger_zone(tabs[i])
    except Exception as e:
        st.error(f"Error: {str(e)}")

st.write(st.session_state.portfolios)
