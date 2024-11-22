import streamlit as st
import os
import configparser

st.title("Portfolio")

@st.fragment
@st.dialog("Add new portfolio")
def add_new_portfolio():
    st.write("Add new portfolio")
    name = st.text_input("Name")
    description = st.text_input("Description")
    if st.button("Submit"):
        # Add new portfolio to session state
        st.session_state.portfolios.append({
            "name": name,
            "description": description
        })
        # Add new portfolio to ini file
        portfolios[name] = {
            "description": description
        }
        with open(portfoliofilepath, 'w') as portfoliofile:
            portfolios.write(portfoliofile)
        # Close dialog
        st.rerun()

@st.fragment
@st.dialog("Danger Zone")
def danger_zone(i):
    name = st.text_input("Name", value=st.session_state.portfolios[i]["name"])
    tmp_name = name
    description = st.text_input("Description", value=st.session_state.portfolios[i]["description"])

    if st.button("Save"):
        # Update portfolio in session state
        st.session_state.portfolios[i]["name"] = name
        st.session_state.portfolios[i]["description"] = description
        # Update portfolio in ini file
        portfolios[name] = {
            "description": description
        }
        portfolios.remove_section(portfolio["name"])
        with open(portfoliofilepath, 'w') as portfoliofile:
            portfolios.write(portfoliofile)
        # Close dialog
        st.rerun()
        
    st.write(f"Delete portfolio {st.session_state.portfolios[i]["name"]}?")
    if st.button("Delete"):
        # Delete portfolio from session state
        st.session_state.portfolios.remove(st.session_state.portfolios[i])
        # Delete portfolio from ini file
        portfolios.remove_section(portfolio["name"])
        with open(portfoliofilepath, 'w') as portfoliofile:
            portfolios.write(portfoliofile)
        # Close dialog
        st.rerun()

# Load portfolios from ini file
if not os.path.exists("./data"):
    os.makedirs("./data")
portfoliofilepath = "./data/portfolio.ini"
portfolios = configparser.ConfigParser()
if not os.path.exists(portfoliofilepath):
    with open(portfoliofilepath, 'w') as portfoliofile:
        portfolios.write(portfoliofile)
else:
    portfolios.read(portfoliofilepath)

# Load portfolios from session state
if "portfolios" not in st.session_state:
    st.session_state.portfolios = []
    for portfolio in portfolios.sections():
        st.session_state.portfolios.append({
            "name": portfolio,
            "description": portfolios[portfolio]["description"]
        })

# Add new portfolio dialog
if st.sidebar.button("Add new portfolio"):
    add_new_portfolio()

# Display portfolios
tab = []
for portfolio in st.session_state.portfolios:
    tab.append(portfolio["name"])
tab.sort()

if len(tab) > 0:
    tabs = st.tabs(tab)
    for i, tab in enumerate(tabs):
        tab.write(st.session_state.portfolios[i])
        if tab.button("Danger Zone", key=f"dangerZ_{i}"):
            danger_zone(i)


st.write(st.session_state.portfolios)
