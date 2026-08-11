# Security Policy

## Supported versions

| Version | Supported |
|---------|-----------|
| 0.2.x   | Yes       |

## Reporting a vulnerability

If you find a security issue (e.g. path traversal, unsafe file handling, or code execution via crafted STEP input), please **do not** open a public GitHub issue.

Instead, contact the repository owner privately (GitHub security advisory or direct message) with:

- Description of the issue
- Steps to reproduce
- Impact assessment (if known)

We will acknowledge reports within a reasonable time and coordinate a fix before any public disclosure.

## Scope

This tool reads local STEP files and writes export/index data to disk. It does not expose a network service. Typical risks are limited to local file system access when processing untrusted STEP files.
