# Contributing to LimX CLI

Thank you for helping improve LimX CLI. This project welcomes focused contributions that make the CLI, Scratch bridge, documentation, packaging, or tests safer and easier to use.

## Contribution Scope

In scope:

- CLI commands and JSON output behavior.
- Signaling WebSocket client behavior.
- Scratch bridge and safe block exposure.
- Packaging, CMake install layout, and runtime bundle scripts.
- Documentation, examples, tests, and issue templates.
- Bug fixes that preserve robot safety defaults such as dry-run and bounded motion.

Out of scope unless maintainers explicitly agree first:

- Robot firmware, low-level motor control, or safety controller changes.
- Cloud account, fleet, billing, or production authorization systems.
- Adding secrets, internal credentials, private robot data, or environment-specific configuration.
- Broad rewrites or unrelated formatting churn.
- New high-risk robot actions without tests, dry-run behavior, and documentation.

## Reporting Issues

Before opening an issue, please search existing issues and check the README.

For bug reports, include:

- LimX CLI version or commit.
- Operating system and Python version.
- How LimX CLI was installed or run.
- Exact command, expected result, and actual result.
- Relevant logs with secrets, tokens, internal hostnames, and robot identifiers removed.

For feature requests, describe:

- The user problem.
- The target audience.
- The proposed behavior.
- Safety considerations and non-goals.

Security issues must not be reported in public issues. See SECURITY.md.

## Pull Requests

1. Open an issue or discussion first for behavior changes or larger work.
2. Keep pull requests focused and small enough to review.
3. Add or update tests for behavior changes.
4. Update README, CHANGELOG, NOTICE, or templates when relevant.
5. Run the test suite before submitting.

Recommended checks:

```bash
python3 -m pytest tests/ -q
cmake -S . -B build
```

If your change affects installation layout or runtime wrappers, also test a local install:

```bash
cmake --build build
cmake --install build --prefix install
install/bin/limx-cli --help
install/bin/limx-scratch --help
```

## Coding Guidelines

- Prefer clear, conservative changes over clever abstractions.
- Preserve JSON output for automation workflows.
- Preserve `--dry-run` and bounded command behavior for risky robot operations.
- Do not commit generated build outputs, secrets, tokens, robot logs, or local runtime data.
- Keep third-party notices and licenses intact.
