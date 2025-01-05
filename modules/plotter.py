import logging
import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates

logger = logging.getLogger(__name__)


def plot_as_pie(df):
    # find value of 1% of the total
    total = df.sum(axis=1).values[0]
    if total == 0:
        st.error("No data to plot")
        return
    limit = (1 * total) / 100
    logger.debug(f"1% of {total} is {limit}")

    # Group token representing less then 1% of total value
    dfothers = df.loc[:, (df < limit).all(axis=0)]
    df = df.loc[:, (df >= limit).all(axis=0)]
    df["Others"] = dfothers.sum(axis=1)

    labels = df.columns.tolist()
    values = df.values.tolist()[0]
    logger.info(f"Pie labels: {labels}")
    logger.info(f"Pie values: {values}")

    plt.figure(figsize=(10, 10), facecolor="white")
    ax1 = plt.subplot()
    ax1.pie(values, labels=labels)
    st.pyplot(plt)


def plot_as_graph(df, options=None, count=None, tab=None):
    logger.debug(f"Plot as graph - Options: {options}, Count: {count}, Tab: {tab}")
    if df.empty:
        st.error("No data to plot")
        return
    # Create custom chart with linear time scale
    fig, ax = plt.subplots(figsize=(10, 6))
    df.index = pd.to_datetime(df.index)
    if options and count is not None:
        ax.plot(df.index, df[options[count]].values)
    else:
        ax.plot(df.index, df.values)

    # Set x-axis to use dates with fixed intervals
    ax.xaxis.set_major_locator(mdates.AutoDateLocator())
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m-%d"))
    plt.xticks(rotation=45)

    # Set labels
    ax.set_xlabel("Date")
    ax.set_ylabel("Value (€)")

    # Adjust layout and display the plot
    plt.tight_layout()
    if tab:
        tab.pyplot(fig)
    else:
        st.pyplot(fig)
