# Code Review Report - CryptoUpdate

**Date**: 2026-04-18
**Scope**: 26 Python files (app.py, app_pages, modules, modules/database, tests)

---

## Findings by File

### app_pages/1_Portfolios.py

- � **L2** - `import traceback` at module top but only used in one `except` block; switch to `logger.exception()` and remove the import.
- 🟡 **L304-312** - `is_portfolio_empty()` calls `create_portfolio_dataframe(pf)`, which triggers full Market DB price lookups for every portfolio on every render just to determine emptiness. Extract a cheap amount-only check from raw portfolio data.
- 🔵 **L399** - `traceback.print_exc()` in bare `except Exception` block; replace with `logger.exception()`.

### app_pages/2_Graphs.py

- 🟡 **L167** - `st.plotly_chart(fig, width="stretch")` in `plot_modern_graph` — `width` is not a valid `st.plotly_chart` keyword; use `use_container_width=True`.
- 🟡 **L288** - Same issue in `plot_dual_axis_graph`.

### app_pages/6_Settings.py

- 🟡 **L33-52** - `_check_marketraccoon()` can return `"invalid_url"` (for `MissingSchema`), but the sidebar caller has no `elif _status == "invalid_url"` branch — the status is silently swallowed and the user sees nothing.
- 🔵 **L16-29** - Only specific `requests` exceptions are caught; other `RequestException` subclasses (e.g. `SSLError`, `TooManyRedirects`) propagate through `@st.cache_data` and crash the sidebar widget.

### app_pages/X_Tests.py

- 🔵 **L67** - `import requests` inside `check_api_data_for_date`; move to module top.
- 🟡 **L163** - `ThreadPoolExecutor(max_workers=10)` fires up to `len(missing_dates)` concurrent requests to MarketRaccoon with no rate limiting or backoff. Risk of 429 on large date gaps.
- 🔵 **L240** - `logger.error(...)` in the `as_completed` exception handler; use `logger.exception()` to capture the traceback.

### modules/aiprocessing.py

- 🔵 **L157** - `traceback.print_exc()` in `call_ai()` exception handler; replace with `logger.exception()` and remove `import traceback`.

### modules/cmc.py

- 🟡 **L11** - `__init__` annotated `-> dict`; should be `-> None`.
- 🔵 **L2** - `import traceback` only used in one error handler; replace with `logger.exception()` and remove the import.
- 🔵 **L78** - `traceback.print_exc()` in `get_current_fiat_prices()` error handler; replace with `logger.exception()`.

### modules/configuration.py

- 🔵 **L58, L62** - `os.path.basename(settings["dbfile"])` and `os.path.basename(settings["archive_path"])` silently discard any subdirectory component. A path like `data/subdir/db.sqlite3` would be saved as `db.sqlite3`, losing `subdir/` on the next read.

### modules/token_metadata.py

- 🟡 **L329-386** - `upsert_token_info_by_mr_id` has three-level branching (look up by `mraccoon_id` → look up by symbol → insert new). Correct but hard to follow; consider factoring the two lookup queries into named helpers.
- 🟡 **L388-401** - `delete_token(token)` issues `DELETE FROM TokenMetadata WHERE token = ?`. Since `token` is no longer the PRIMARY KEY (migration v4 added `id AUTOINCREMENT`), multiple rows may exist per symbol — all are deleted. Verify this is the intended semantics or add a delete-by-`id` variant.

### modules/tools.py

- 🟡 **L361** - `get_dataframe()` slices `df[["Token", "Market Price", "Coins in wallet", "Timestamp"]]` without first validating the columns exist. A missing column produces an unhelpful `KeyError`; add an explicit presence check with a clear error message.
- 🟡 **L696** - `_get_api_fiat_rate()` calls `api.get_fiat_latest_rate()` (uncached) instead of `api.get_fiat_latest_rate_cached()`, bypassing `FiatCacheManager` TTL logic and causing redundant network requests.
- 🔵 **L256** - `traceback.print_exc()` in `update_database()` error handler; replace with `logger.exception()`.
- 🔵 **L1017** - `traceback.print_exc()` in `update()` error handler; replace with `logger.exception()`.

