import logging
import streamlit as st
import pandas as pd
import plotly.express as px

logger = logging.getLogger(__name__)


def plot_as_pie(df: pd.DataFrame, column):
    logger.debug("Plot with Plotly")
    if df.empty:
        st.error("No data to plot")
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
        dfless_sum.index = ['Others']
        logger.debug(f"Dataframe less than 1% sum:\n{dfless_sum}")

        dffinal = pd.concat([dffinal, dfless_sum])
        logger.debug(f"Dataframe more than 1% sum with Others:\n{dffinal}")

    fig = px.pie(dffinal, dffinal.index, column, width=700, height=700)
    st.plotly_chart(fig, use_container_width=True)

def plot_as_graph(df: pd.DataFrame, st_object=None):
    logger.debug(f"Plot with Plotly - StreamlitObject: {st_object}")
    if df.empty:
        st.error("No data to plot")
        return
    # Create custom chart with linear time scale
    fig = px.line(df, x=df.index, y=df.columns)
    if st_object:
        st_object.plotly_chart(fig)
    else:
        st.plotly_chart(fig)
