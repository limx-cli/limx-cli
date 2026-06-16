from setuptools import find_packages, setup


setup(
    name="limx-cli",
    version="0.1.0",
    description="Agent-native CLI harness for the LimX robot signaling WebSocket skills",
    packages=find_packages(),
    py_modules=["limx_cli_entrypoints"],
    include_package_data=True,
    package_data={"limx-cli": ["*.js", "vendor/**/*"]},
    entry_points={
        "console_scripts": [
            "limx-cli=limx_cli_entrypoints:cli_main",
            "limx-scratch=limx_cli_entrypoints:scratch_main",
        ],
    },
    python_requires=">=3.8",
)
