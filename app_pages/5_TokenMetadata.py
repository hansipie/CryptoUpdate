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

from modules import tools
from modules.token_metadata import TokenMetadataManager, TokenStatus

logger = logging.getLogger(__name__)

st.title("Token Metadata Management")

# Initialize token metadata manager
manager = TokenMetadataManager(st.session_state.settings["dbfile"])


@st.dialog("Sélectionner le token MarketRaccoon")
def _select_coin_dialog():
    """Dialog pour sélectionner le bon token parmi plusieurs résultats MarketRaccoon."""
    coins_df = st.session_state.get("pending_coins")
    token_symbol = st.session_state.get("pending_token_symbol")

    if coins_df is None or coins_df.empty:
        st.rerun()
        return

    st.write(f"Plusieurs tokens trouvés pour **{token_symbol}**. Sélectionnez le bon :")

    options = []
    for _, row in coins_df.iterrows():
        ucid = row.get("cmc_id")
        ucid_part = f", UCID: {ucid}" if pd.notna(ucid) else ""
        options.append(
            f"{row['symbol']} — {row['name']} (ID: {row['id']}{ucid_part})"
        )
    selected_idx = st.selectbox(
        "Token",
        range(len(options)),
        format_func=lambda i: options[i]
    )

    col1, col2 = st.columns(2)
    with col1:
        if st.button("Confirmer", type="primary", icon=":material/check:", use_container_width=True):
            row = coins_df.iloc[selected_idx]
            st.session_state["checked_mr_id"] = int(row["id"])
            st.session_state["checked_mr_name"] = row["name"]
            st.session_state["checked_token"] = row["symbol"]
            st.session_state["checked_cmc_id"] = row.get("cmc_id")
            del st.session_state["pending_coins"]
            del st.session_state["pending_token_symbol"]
            st.rerun()
    with col2:
        if st.button("Ignorer", icon=":material/cancel:", use_container_width=True):
            del st.session_state["pending_coins"]
            del st.session_state["pending_token_symbol"]
            st.rerun()


@st.dialog("⚠️ Confirmer la suppression")
def _delete_confirmation_dialog():
    """Dialog de confirmation avant suppression d'un token."""
    token_symbol = st.session_state.get("token_to_delete")
    mr_id = st.session_state.get("token_to_delete_id")

    if not token_symbol or mr_id is None:
        st.rerun()
        return

    # Récupérer les infos du token en utilisant le mraccoon_id
    token_info = manager.get_token_info_by_mr_id(mr_id)
    token_name = token_info.get("name") if token_info else None
    display_symbol = token_info.get("token") if token_info else token_symbol

    if token_name:
        st.warning(f"Êtes-vous sûr de vouloir supprimer **{display_symbol}** ({token_name}) ?")
    else:
        st.warning(f"Êtes-vous sûr de vouloir supprimer **{display_symbol}** ?")
    st.write("Cette action supprimera toutes les métadonnées associées à ce token.")

    col1, col2 = st.columns(2)
    with col1:
        if st.button("Supprimer", type="primary", icon=":material/delete_forever:", use_container_width=True):
            deleted = manager.delete_token_by_mr_id(mr_id)
            if deleted:
                st.success(f"{display_symbol} supprimé.")
            else:
                st.warning(f"{display_symbol} introuvable en base.")
            _clear_checked_state()
            del st.session_state["token_to_delete"]
            if "token_to_delete_id" in st.session_state:
                del st.session_state["token_to_delete_id"]
            st.rerun()
    with col2:
        if st.button("Annuler", icon=":material/close:", use_container_width=True):
            del st.session_state["token_to_delete"]
            if "token_to_delete_id" in st.session_state:
                del st.session_state["token_to_delete_id"]
            st.rerun()


# Ouvrir le dialog si des coins sont en attente de sélection
if "pending_coins" in st.session_state:
    _select_coin_dialog()

# Ouvrir le dialog de confirmation de suppression si nécessaire
if "token_to_delete" in st.session_state:
    _delete_confirmation_dialog()


def _clear_checked_state():
    """Supprime les clés checked_* du session_state."""
    for key in ("checked_token", "checked_mr_id", "checked_mr_name", "checked_cmc_id"):
        st.session_state.pop(key, None)


