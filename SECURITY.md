# Security Report

## Last Updated: 2026-04-18

## Executive Summary

A comprehensive security audit was conducted on the CryptoUpdate application. Multiple critical and high-severity vulnerabilities were identified and remediated. All project dependencies have been upgraded to their latest secure versions. This document outlines the vulnerabilities found, fixes applied, dependency status, and security best practices.

## Vulnerabilities Identified and Fixed

### 1. CRITICAL - SQL Injection Vulnerabilities

**Location:** `modules/database/swaps.py`

**Lines Affected:** 55, 107, 120, 122

**Description:**
The code used f-strings to construct SQL queries, allowing potential SQL injection attacks. An attacker could manipulate the `tag` or `entry_id` parameters to execute arbitrary SQL commands.

**Vulnerable Code:**
```python
# Line 107
cursor.execute(f"DELETE FROM Swaps WHERE id = {entry_id}")

# Line 120
cursor.execute(f"UPDATE Swaps SET tag = NULL WHERE id = {entry_id}")

# Line 122
cursor.execute(f"UPDATE Swaps SET tag = '{tag}' WHERE id = {entry_id}")

# Lines 55-66
tag_filter = f"WHERE tag = '{tag}'"
cursor.execute(f"SELECT ... FROM Swaps {tag_filter} ...")
```

**Fix Applied:**
Implemented parameterized queries using SQLite's parameter substitution (`?` placeholders):
```python
# Fixed delete
cursor.execute("DELETE FROM Swaps WHERE id = ?", (entry_id,))

# Fixed update
cursor.execute("UPDATE Swaps SET tag = ? WHERE id = ?", (tag, entry_id))

# Fixed select
cursor.execute("SELECT ... FROM Swaps WHERE tag = ? ...", (tag,))
```

**Impact:** Prevents SQL injection attacks that could lead to data theft, data manipulation, or database compromise.

---

### 2. CRITICAL - Hardcoded API Key

**Location:** `modules/cmc.py`

**Lines Affected:** 32, 95

**Description:**
A sandbox API key was hardcoded in the source code for CoinMarketCap API access in debug mode. This exposed the API key in version control and could lead to unauthorized API usage.

**Vulnerable Code:**
```python
headers = {"X-CMC_PRO_API_KEY": "b54bcf4d-1bca-4e8e-9a24-22ff2c3d462c"}
```

**Fix Applied:**
Removed the hardcoded key and now uses the configured API token from settings for both production and debug modes:
```python
# In debug mode, use the sandbox API with the provided token
# Sandbox API keys should be configured in settings
headers = {"X-CMC_PRO_API_KEY": str(self.coinmarketcap_token)}
```

**Impact:** Prevents unauthorized API usage and ensures all API keys are properly managed through configuration.

---

### 3. HIGH - Sensitive Data Exposure in Logs

**Location:** `modules/cmc.py`

**Lines Affected:** 48, 77, 124

**Description:**
Full API responses and error messages were logged at INFO and ERROR levels, potentially exposing sensitive data in log files.

**Vulnerable Code:**
```python
logger.info("Get current market prices from Coinmarketcap successfully\n%s", content)
logger.error(response.text)
```

**Fix Applied:**
- Moved detailed API response logging to DEBUG level
- Changed ERROR level logs to only include status codes, with details in DEBUG
```python
logger.info("Get current market prices from Coinmarketcap successfully")
logger.debug("API response data: %s", content)
logger.error("API request failed with status code: %d", response.status_code)
logger.debug("Error response: %s", response.text)
```

**Impact:** Reduces risk of sensitive data exposure in production logs while maintaining debugging capability.

---

### 4. HIGH - Session State Exposure in Debug Mode

**Location:** `app.py`

**Lines Affected:** 95-97

**Description:**
When debug mode was enabled, the entire session state including API tokens and passwords was displayed in the Streamlit UI.

**Vulnerable Code:**
```python
if st.session_state.settings["debug_flag"]:
    st.write("Debug mode is ON")
    st.write(st.session_state)
```

