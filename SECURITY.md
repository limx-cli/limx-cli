# Security Policy

LimX CLI can send commands to real robots through a signaling WebSocket API. Please treat security issues carefully and do not disclose exploitable details in public issues.

## Reporting a Vulnerability

Do not open a public GitHub issue for vulnerabilities.

Report security issues through one of these private channels:

- Email: it@limxdynamics.com
- If your organization has a private disclosure process with LimX, use that channel.

Please include:

- A concise description of the issue.
- Affected versions or commits.
- Reproduction steps or proof of concept, if safe to share privately.
- Potential impact on robot safety, data exposure, authentication, or command execution.
- Suggested mitigation, if available.

Avoid including secrets, tokens, private keys, personal data, customer data, or live robot credentials in the report.

## Supported Versions

This repository is currently at the `0.1.x` initial release stage. Security fixes are expected to target the latest public release and the default development branch unless maintainers document otherwise.

## Safety Notes

- Use `--dry-run` before high-risk motion, action, dance, audio, or display-changing commands.
- Do not expose `limx-scratch` or robot signaling ports to untrusted networks.
- Do not commit real robot credentials, internal hostnames, API tokens, logs with account identifiers, or local data captures.
- When testing suspected vulnerabilities, use a safe lab robot or simulator and follow local robot safety procedures.
