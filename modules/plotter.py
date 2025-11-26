import logging
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

logger = logging.getLogger(__name__)


def plot_as_pie(df: pd.DataFrame, column):
    logger.debug("Plot with Plotly")
    if df.empty:
        st.info("No data available")
        return

    total = df[column].sum()
    limit = (1 * total) / 100
    logger.debug(f"1% of {total} is {limit}")

    # Group token representing less then 1% of total value
    dffinal = df.loc[df[column] >= limit]
    logger.debug(f"Dataframe more than {limit}:\n{dffinal}")

    dfless = df.loc[df[column] < limit]
    if not dfless.empty:
        logger.debug(f"Dataframe less than {limit}:\n{dfless}")

        dfless_sum = pd.DataFrame(dfless.sum()).T
        dfless_sum.index = ["Others"]
        logger.debug(f"Dataframe less than 1% sum:\n{dfless_sum}")

        dffinal = pd.concat([dffinal, dfless_sum])
        logger.debug(f"Dataframe more than 1% sum with Others:\n{dffinal}")

    fig = px.pie(dffinal, dffinal.index, column, width=700, height=700)
    st.plotly_chart(fig, width='stretch')


def plot_as_graph(df: pd.DataFrame):
    logger.debug("Plot with Plotly")
    if df.empty:
        st.info("No data available")
        return

    fig = go.Figure()

    # Ajouter la première trace en utilisant l'axe y par défaut (yaxis)
    fig.add_trace(go.Scatter(x=df.index, y=df[df.columns[0]], name=df.columns[0]))

    # Pour les colonnes suivantes, créer un nouvel axe y (yaxis2, yaxis3, etc.)
    for i, col in enumerate(df.columns[1:], start=2):
        fig.add_trace(go.Scatter(x=df.index, y=df[col], name=col, yaxis=f"y{i}"))
        # Ajout ou mise à jour de l'axe y additionnel dans la configuration de la mise en page
        fig.update_layout(
            {
                f"yaxis{i}": {
                    "title": col,
                    "overlaying": "y",  # Superpose cet axe sur le premier axe y
                    "side": "right",  # Place l'axe à droite (vous pouvez ajuster la position)
                }
            }
        )

    # Définir le titre de l'axe y par défaut pour la première colonne
    fig.update_layout(yaxis={"title": df.columns[0]})

    st.plotly_chart(fig)
