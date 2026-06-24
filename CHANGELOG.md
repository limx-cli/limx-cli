# Changelog

All notable changes to LimX CLI are documented here.

## Unreleased

### Fixed

- Ensure `websocket-client` is included in copyable deployment bundles by exposing it through legacy `setup.py` metadata and failing target builds if the bundled Python runtime is missing the `websocket` package.
- Rebuild the CMake deployment bundle when Python package metadata or CLI Python sources change, preventing stale bundles after dependency updates.

## [0.1.0] - 2026-06-17

### Added

- Initial LimX CLI command-line interface for LimX robot signaling WebSocket skills.
- JSON-first CLI output for automation and AI Agent workflows.
- Dry-run support for planning commands without sending robot control requests.
- Robot state, action, dance, audio, emoji, lock, raw request, and bounded motion command groups.
- Scratch bridge service with LimX Robot block extension support.
- Copyable CMake deployment bundle with bundled Python package resources and Node.js runtime.
- Agent Skill documentation in `SKILL.md`.
- Unit tests for CLI, signaling client, and Scratch bridge behavior.

### Known Limitations

- Hardware coverage is focused on Oli-style workflows; other robot families need validation.
- `limx-scratch` is intended for trusted local networks and should not be exposed to the public internet.
- Long-running production orchestration, fleet management, cloud account management, and authorization policy enforcement are out of scope.
- The Scratch UI is based on Scratch GUI and carries GPL-3.0 distribution obligations when included in releases.
- Wheel filenames are normalized by Python packaging standards, so the built artifact is named like `limx_cli-0.1.0-py3-none-any.whl` even though the project name is `limx-cli`.