# Sidebar for adding/updating token metadata
with st.sidebar:
    st.header("Add/Update Token")

    # --- Partie 1 : Recherche token ---
    token_symbol = st.text_input(
        "Token Symbol",
        placeholder="BTC, ETH, etc.",
        help="Enter the token symbol (case-sensitive)"
    ).strip().upper()

    if st.button("Check", icon=":material/search:", use_container_width=True):
        if not token_symbol:
            st.warning("Veuillez saisir un symbole.")
        else:
            st.session_state["checked_token"] = token_symbol
            # 1. Appel API MarketRaccoon en priorité
            try:
                api_market = tools._get_cached_api_market()
                coins_df = api_market.get_coins(symbols=[token_symbol])

                if coins_df is None or coins_df.empty:
                    st.warning(f"Token {token_symbol} non trouvé sur MarketRaccoon.")
                    st.session_state["checked_mr_id"] = None
                    st.session_state["checked_mr_name"] = None
                elif len(coins_df) == 1:
                    row = coins_df.iloc[0]
                    st.session_state["checked_mr_id"] = int(row["id"])
                    st.session_state["checked_mr_name"] = row["name"]
                    st.session_state["checked_token"] = row["symbol"]
                    st.session_state["checked_cmc_id"] = row.get("cmc_id")
                else:
                    # Plusieurs résultats → dialog de sélection
                    st.session_state["checked_mr_id"] = None
                    st.session_state["checked_mr_name"] = None
                    st.session_state["pending_coins"] = coins_df
                    st.session_state["pending_token_symbol"] = token_symbol
                    st.rerun()
            except Exception as e:
                logger.warning("Could not fetch MarketRaccoon info for %s: %s", token_symbol, e)
                # 2. Fallback : utiliser les infos existantes en DB
                existing_mr_id = manager.get_mr_id(token_symbol)
                if existing_mr_id is not None:
                    info = manager.get_token_info_by_mr_id(existing_mr_id)
                    st.session_state["checked_mr_id"] = existing_mr_id
                    st.session_state["checked_mr_name"] = info.get("name") if info else None
                    st.session_state["checked_token"] = info.get("token") if info else token_symbol
                    st.info(f"API indisponible — infos chargées depuis la base de données.")
                else:
                    st.warning(f"API indisponible et token {token_symbol} absent de la base.")
                    st.session_state["checked_mr_id"] = None
                    st.session_state["checked_mr_name"] = None

    checked_id = st.session_state.get("checked_mr_id")
    has_checked = checked_id is not None

    st.divider()

    # --- Partie 2 : MarketRaccoon Info (lecture seule) ---
    st.subheader("MarketRaccoon Info")
    checked_id = st.session_state.get("checked_mr_id")

    # Mettre à jour les clés widget avant le rendu
    st.session_state["mr_name_display"] = st.session_state.get("checked_mr_name") or ""
    st.session_state["mr_id_display"] = str(checked_id) if checked_id is not None else ""
    cmc_id = st.session_state.get("checked_cmc_id")
    st.session_state["mr_cmc_id_display"] = str(cmc_id) if cmc_id else ""

    st.text_input("Name", disabled=True, key="mr_name_display")
    col1, col2 = st.columns(2)
    with col1:
        st.text_input("MarketRaccoon ID", disabled=True, key="mr_id_display")
    with col2:
        st.text_input("UCID", disabled=True, key="mr_cmc_id_display")

    submit_disabled = not has_checked or checked_id is None
    if st.button("Submit", icon=":material/cloud_upload:", use_container_width=True, disabled=submit_disabled):
        manager.upsert_token_info_by_mr_id(
            st.session_state["checked_mr_id"],
            st.session_state.get("checked_token", ""),
            st.session_state.get("checked_mr_name", ""),
        )
        st.success(f"MR info saved for {st.session_state.get('checked_token', '')}")
        _clear_checked_state()
        st.rerun()

    st.divider()

    # --- Partie 3 : Métadonnées (formulaire éditable) ---
    st.subheader("Metadata")

    with st.form("metadata_form"):
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
                "Last Date",
                value=None,
                help="Date of last valid price (optional)"
            )

        notes = st.text_area(
            "Notes",
            placeholder="Additional information about this token...",
            help="Notes about the token status"
        )

        submitted = st.form_submit_button(
            "Save Metadata", icon=":material/save:", disabled=not has_checked, use_container_width=True
        )

        if submitted:
            checked_mr_id = st.session_state.get("checked_mr_id")
            checked_token = st.session_state.get("checked_token", "")
            if checked_mr_id is None:
                st.error("No MarketRaccoon ID checked!")
            else:
                try:
                    delisting_dt = None
                    if delisting_date:
                        delisting_dt = datetime.combine(
                            delisting_date, datetime.min.time()
                        ).replace(tzinfo=timezone.utc)

                    last_price_dt = None
                    if last_valid_price_date:
                        last_price_dt = datetime.combine(
                            last_valid_price_date, datetime.min.time()
                        ).replace(tzinfo=timezone.utc)

                    manager.add_or_update_token_by_mr_id(
                        mr_id=checked_mr_id,
                        token=checked_token,
                        status=TokenStatus(status),
                        delisting_date=delisting_dt,
                        last_valid_price_date=last_price_dt,
                        notes=notes if notes else None,
                    )
                    st.success(f"Metadata saved for {checked_token}")
                    _clear_checked_state()
                    st.rerun()
                except Exception as e:
                    logger.exception(f"Error saving token metadata: {e}")
                    st.error(f"Error saving metadata: {e}")

    st.divider()

    # --- Partie 4 : Danger Zone ---
    if st.button(
        "Danger Zone",
        icon=":material/destruction:",
        use_container_width=True,
        disabled=not has_checked,
        type="primary",
    ):
        checked_token = st.session_state.get("checked_token", "")
        checked_mr_id = st.session_state.get("checked_mr_id")
        st.session_state["token_to_delete"] = checked_token
        st.session_state["token_to_delete_id"] = checked_mr_id
        st.rerun()

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
        df_recent = df_all.nlargest(10, 'updated_at')[['token', 'name', 'status', 'updated_at', 'notes']]
        df_recent['updated_at'] = df_recent['updated_at'].dt.strftime('%Y-%m-%d %H:%M')

        st.dataframe(
            df_recent,
            width='stretch',
            hide_index=True,
            column_config={
                "token": st.column_config.TextColumn("Token", width="small"),
                "name": st.column_config.TextColumn("Name", width="medium"),
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
        df_active = df_active[['token', 'name', 'notes', 'created_at', 'updated_at']]

        st.dataframe(
            df_active,
            width='stretch',
            hide_index=True,
            column_config={
                "token": st.column_config.TextColumn("Token", width="small"),
                "name": st.column_config.TextColumn("Name", width="medium"),
                "notes": st.column_config.TextColumn("Notes", width="large"),
                "created_at": st.column_config.TextColumn("Created", width="medium"),
                "updated_at": st.column_config.TextColumn("Updated", width="medium"),
            }
        )

        # Quick actions
        st.subheader("Quick Actions")
        col1, col2 = st.columns(2)

        with col1:
            active_options = [
                t for t in active_tokens
                if t.get("mraccoon_id") is not None
            ]
            token_to_delist = st.selectbox(
                "Mark token as delisted",
                options=[''] + active_options,
                format_func=lambda t: (
                    "" if t == '' else f"{t['token']} — {t.get('name', '')} (ID: {t['mraccoon_id']})"
                ),
                key="delist_token"
            )

            if st.button("Mark as Delisted", disabled=not token_to_delist):
                try:
                    manager.add_or_update_token_by_mr_id(
                        mr_id=token_to_delist["mraccoon_id"],
                        token=token_to_delist["token"],
                        status=TokenStatus.DELISTED,
                        delisting_date=datetime.now(timezone.utc),
                        notes="Marked as delisted via UI"
                    )
                    st.success(f"✅ {token_to_delist['token']} marked as delisted")
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
        df_delisted = df_delisted[['token', 'name', 'delisting_date', 'last_valid_price_date', 'notes']]

        st.dataframe(
            df_delisted,
            width='stretch',
            hide_index=True,
            column_config={
                "token": st.column_config.TextColumn("Token", width="small"),
                "name": st.column_config.TextColumn("Name", width="medium"),
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
                'token', 'name', 'status', 'delisting_date',
                'last_valid_price_date', 'notes', 'updated_at'
            ]]

            st.dataframe(
                df_display,
                width='stretch',
                hide_index=True,
                column_config={
                    "token": st.column_config.TextColumn("Token", width="small"),
                    "name": st.column_config.TextColumn("Name", width="medium"),
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
