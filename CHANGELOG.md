# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).
The project has no tagged release yet: entries are grouped by date, newest first.

## 2026-10-17

### Added

- Test suite (`pytest`, 28 tests) covering transactions, migrations, the price
  cache, CoinMarketCap parsing, currency conversion, DST handling and
  configuration saving, with a `Tests` GitHub Actions workflow.

### Fixed

- Add/Edit Swap: tokens are trimmed and uppercased, and both tokens and
  strictly positive amounts are required.
- Settings: URLs are trimmed and must be valid http(s) URLs, and the colour
  thresholds must satisfy green >= orange >= red; invalid input is not saved.
- `settings.json` is written to a temporary file then renamed, so a failure can
  no longer truncate it; a new file is created with `0600` permissions and an
  existing one keeps its permissions.
- Import: the AI answer is checked (no answer, no assets, missing columns),
  extracted symbols are uppercased and rows with an invalid amount are skipped
  with a warning, uploads are limited to 10 MB and unreadable files give an
  error instead of a traceback.
- `Swaps.delete`, `update_tag` and `update_note` no longer swallow database
  errors, so the interface cannot report a success that did not happen.

- Local currency conversion inverted the USD rate: `Currency` stores
  "1 EUR = x USD" while a price in EUR was expected (100 USD became 120 EUR
  instead of 83.33 EUR when 1 EUR = 1.20 USD).
- MarketRaccoon series are indexed in naive local time; they were read back as
  UTC, shifting interpolated prices and fiat rates by the UTC offset.
- Adding an operation at an ambiguous or nonexistent DST hour no longer raises
  (`to_timestamp_a`).
- "Add Buy" / "Edit Buy" now require a token, not only a portfolio.
- Debug mode no longer prints the `ai_apitoken` widget value: any session key
  containing `token` or `password` is hidden.
- Operations, swaps, airdrops and their effect on `Portfolios_Tokens` are
  written in a single transaction (add, edit, delete). A failure no longer
  leaves `portfolio_adjusted = 1` without the matching holdings change.
- Renaming a portfolio updates `Operations.portfolio` and
  `Swaps.wallet_from` / `wallet_to`, so synchronized operations keep working.
- Each migration and its `db_version` are applied in one `BEGIN IMMEDIATE`
  transaction, with the version re-read under lock: an interrupted or
  concurrent start can no longer leave the schema half-migrated.
- A partial CoinMarketCap response no longer re-inserts the previous snapshot
  of the missing tokens into `TokensDatabase`.
- `set_token_add` increments in SQL, so concurrent sessions cannot overwrite
  each other's update.
- The price cache only widens a coin's covered range when the fetched range
  overlaps it; disjoint fetches no longer mark the gap as covered.
- Missing or invalid CoinMarketCap prices and fiat rates are skipped instead of
  being stored as `0`.
- A conversion that cannot be done (rate unavailable or invalid) returns
  `None` instead of the amount in the source currency. The Home page shows
  `n/a` for "Invested" and "Profit", and the API performance no longer
  presents a USD price as EUR.
- SQLite connections are closed when leaving the `with` block
  (`modules.utils.db_connect`) instead of waiting for garbage collection.

### Changed

- Operations tables (buys, averages, swaps, airdrops) are cached and keyed on
  the database state, so selecting a row no longer recomputes them; an edit or
  "Update prices" refreshes them. This also removes the stale swap performance
  (previously cached for an hour) and the full-file hash on every rerun.
- `Operations.insert/delete` and `Swaps.insert` apply the portfolio change
  themselves; new `Operations.replace` and `Swaps.replace` edit a row and undo
  its previous effect atomically.
- `Market.update_market` returns the timestamp of the update.

## 2026-10-14

### Added

- MarketRaccoon price cache (`data/api_price_cache.sqlite3`) that downloads only
  the missing head and tail of each coin's history (#10).
- Airdrops tab in Operations and currency conversion of operations (#10).

### Security

- Bump `urllib3` to 2.8.0 and `werkzeug` to 3.1.9 (#11).

## 2026-09-04

### Fixed

- Operations: drop row selections that are beyond the current table length (#9).

## 2026-08-21

### Changed

- Dependency updates (#7) and `/.agents` ignored by Git (#8).

### Fixed

- Portfolio visibility (#7).

## 2026-04-18

### Fixed

- Code review fixes across all modules (#4).

### Changed

- README, database rules and security documentation updated (#5, #6).

## 2026-02-24

### Security

- Prevent SQL injection in `Market` queries.

### Changed

- Further code review fixes; Material icons for the MarketRaccoon health check
  in Settings.

## 2026-02-16

### Added

- `note` column on `Swaps` (migration v5).

### Changed

- camelCase to snake_case (PEP 8) across the code base; `CLAUDE.md` and
  `README.md` rewritten.

## 2026-02-10

### Added

- Versioned database migrations (`modules/database/migrations.py`).
- MarketRaccoon token identifiers (`mraccoon_id`) in `TokenMetadata`.

### Removed

- The Tokens page.

## 2026-02-08

### Added

- Dynamic EUR/USD display currency, replacing hardcoded `€` symbols.
- Historical currency conversion in the Operations Buy and Swap tables.

### Security

- Dependency updates fixing 5 CVEs.

## 2026-02-06

### Added

- MarketRaccoon API token authentication on all requests.

## 2026-02-02

### Added

- Data source toggle (local database / MarketRaccoon API) with caching on the
  Graphs page.

## Before 2026-02

Initial development, from the first push on 2023-04-08 (Docker packaging added
on 2023-04-28).

[Unreleased]: https://github.com/hansipie/CryptoUpdate/commits/main
