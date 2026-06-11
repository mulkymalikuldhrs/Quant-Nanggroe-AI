# Security Policy

## Reporting a Vulnerability

If you discover a security vulnerability within this project, please send an email to **mulkymalikuldhaher@email.com**. All security vulnerabilities will be promptly addressed.

Please do not publicly disclose the vulnerability until it has been addressed by the maintainers.

## Supported Versions

| Version | Supported          |
| ------- | ------------------ |
| 15.3.x  | ✅ Active          |
| < 15.0  | ❌ End of Life     |

## Security Measures

### API Key Protection
- API keys are **never** injected into the client-side bundle via Vite's `define` config
- All API keys are managed at runtime through the application's Settings panel
- Keys are stored in the browser's IndexedDB/localStorage (client-side only)
- `.env.example` is provided as a template; actual `.env` files are gitignored

### Data Security
- All dependencies are regularly audited for known vulnerabilities
- Sensitive data is never logged to external services
- API keys and credentials must never be committed to version control
- Error messages are sanitized in production to prevent information disclosure
- ErrorBoundary does not expose internal error details in production mode

### Input Validation
- All market data inputs are validated before processing
- Chat command inputs are sanitized
- CORS proxy rotation limits exposure to any single proxy service

### Runtime Security
- Google OAuth tokens are scoped to Drive.file and Drive.readonly
- Access tokens for Google Drive are stored in localStorage with appropriate scoping
- BrowserCore sanitizes fetched HTML by removing `<script>`, `<style>`, `<iframe>` tags
- No arbitrary code execution from user inputs

### Known Limitations
- This is a **client-side only** application — all data resides in the user's browser
- In-memory caches (price data, audit logs) are lost on page refresh
- CORS proxies are third-party services; their availability and security are not guaranteed
- The ResearchAgent makes periodic network requests to public APIs
- No server-side authentication — the app is designed for single-user local operation

## Best Practices

- Always use the latest stable version
- Keep your API keys and credentials secure
- Never share your Google OAuth access token
- Report any suspicious behavior immediately
- Follow responsible disclosure guidelines
- Review the `.env.example` file for all configurable environment variables

---

> ⚠️ **For Education Purpose Only**
>
> This project is provided strictly for educational and research purposes. The authors and contributors assume **no responsibility or liability** for any damages, losses, or risks arising from the use of this software. **We do not bear any responsibility or risk** for how this software is used.
>
> **Contact:** Mulky Malikul Dhaher | mulkymalikuldhaher@email.com
