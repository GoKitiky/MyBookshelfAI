# Security

## Supported versions

Security updates are applied to the default branch (`main`). Use the latest commit for production-style deployments.

## Reporting a vulnerability

Please **do not** open a public GitHub issue for security reports.

Instead, use one of these options:

1. **[GitHub Security Advisories](https://github.com/GoKitiky/MyBookshelfAI/security/advisories/new)** (preferred if you have a GitHub account).
2. Open a **private** vulnerability report via the repository’s **Security** tab, if enabled.

Include steps to reproduce, affected component (API, frontend, Docker setup), and impact. We will acknowledge receipt as soon as we can.

## Scope notes

MyBookshelfAI is a **self-hosted, local-first** app. You supply your own LLM API keys; treat this repository and your deployment like any other service that handles credentials—use strong keys, limit provider-side permissions where possible, and do not commit `.env` or database files to git.
