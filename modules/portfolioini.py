import streamlit as st
import os
import configparser
import logging
import json

logger = logging.getLogger(__name__)

portfolio_ini_path = "./data/portfolio.ini"


def loadPortfoliosIni() -> configparser.ConfigParser:
    # Load portfolios from ini file

    logger.debug(f"Portfolio ini path: {portfolio_ini_path}")

    if not os.path.exists(os.path.dirname(portfolio_ini_path)):
        os.makedirs(os.path.dirname(portfolio_ini_path))

    portfolio_config = configparser.ConfigParser()
    if not os.path.exists(portfolio_ini_path):
        logger.debug("Creating portfolio.ini file")
        with open(portfolio_ini_path, "w") as file:
            portfolio_config.write(file)
    else:
        logger.debug("Reading portfolio.ini file")
        portfolio_config.read(portfolio_ini_path)
    return portfolio_config


def savePortfoliosIni(portfolio_config: configparser.ConfigParser):
    # Save portfolios to ini file
    logger.debug(f"Portfolio ini path: {portfolio_ini_path}")

    with open(portfolio_ini_path, "w") as file:
        portfolio_config.write(file)


def loadPortfoliosSession(portfolio_config: configparser.ConfigParser):
    # Load portfolios from session state
    if "portfolios" not in st.session_state:
        st.session_state.portfolios = {}
        for section in portfolio_config.sections():
            st.session_state.portfolios[section] = {
                "data": portfolio_config[section]["data"]
            }


# def setPortfolio(name: str, data: dict):
#     # Set portfolio data
#     st.write(f"Setting portfolio {name} with data {data}")
#     crypto_dict = json.loads(st.session_state.portfolios[name]["data"])
#     if crypto_dict:
#         crypto_dict[data["symbol"]]["amount"] = data["amount"]
#         st.session_state.portfolios[name]["data"] = json.dumps(crypto_dict.to_dict(orient="index"))


# def addPortfolio(name: str, data: dict):
#     st.session_state.portfolios[name]["data"][data.symbol] += data.amount
