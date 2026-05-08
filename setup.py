from setuptools import find_packages, setup


setup(
    name="limx-agent-harness",
    version="0.1.0",
    description="Agent-native CLI harness for the LimX robot signaling WebSocket skills",
    packages=find_packages(),
    include_package_data=True,
    package_data={"limx_agent_harness": ["*.js", "vendor/**/*"]},
    install_requires=["websocket-client>=1.6"],
    entry_points={
        "console_scripts": [
            "limx-cli=limx_agent_harness.cli:main",
            "limx-scratch=limx_agent_harness.scratch_bridge:main",
        ],
    },
    python_requires=">=3.8",
)
