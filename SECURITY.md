# Security Policy

## Supported versions

| Version | Supported |
|---------|-----------|
| 0.2.x   | Yes       |
| < 0.2   | Best effort |

## Reporting a vulnerability

Please **do not** open a public GitHub issue for security vulnerabilities.

Report privately via GitHub Security Advisories for this repository:

https://github.com/Onur45500/bury-bench/security/advisories/new

Include:

- A short description of the issue
- Steps to reproduce
- Impact assessment (if known)
- Whether you have a suggested fix

We aim to acknowledge reports within **7 days** and to share a remediation plan
or status update within **30 days**.

## Scope notes

bury-bench is a local CLI evaluation harness. Typical concerns include:

- Accidental logging or committing of API keys from provider adapters
- Path traversal when loading user-supplied fixture/result paths
- Unsafe deserialization of untrusted result JSON (treat result files as trusted input from the operator)

Provider API keys must come from environment variables only. Never commit keys,
`.env` files, or live response dumps that contain secrets.
