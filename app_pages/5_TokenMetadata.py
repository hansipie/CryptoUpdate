"""Token Metadata Management page.

This module provides a UI for managing token metadata including:
- Viewing active and delisted tokens
- Adding/updating token status (active, delisted, deprecated, migrated)
- Setting delisting dates and notes
- Filtering tokens by status
"""

import logging
from datetime import datetime, timezone

import pandas as pd
import streamlit as st

from modules.token_metadata import TokenMetadataManager, TokenStatus

logger = logging.getLogger(__name__)

st.title("Token Metadata Management")

# Initialize token metadata manager
manager = TokenMetadataManager(st.session_state.settings["dbfile"])

# Sidebar for adding/updating token metadata
with st.sidebar:
    st.header("Add/Update Token")

    with st.form("add_token_form"):
        token_symbol = st.text_input(
            "Token Symbol",
            placeholder="BTC, ETH, etc.",
            help="Enter the token symbol (case-sensitive)"
        ).strip().upper()

        status = st.selectbox(
            "Status",
            options=[s.value for s in TokenStatus],
            help="Select token status"
        )

        col1, col2 = st.columns(2)
        with col1:
            delisting_date = st.date_input(
                "Delisting Date",
                value=None,
                help="Date when token was delisted (optional)"
            )

        with col2:
            last_valid_price_date = st.date_input(
                "Last Valid Price Date",
                value=None,
                help="Date of last valid price (optional)"
            )

        notes = st.text_area(
            "Notes",
            placeholder="Additional information about this token...",
            help="Notes about the token status"
        )

        submitted = st.form_submit_button("Save Token Metadata", width='stretch')

        if submitted:
            if not token_symbol:
                st.error("Token symbol is required!")
            else:
                try:
                    # Convert dates to datetime objects
                    delisting_dt = None
                    if delisting_date:
                        delisting_dt = datetime.combine(
                            delisting_date,
                            datetime.min.time()
                        ).replace(tzinfo=timezone.utc)

                    last_price_dt = None
                    if last_valid_price_date:
                        last_price_dt = datetime.combine(
                            last_valid_price_date,
                            datetime.min.time()
                        ).replace(tzinfo=timezone.utc)

                    # Save metadata
                    manager.add_or_update_token(
                        token=token_symbol,
                        status=TokenStatus(status),
                        delisting_date=delisting_dt,
                        last_valid_price_date=last_price_dt,
                        notes=notes if notes else None
                    )

                    st.success(f"✅ Metadata saved for {token_symbol}")
                    st.rerun()

                except Exception as e:
                    logger.exception(f"Error saving token metadata: {e}")
                    st.error(f"Error saving metadata: {e}")

# Main content area
tab1, tab2, tab3, tab4 = st.tabs(["📊 Overview", "✅ Active Tokens", "❌ Delisted Tokens", "📋 All Tokens"])

# Tab 1: Overview with statistics
with tab1:
    st.header("Token Metadata Overview")

    # Get all metadata
    all_metadata = manager.get_all_metadata()

    if not all_metadata:
        st.info("No token metadata found. Add tokens using the sidebar form.")
    else:
        # Statistics
        total_tokens = len(all_metadata)
        active_count = sum(1 for t in all_metadata if t['status'] == 'active')
        delisted_count = sum(1 for t in all_metadata if t['status'] == 'delisted')
        deprecated_count = sum(1 for t in all_metadata if t['status'] == 'deprecated')
        migrated_count = sum(1 for t in all_metadata if t['status'] == 'migrated')

        col1, col2, col3, col4, col5 = st.columns(5)

        with col1:
            st.metric("Total Tokens", total_tokens)
        with col2:
            st.metric("Active", active_count, delta=None, delta_color="normal")
        with col3:
            st.metric("Delisted", delisted_count, delta=None, delta_color="inverse")
        with col4:
            st.metric("Deprecated", deprecated_count)
        with col5:
            st.metric("Migrated", migrated_count)

        st.divider()

        # Recent changes
        st.subheader("Recent Updates")
        df_all = pd.DataFrame(all_metadata)
        df_all['updated_at'] = pd.to_datetime(df_all['updated_at'])
        df_recent = df_all.nlargest(10, 'updated_at')[['token', 'status', 'updated_at', 'notes']]
        df_recent['updated_at'] = df_recent['updated_at'].dt.strftime('%Y-%m-%d %H:%M')

        st.dataframe(
            df_recent,
            width='stretch',
            hide_index=True,
            column_config={
                "token": st.column_config.TextColumn("Token", width="small"),
                "status": st.column_config.TextColumn("Status", width="small"),
                "updated_at": st.column_config.TextColumn("Last Updated", width="medium"),
                "notes": st.column_config.TextColumn("Notes", width="large"),
            }
        )

