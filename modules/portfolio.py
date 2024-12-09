import streamlit as st
import logging
import sqlite3
from modules.process import clean_price

logger = logging.getLogger(__name__)


class Portfolios:
    def __init__(self, db_path: str = "./data/db.sqlite3"):
        self.db_path = db_path
        
        # Créer les tables si elles n'existent pas
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS Portfolios (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT UNIQUE NOT NULL
                )
            ''')
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS Tokens_PF (
                    portfolio_id INTEGER,
                    token TEXT,
                    amount TEXT,
                    PRIMARY KEY (portfolio_id, token),
                    FOREIGN KEY (portfolio_id) REFERENCES Portfolios(id)
                )
            ''')
            conn.commit()
        
        self._load_portfolios()

    def _load_portfolios(self):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT id, name FROM Portfolios')
            portfolio_rows = cursor.fetchall()
            
            portfolios = {}
            for p_id, name in portfolio_rows:
                portfolios[name] = {}
                # Charger les tokens pour ce portfolio
                cursor.execute('SELECT token, amount FROM Tokens_PF WHERE portfolio_id = ?', (p_id,))
                for token, amount in cursor.fetchall():
                    portfolios[name][token] = {"amount": amount}
            
            st.session_state.portfolios = portfolios

    def save(self):
        logger.debug("Saving portfolios to database")
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Vider les tables
            cursor.execute('DELETE FROM Tokens_PF')
            cursor.execute('DELETE FROM Portfolios')
            
            # Insérer les portfolios
            for portfolio_name in st.session_state.portfolios:
                cursor.execute('INSERT INTO Portfolios (name) VALUES (?)', (portfolio_name,))
                portfolio_id = cursor.lastrowid
                
                # Insérer les tokens
                for token, token_data in st.session_state.portfolios[portfolio_name].items():
                    amount = clean_price(token_data["amount"])
                    cursor.execute(
                        'INSERT INTO Tokens_PF (portfolio_id, token, amount) VALUES (?, ?, ?)',
                        (portfolio_id, token, amount)
                    )
            conn.commit()

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
        if token not in st.session_state.portfolios[name]:
            st.session_state.portfolios[name][token] = {"amount": "0"}
        current_amount = float(st.session_state.portfolios[name][token]["amount"])
        st.session_state.portfolios[name][token] = {
            "amount": str(current_amount + float(amount))
        }
        self.save()

    def delete_token(self, name: str, token: str):
        if name in st.session_state.portfolios and token in st.session_state.portfolios[name]:
            st.session_state.portfolios[name].pop(token)
            self.save()

    def rename(self, old_name: str, new_name: str):
        if old_name in st.session_state.portfolios:
            if new_name not in st.session_state.portfolios:  # Éviter les doublons
                # Modifier dans session_state
                st.session_state.portfolios[new_name] = st.session_state.portfolios.pop(old_name)
                
                # Mise à jour dans la base de données
                with sqlite3.connect(self.db_path) as conn:
                    cursor = conn.cursor()
                    cursor.execute('UPDATE Portfolios SET name = ? WHERE name = ?', 
                                 (new_name, old_name))
                    conn.commit()
            else:
                raise ValueError(f"Un portfolio nommé '{new_name}' existe déjà")
        else:
            raise ValueError(f"Le portfolio '{old_name}' n'existe pas")
