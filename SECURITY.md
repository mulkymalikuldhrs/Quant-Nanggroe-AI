# Security Policy

## Supported Versions

| Version | Supported |
|---------|-----------|
| 4.0.x   | ✅ Active |
| < 4.0   | ❌ Unsupported |

## Reporting a Vulnerability

Report security vulnerabilities to **Mulky Malikul Dhaher** via:
- **GitHub Issues**: https://github.com/dhaher-labs/Quant-Nanggroe-AI/issues
- **GitLab**: https://gitlab.com/mulkymalikuldhr
- **Email**: mulkymalikuldhr@dhaher-labs.codeberg.page

Response SLA: 48 hours for critical issues.

## Security Architecture

### Authentication & Authorization
- JWT-based authentication with configurable secrets
- Role-based access control via `QNAI_JWT_SECRET`
- All protected routes validated through middleware

### Credential Management
- API keys stored via `pydantic-settings` from environment
- `.env` files excluded from version control (`.gitignore`)
- `.env.example` provided with placeholder values
- `credential_inference.py` handles secure credential resolution
- `keyvault.py` provides encryption-at-rest via `cryptography` library
- Never hardcode secrets — always use `Settings` class

### Data Protection
- PII redaction in logs via `security/audit.py`
- SQLAlchemy parameterized queries prevent SQL injection
- Audit logging for all trading operations

### Network Security
- Redis requires authentication (`REDIS_PASSWORD`)
- Database access controlled via `DATABASE_URL`
- CORS configured in FastAPI app

### Monitoring & Incident Response
- Prometheus metrics for anomaly detection
- Kill switch mechanism for emergency stop
- Security scan CI job runs on every push
- Pre-commit hooks enforce security checks

## Best Practices for Contributors

1. **NEVER** commit `.env` files or real API keys
2. **NEVER** hardcode secrets — use `Settings` from `pydantic-settings`
3. **ALWAYS** run `pre-commit` before pushing
4. **ALWAYS** use parameterized queries, never string formatting for SQL
5. **REPORT** any discovered credentials in the codebase immediately
6. **USE** `keyvault.py` for encrypting sensitive data at rest