# Tab 2: Active Tokens
with tab2:
    st.header("Active Tokens")

    active_tokens = [t for t in all_metadata if t['status'] == 'active']

    if not active_tokens:
        st.info("No active tokens found.")
    else:
        st.write(f"**{len(active_tokens)} active tokens**")

        df_active = pd.DataFrame(active_tokens)
        df_active = df_active[['token', 'notes', 'created_at', 'updated_at']]

        st.dataframe(
            df_active,
            width='stretch',
            hide_index=True,
            column_config={
                "token": st.column_config.TextColumn("Token", width="small"),
                "notes": st.column_config.TextColumn("Notes", width="large"),
                "created_at": st.column_config.TextColumn("Created", width="medium"),
                "updated_at": st.column_config.TextColumn("Updated", width="medium"),
            }
        )

        # Quick actions
        st.subheader("Quick Actions")
        col1, col2 = st.columns(2)

        with col1:
            token_to_delist = st.selectbox(
                "Mark token as delisted",
                options=[''] + [t['token'] for t in active_tokens],
                key="delist_token"
            )

            if st.button("Mark as Delisted", disabled=not token_to_delist):
                try:
                    manager.add_or_update_token(
                        token=token_to_delist,
                        status=TokenStatus.DELISTED,
                        delisting_date=datetime.now(timezone.utc),
                        notes="Marked as delisted via UI"
                    )
                    st.success(f"✅ {token_to_delist} marked as delisted")
                    st.rerun()
                except Exception as e:
                    st.error(f"Error: {e}")

# Tab 3: Delisted Tokens
with tab3:
    st.header("Delisted Tokens")

    delisted_tokens = [t for t in all_metadata if t['status'] == 'delisted']

    if not delisted_tokens:
        st.info("No delisted tokens found.")
    else:
        st.write(f"**{len(delisted_tokens)} delisted tokens**")

        df_delisted = pd.DataFrame(delisted_tokens)
        df_delisted = df_delisted[['token', 'delisting_date', 'last_valid_price_date', 'notes']]

        st.dataframe(
            df_delisted,
            width='stretch',
            hide_index=True,
            column_config={
                "token": st.column_config.TextColumn("Token", width="small"),
                "delisting_date": st.column_config.TextColumn("Delisted On", width="medium"),
                "last_valid_price_date": st.column_config.TextColumn("Last Valid Price", width="medium"),
                "notes": st.column_config.TextColumn("Notes", width="large"),
            }
        )

        # Warning about database cleanup
        with st.expander("⚠️ Database Cleanup Recommendations"):
            st.markdown("""
            Delisted tokens may still have historical data in the database:

            - **Market table**: Historical price data with price = 0
            - **TokensDatabase table**: Portfolio valuation history

            **Note**: Historical data for delisted tokens is preserved for audit purposes.
            Only zero-price entries have been cleaned up during initial database maintenance.
            """)

# Tab 4: All Tokens
with tab4:
    st.header("All Token Metadata")

    if not all_metadata:
        st.info("No token metadata found.")
    else:
        # Filter options
        col1, col2 = st.columns([2, 1])

        with col1:
            search_term = st.text_input(
                "Search tokens",
                placeholder="Enter token symbol...",
                help="Filter tokens by symbol"
            ).upper()

        with col2:
            status_filter = st.multiselect(
                "Filter by status",
                options=[s.value for s in TokenStatus],
                default=None
            )

        # Apply filters
        filtered_metadata = all_metadata

        if search_term:
            filtered_metadata = [t for t in filtered_metadata if search_term in t['token']]

        if status_filter:
            filtered_metadata = [t for t in filtered_metadata if t['status'] in status_filter]

        st.write(f"**Showing {len(filtered_metadata)} of {len(all_metadata)} tokens**")

        # Display table
        if filtered_metadata:
            df_all = pd.DataFrame(filtered_metadata)
            df_display = df_all[[
                'token', 'status', 'delisting_date',
                'last_valid_price_date', 'notes', 'updated_at'
            ]]

            st.dataframe(
                df_display,
                width='stretch',
                hide_index=True,
                column_config={
                    "token": st.column_config.TextColumn("Token", width="small"),
                    "status": st.column_config.TextColumn("Status", width="small"),
                    "delisting_date": st.column_config.TextColumn("Delisted On", width="medium"),
                    "last_valid_price_date": st.column_config.TextColumn("Last Valid Price", width="medium"),
                    "notes": st.column_config.TextColumn("Notes", width="large"),
                    "updated_at": st.column_config.TextColumn("Last Updated", width="medium"),
                }
            )
        else:
            st.info("No tokens match your filters.")

        # Export functionality
        st.divider()

        if st.button("📥 Export to CSV", width='stretch'):
            df_export = pd.DataFrame(all_metadata)
            csv = df_export.to_csv(index=False)
            st.download_button(
                label="Download CSV",
                data=csv,
                file_name=f"token_metadata_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                mime="text/csv",
                width='stretch'
            )

# Footer with help
with st.expander("ℹ️ Help & Documentation"):
    st.markdown("""
    ### Token Status Types

    - **Active**: Token is currently traded and has valid price data
    - **Delisted**: Token has been removed from exchanges and is no longer traded
    - **Deprecated**: Token is being phased out but may still have some functionality
    - **Migrated**: Token has been migrated to a new contract/symbol

    ### Best Practices

    1. **Mark tokens as delisted** when they're no longer available on exchanges
    2. **Add notes** explaining why a token was delisted or any relevant context
    3. **Set dates** to track when changes occurred
    4. **Use filters** in the UI to avoid showing delisted tokens to users

    ### Code Integration

    ```python
    from modules.token_metadata import TokenMetadataManager

    manager = TokenMetadataManager()

    # Filter active tokens before display
    active_tokens = manager.filter_active_tokens(all_tokens)

    # Check if specific token is active
    if manager.is_token_active('BTC'):
        # Show token
    ```

    See `DATABASE_RULES.md` for complete documentation.
    """)
