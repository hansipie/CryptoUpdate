import streamlit as st
import logging
import json
from modules.process import clean_price

logger = logging.getLogger(__name__)


class Portfolio:
    def __init__(self):
        self.file = "./data/portfolio.json"

        try:
            with open(self.file, "r") as file:
                self.portfolios = json.load(file)
        except FileNotFoundError:
            self.portfolios = {"portfolios": {}}
            with open(self.file, "w") as file:
                json.dump(self.portfolios, file)
        if "portfolios" not in self.portfolios:
            self.portfolios["portfolios"] = {}
        logger.debug(f"Portfolios from JSON: {self.portfolios}")

        st.session_state.portfolios = self.portfolios["portfolios"]
        logger.debug(f"Session state portfolios: {st.session_state.portfolios}")

    def save(self):
        logger.debug(f"Saving portfolio to {self.file}")
        # Format the portfolios data
        formatted_portfolios = {
            portfolio_name: {
                token: {"amount": clean_price(token_data["amount"])}
                for token, token_data in portfolio_data.items()
            }
            for portfolio_name, portfolio_data in st.session_state.portfolios.items()
        }

        self.portfolios["portfolios"] = formatted_portfolios
        logger.debug(f"Portfolios to save: {self.portfolios}")
        with open(self.file, "w") as file:
            json.dump(self.portfolios, file, indent=2)
        logger.debug(f"Portfolio saved done.")

    def add(self, name: str):
        st.session_state.portfolios[name] = {}
        self.save()

    def delete(self, name: str):
        st.session_state.portfolios.pop(name)
        self.save()

    def set_token(self, name: str, token: str, amount: float):
        if name not in st.session_state.portfolios:
            st.session_state.portfolios[name] = {}
        st.session_state.portfolios[name][token] = {"amount": amount}
        self.save()

    def add_token(self, name: str, token: str, amount: float):
        if name not in st.session_state.portfolios:
            st.session_state.portfolios[name] = {}
        st.session_state.portfolios[name][token] = {
            "amount": float(st.session_state.portfolios[name][token]["amount"])
            + float(amount)
        }
        self.save()

    def delete_token(self, name: str, token: str):
        if (
            name in st.session_state.portfolios
            and token in st.session_state.portfolios[name]
        ):
            st.session_state.portfolios[name].pop(token)
            self.save()
