# Security Policy

## Supported versions

| Version | Supported |
|---------|-----------|
| 0.2.x   | Yes       |

## Reporting a vulnerability

If you find a security issue (path traversal, unsafe file handling, or similar),
please do not open a public GitHub issue.

Contact the repository owner privately (GitHub security advisory or a direct
message) and include:

- What the issue is
- How to reproduce it
- Impact, if you know it

Reports are acknowledged when possible, and a fix can be coordinated before any
public disclosure.

## Scope

StepSplit reads local STEP files and writes export/index data to disk. It does
not expose a network service. Typical risks are limited to local filesystem
access when processing untrusted STEP input. The source STEP file is opened
read-only; exports refuse to overwrite the source (including hard links).
