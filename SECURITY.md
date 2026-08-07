# Security Policy

## Supported versions

Security fixes are applied to the latest release. Earlier alpha releases should be upgraded rather than treated as supported production versions.

## Reporting a vulnerability

Please do not open a public issue for a suspected vulnerability. Use GitHub's private vulnerability reporting feature for the repository. Include the affected version, reproduction steps, impact, and any suggested mitigation.

Uploaded scientific files are processed locally by default. The backend binds to `127.0.0.1`; exposing it to another interface is unsupported unless it is placed behind appropriate authentication and network controls.

## Sensitive data

Do not place credentials in the repository. Local Streamlit secrets belong in `.streamlit/secrets.toml`, which is ignored by Git. Diagnostic reports should not include uploaded scientific data unless the user explicitly chooses to share it.