### modules/database/apimarket.py

- 🔵 **L182** - `dt.astimezone(pd.Timestamp.now(tz="UTC").tz).isoformat()` constructs a `pd.Timestamp` just to extract its `.tz` attribute; use `datetime.timezone.utc` directly: `dt.astimezone(datetime.timezone.utc).isoformat()`.
- 🔵 **L373** - Same redundant pattern as L182.

### modules/database/customdata.py

- 🟡 **L40** - `get()` is annotated `-> str` but returns `None` or a raw sqlite3 row tuple `(value, type)`. Misleading annotation; callers must know the real contract by convention.

### modules/database/fiat_cache.py

- 🔵 **L270-273** - `if "temp_path" in locals()` in the `_save_cache` exception handler is fragile. Initialize `temp_path: str | None = None` before the `try` block and test `if temp_path is not None`.

### modules/database/market.py

- 🟡 **L391** - `get_token_lowhigh()` is annotated `-> pd.DataFrame` but returns `tuple[pd.DataFrame, pd.DataFrame]` (low, high).
- 🟡 **L414** - `get_currency_lowhigh()` has the same incorrect annotation.

### modules/database/portfolios.py

- 🟡 **L55** - `delete_portfolio()` deletes only the `Portfolios` row, not the associated `Portfolios_Tokens` rows. SQLite FK enforcement is off by default and no `ON DELETE CASCADE` is set, so orphan holdings rows accumulate.
- 🔵 **L107** - `str(amount)` in `set_token()` SQL binding is redundant; sqlite3 accepts Python `float` natively.
- 🔵 **L145** - `str(new_amount)` in `set_token_add()` SQL binding is likewise redundant.

---

## Consolidated Recommendations (Sorted by Impact)

| # | Priority | Action | File(s) | Benefit |
|---|---|---|---|---|
| 1 | 🟡 | Reconnect fiat-rate path to cached accessor in `_get_api_fiat_rate` | [modules/tools.py](modules/tools.py):696 | Consistent caching, fewer redundant API calls |
| 2 | 🟡 | Add cascade cleanup when deleting portfolios | [modules/database/portfolios.py](modules/database/portfolios.py):55 | Referential integrity, no orphan rows |
| 3 | 🟡 | Handle `"invalid_url"` status in settings sidebar | [app_pages/6_Settings.py](app_pages/6_Settings.py):33-52 | No silent failure on misconfigured URL |
| 4 | 🟡 | Decouple `is_portfolio_empty` from valuation / price queries | [app_pages/1_Portfolios.py](app_pages/1_Portfolios.py):304-312 | Avoid expensive hidden work on every render |
| 5 | 🟡 | Fix invalid `width="stretch"` in `st.plotly_chart()` calls | [app_pages/2_Graphs.py](app_pages/2_Graphs.py):167,288 | Correct Streamlit/Plotly layout |
| 6 | 🟡 | Fix incorrect return type annotations | [modules/database/market.py](modules/database/market.py):391,414 · [modules/database/customdata.py](modules/database/customdata.py):40 · [modules/cmc.py](modules/cmc.py):11 | Accurate static analysis, safer callers |
| 7 | 🟡 | Validate expected columns in `get_dataframe` before slicing | [modules/tools.py](modules/tools.py):361 | Early, descriptive failure instead of KeyError |
| 8 | 🟡 | Add rate limiting / backoff in threaded API date checks | [app_pages/X_Tests.py](app_pages/X_Tests.py):163 | Avoid 429 throttling from MarketRaccoon |
| 9 | 🟡 | Clarify `delete_token(token)` all-rows semantics or add delete-by-id variant | [modules/token_metadata.py](modules/token_metadata.py):388-401 | Safer data ops since token is no longer PK |
| 10 | 🟡 | Refactor `upsert_token_info_by_mr_id` three-branch logic into named helpers | [modules/token_metadata.py](modules/token_metadata.py):329-386 | Readability and maintainability |
| 11 | 🔵 | Replace all `traceback.print_exc()` with `logger.exception()` and drop `import traceback` | [modules/aiprocessing.py](modules/aiprocessing.py) · [modules/cmc.py](modules/cmc.py) · [modules/tools.py](modules/tools.py):256,1017 · [app_pages/1_Portfolios.py](app_pages/1_Portfolios.py):399 | Structured observability, clean imports |
| 12 | 🔵 | Catch `requests.exceptions.RequestException` broadly in `_check_marketraccoon` | [app_pages/6_Settings.py](app_pages/6_Settings.py):16-29 | Prevent unhandled SSL/proxy errors crashing sidebar |
| 13 | 🔵 | Fix `os.path.basename()` dropping subdirectory in `save_config` | [modules/configuration.py](modules/configuration.py):58,62 | Correct round-trip save for non-flat paths |
| 14 | 🔵 | Replace `if "temp_path" in locals()` with `temp_path = None` pre-init | [modules/database/fiat_cache.py](modules/database/fiat_cache.py):270-273 | Robust cleanup in all Python implementations |
| 15 | 🔵 | Simplify `pd.Timestamp.now(tz="UTC").tz` → `datetime.timezone.utc` | [modules/database/apimarket.py](modules/database/apimarket.py):182,373 | Cleaner, dependency-free UTC usage |
| 16 | 🔵 | Remove redundant `str(amount)` / `str(new_amount)` in SQL bindings | [modules/database/portfolios.py](modules/database/portfolios.py):107,145 | Idiomatic sqlite3 float binding |
| 17 | 🔵 | Move `import requests` to module top | [app_pages/X_Tests.py](app_pages/X_Tests.py):67 | PEP 8 / import hygiene |