**Fix Applied:**
Implemented filtering to redact sensitive information before displaying:
```python
if st.session_state.settings["debug_flag"]:
    st.write("Debug mode is ON")
    # Filter out sensitive data from session state before displaying
    safe_session_state = {
        k: v for k, v in st.session_state.items()
        if k not in ["settings"] and not k.endswith("_token")
    }
    # Add non-sensitive settings
    if "settings" in st.session_state:
        safe_session_state["settings"] = {
            k: ("***REDACTED***" if "token" in k.lower() or "password" in k.lower() else v)
            for k, v in st.session_state.settings.items()
        }
    st.write(safe_session_state)
```

**Impact:** Prevents accidental exposure of API keys and passwords in the UI while maintaining debugging capability.

---

## Security Best Practices Implemented

### 1. Parameterized SQL Queries
All database operations now use parameterized queries to prevent SQL injection:
- ✅ `operations.py` - Already using parameterized queries
- ✅ `portfolios.py` - Already using parameterized queries
- ✅ `swaps.py` - Now fixed to use parameterized queries
- ✅ `market.py` - Already using parameterized queries
- ✅ `tokensdb.py` - Already using parameterized queries

### 2. Sensitive Data Handling
- API keys are managed through configuration files (not hardcoded)
- Sensitive data is redacted from debug output
- API responses are logged at DEBUG level only

### 3. Configuration Security
The application uses `settings.json` for configuration. Users should:
- **Never commit `settings.json` to version control**
- Store API keys securely
- Use environment variables or secret management systems in production
- Ensure `.gitignore` includes `settings.json`

### 4. Logging Security
- Sensitive data only logged at DEBUG level
- Production logs (INFO/ERROR) do not contain API responses or keys
- Error messages are descriptive but don't leak sensitive information

---

## Recommendations for Future Development

### 1. Environment Variables
Consider migrating from `settings.json` to environment variables for sensitive configuration:
```python
import os
from dotenv import load_dotenv

load_dotenv()

COINMARKETCAP_TOKEN = os.getenv("COINMARKETCAP_TOKEN")
AI_APITOKEN = os.getenv("AI_APITOKEN")
NOTION_TOKEN = os.getenv("NOTION_TOKEN")
```

### 2. Input Validation
Implement robust input validation for all user inputs:
- Validate token symbols (alphanumeric only)
- Validate numeric inputs (amounts, timestamps)
- Sanitize file uploads
- Validate portfolio names

### 3. Rate Limiting
Consider implementing rate limiting for:
- API calls to external services
- User actions (if multi-user support is added)
- Database operations

### 4. Security Headers
If deploying as a web service, implement security headers:
- Content-Security-Policy
- X-Frame-Options
- X-Content-Type-Options
- Strict-Transport-Security

### 5. Dependency Scanning
Regularly scan dependencies for vulnerabilities:
```bash
# Using pip-audit
pip install pip-audit
pip-audit

# Or using safety
pip install safety
safety check
```

### 6. Secret Management
For production deployments:
- Use Streamlit secrets management (`st.secrets`)
- Consider HashiCorp Vault or AWS Secrets Manager
- Implement secret rotation policies

### 7. Database Security
- Use encryption at rest for SQLite database
- Implement regular database backups
- Consider using encrypted database connections
- Add database integrity checks

### 8. Code Review Process
- Implement mandatory security reviews for database operations
- Check for hardcoded secrets in pre-commit hooks
- Use static analysis tools (e.g., Bandit for Python)

---

## Testing Recommendations

### Security Testing Checklist

- [ ] SQL Injection testing on all database operations
- [ ] Verify no secrets in logs at INFO/ERROR levels
- [ ] Test debug mode with various session states
- [ ] Verify API error responses don't leak sensitive data
- [ ] Test with invalid/malicious inputs
- [ ] Verify `.gitignore` excludes sensitive files
- [ ] Check for any remaining hardcoded secrets

### Automated Security Tools

Consider integrating these tools:

1. **Bandit** - Python security linter
   ```bash
   pip install bandit
   bandit -r . -ll
   ```

2. **pip-audit** - Dependency vulnerability scanner
   ```bash
   pip install pip-audit
   pip-audit
   ```

3. **Semgrep** - Static analysis tool
   ```bash
   pip install semgrep
   semgrep --config=auto .
   ```

---

## Compliance Notes

### Data Protection
- API keys are now properly protected
- Personal data (if any) should comply with GDPR/privacy laws
- Consider adding privacy policy if handling user data

