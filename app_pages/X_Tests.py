import logging
import os
import sqlite3
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime

import pandas as pd
import streamlit as st


logger = logging.getLogger(__name__)

st.title("Tests")


def find_missing_dates(dbfile: str) -> list:
    """Find all dates with no data in the database.

    Args:
        dbfile: Path to the SQLite database file

    Returns:
        List of dates (as strings) with no data
    """
    with sqlite3.connect(dbfile) as con:
        # Get all unique dates from the database
        query = """
        SELECT DISTINCT date(timestamp, 'unixepoch') as date
        FROM TokensDatabase
        ORDER BY date
        """
        df_dates = pd.read_sql_query(query, con)

        if df_dates.empty:
            logger.warning("No data found in database")
            return []

        # Convert to datetime
        df_dates['date'] = pd.to_datetime(df_dates['date'])
        existing_dates = set(df_dates['date'].dt.date)

        # Get the first and last dates
        first_date = df_dates['date'].min().date()
        last_date = df_dates['date'].max().date()

        # Generate all dates between first and last
        all_dates = pd.date_range(start=first_date, end=last_date, freq='D')
        all_dates_set = set(all_dates.date)

        # Find missing dates
        missing_dates = sorted(all_dates_set - existing_dates)

        return missing_dates


def check_api_data_for_date(api_url: str, date) -> bool:
    """Check if MarketRaccoon API has cryptocurrency data for a specific date.

    Args:
        api_url: Base URL of the MarketRaccoon API
        date: Date to check (datetime.date object)

    Returns:
        True if API has at least one cryptocurrency data point for that day, False otherwise
    """
    try:
        import requests

        # Create start and end of day in ISO format
        start_dt = datetime.combine(date, datetime.min.time())
        end_dt = datetime.combine(date, datetime.max.time())

        # Convert to ISO 8601 format for API
        startdate = start_dt.isoformat() + 'Z'
        enddate = end_dt.isoformat() + 'Z'

        # Query the API for cryptocurrency data for the entire day
        # Use page_size=1 to minimize data transfer (we only need to know if data exists)
        request = requests.get(
            api_url + "/api/v1/cryptocurrency",
            params={
                "startdate": startdate,
                "enddate": enddate,
                "page_size": 1
            },
            timeout=10,
        )

        if request.status_code == 200:
            data = request.json()
            results = data.get("results", [])

            # If we have at least one result for this day, return True
            if results and len(results) > 0:
                logger.debug("Found %d cryptocurrency data points for date %s", len(results), date)
                return True
            else:
                logger.debug("No cryptocurrency data points for date %s", date)
                return False

        elif request.status_code == 204:
            # No data available
            logger.debug("API returned 204 (no content) for date %s", date)
            return False
        else:
            logger.warning("API returned status %s for date %s", request.status_code, date)
            return False

    except Exception as e:
        logger.error("Error checking API for date %s: %s", date, str(e))
        return False


# Display missing dates section
st.header("Missing Data Analysis")

with st.spinner("Analyzing database for missing dates..."):
    missing_dates = find_missing_dates(st.session_state.settings["dbfile"])

if missing_dates:
    st.warning(f"Found {len(missing_dates)} days with no data in the database")

    # Display statistics
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Total Missing Days", len(missing_dates))
    with col2:
        st.metric("First Missing Date", str(missing_dates[0]))
    with col3:
        st.metric("Last Missing Date", str(missing_dates[-1]))

    # Display the list
    st.subheader("Missing Dates")

    # Convert to DataFrame for better display
    df_missing = pd.DataFrame(missing_dates, columns=["Date"])
    df_missing['Day of Week'] = pd.to_datetime(df_missing['Date']).dt.day_name()

    # Add button to check API
    check_api = st.button("Check MarketRaccoon API", type="primary")

    if check_api:
        # Check API for each missing date
        st.info("Checking MarketRaccoon API for cryptocurrency data availability...")

        # Get API URL from settings
        api_url = st.session_state.settings["marketraccoon_url"]

        # Check each date with parallel requests (10 at a time)
        api_status_dict = {}
        progress_bar = st.progress(0)
        status_text = st.empty()

        # Use ThreadPoolExecutor to make 10 requests in parallel
        with ThreadPoolExecutor(max_workers=10) as executor:
            # Submit all tasks
            future_to_date = {
                executor.submit(check_api_data_for_date, api_url, date): date
                for date in missing_dates
            }

            # Process completed tasks
            completed = 0
            for future in as_completed(future_to_date):
                date = future_to_date[future]
                try:
                    has_data = future.result()
                    api_status_dict[date] = "✅" if has_data else "❌"
                except Exception as e:
                    logger.error("Error checking date %s: %s", date, str(e))
                    api_status_dict[date] = "❌"

                completed += 1
                status_text.text(f"Checking dates: {completed}/{len(missing_dates)}")
                progress_bar.progress(completed / len(missing_dates))

        progress_bar.empty()
        status_text.empty()

        # Sort results by date to maintain original order
        api_status = [api_status_dict[date] for date in missing_dates]

        # Add API status column
        df_missing['API Data'] = api_status

        # Display with scrollable dataframe
        st.dataframe(df_missing, height=400, width='stretch')

        # Show summary
        api_has_data = sum(1 for status in api_status if status == "✅")
        api_no_data = sum(1 for status in api_status if status == "❌")

        col_api1, col_api2 = st.columns(2)
        with col_api1:
            st.metric("✅ API has data", api_has_data)
        with col_api2:
            st.metric("❌ API missing data", api_no_data)
    else:
        # Display dataframe without API check
        st.dataframe(df_missing, height=400, width='stretch')

    # Option to download the list
    csv = df_missing.to_csv(index=False)
    st.download_button(
        label="Download Missing Dates as CSV",
        data=csv,
        file_name="missing_dates.csv",
        mime="text/csv",
    )
else:
    st.success("No missing dates found! Database has continuous data coverage.")