---

## Files with No Findings

- [app.py](app.py)
- [tests/test_utils.py](tests/test_utils.py)
- [app_pages/0_Home.py](app_pages/0_Home.py)
- [app_pages/3_Operations.py](app_pages/3_Operations.py)
- [app_pages/4_Import.py](app_pages/4_Import.py)
- [app_pages/5_TokenMetadata.py](app_pages/5_TokenMetadata.py)
- [modules/plotter.py](modules/plotter.py)
- [modules/utils.py](modules/utils.py)
- [modules/database/migrations.py](modules/database/migrations.py)
- [modules/database/operations.py](modules/database/operations.py)
- [modules/database/swaps.py](modules/database/swaps.py)
- [modules/database/tokensdb.py](modules/database/tokensdb.py)

---

## Executive Summary

The codebase is in significantly improved shape compared to the previous review cycle. All previously reported critical and high-severity defects (outer-merge memory explosion, stale closure in dialogs, `st.info()` inside cached functions, O(n²) DataFrame append in `add_tokens`, invalid `width="stretch"` in plotter/home, `backup_database` with no disk check or rotation) have been resolved.

The remaining 17 findings fall into three themes:

1. **API caching consistency** (finding #1): `_get_api_fiat_rate()` bypasses `FiatCacheManager` by calling the raw uncached accessor — the highest-priority fix as it undermines the cache layer's TTL behaviour.

2. **Type annotation accuracy** (findings #6, #7): Four methods (`customdata.get()`, both `lowhigh` methods in `market`, `cmc.__init__`) carry annotations that contradict actual return types, producing false-negative static-analysis results and requiring callers to know the real contract by convention.

3. **`traceback.print_exc()` residue** (finding #11): Five locations across four files still use the stdlib function for error logging instead of the structured `logger.exception()` pattern adopted everywhere else. Each fix is a two-line change.

Secondary concerns: the missing `"invalid_url"` branch in the settings sidebar (silent gap, finding #3), expensive valuation work hidden inside `is_portfolio_empty()` (finding #4), absent cascade delete for portfolio removal (finding #2), and the two `width="stretch"` instances still in `2_Graphs.py` (finding #5) which are direct copies of the pattern already corrected in `plotter.py` and `0_Home.py`.