### Audit Trail
- All database operations are logged
- Consider implementing audit logging for sensitive operations
- Maintain security patches and update history

---

## Contact

For security concerns or to report vulnerabilities:
- Create a private security advisory on GitHub
- Follow responsible disclosure practices
- Do not publicly disclose vulnerabilities until patched

---

## Dependency Security Status

### Current Vulnerability Status (2026-04-18)

**pip-audit scan results:** 11 vulnerabilities in 8 packages — none in CryptoUpdate's direct application code.

| Package | Version | CVE / GHSA | Fix Version | Impact on CryptoUpdate |
|---------|---------|-----------|-------------|------------------------|
| requests | 2.32.5 | CVE-2026-25645 | 2.33.0 | ⚠️ Direct dep — upgrade recommended |
| pillow | 12.1.1 | CVE-2026-40192 | 12.2.0 | ⚠️ Direct dep — upgrade recommended |
| flask | 3.1.2 | CVE-2026-27205 | 3.1.3 | ℹ️ Transitive (Streamlit) |
| mcp | 1.9.4 | CVE-2025-53365, CVE-2025-66416 | 1.10.0 / 1.23.0 | ℹ️ Dev/tool dep only |
| pygments | 2.19.2 | CVE-2026-4539 | 2.20.0 | ℹ️ Transitive |
| python-multipart | 0.0.22 | CVE-2026-40347 | 0.0.26 | ℹ️ Transitive (Streamlit) |
| tornado | 6.5.4 | GHSA-78cv + 2 CVEs | 6.5.5 | ℹ️ Transitive (Streamlit) |
| werkzeug | 3.1.5 | CVE-2026-27199 | 3.1.6 | ℹ️ Transitive (Streamlit) |

### Current Dependency Versions

| Package | Version | Notes |
|---------|---------|-------|
| streamlit | 1.54.0 | Latest |
| anthropic | 0.79.0 | Latest |
| requests | 2.32.5 | CVE-2026-25645 pending upgrade |
| urllib3 | 2.6.3 | Latest |
| pandas | 2.3.3 | Latest |
| pillow | 12.1.1 | CVE-2026-40192 pending upgrade |
| jinja2 | 3.1.6 | Latest |
| certifi | 2026.1.4 | Latest |
| ruff | 0.15.0 | Latest |
| pylint | 4.0.4 | Latest |

---

## Version History

### Version 1.2 - 2026-04-18
- Code review security hardening across all modules:
  - Added broad `requests.exceptions.RequestException` catch in `_check_marketraccoon` — prevents unhandled SSL/proxy/redirect errors crashing the sidebar
  - Added network error handling in `cmc.py` for both fiat and crypto price requests
  - Fixed `temp_path` pre-initialization in `fiat_cache.py` — deterministic cleanup in exception handlers (`if "temp_path" in locals()` was fragile)
  - Replaced all `traceback.print_exc()` with `logger.exception()` — stack traces now flow through the structured logging pipeline instead of stdout
  - Retry with exponential backoff for fiat currency API (ratesdb.com) — handles transient 429/5xx gracefully
  - Fixed `drop_duplicate()` to use `DELETE` + `append` instead of `to_sql(if_exists="replace")` — avoids unintended table DROP under concurrent access
- Updated pip-audit scan results (11 vulns in 8 packages, 2 in direct deps)

### Version 1.1 - 2025-10-22
- Upgraded all dependencies to latest secure versions
- Addressed 25+ package updates including 4 major version upgrades
- Documented pip vulnerability mitigation via Python 3.12.3 PEP 706
- Verified all CVEs fixed in updated packages

### Version 1.0 - 2025-10-22
- Initial security audit completed
- Fixed 4 critical/high severity vulnerabilities
- Implemented security best practices
- Created security documentation

---

## Additional Resources

- [OWASP Top 10](https://owasp.org/www-project-top-ten/)
- [Python Security Best Practices](https://python.readthedocs.io/en/latest/library/security_warnings.html)
- [Streamlit Security Guidelines](https://docs.streamlit.io/knowledge-base/deploy/authentication-without-sso)
- [SQLite Security](https://www.sqlite.org/security.html)
