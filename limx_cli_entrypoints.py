from importlib import import_module


def cli_main():
    return import_module("limx-cli.cli").main()


def scratch_main():
    return import_module("limx-cli.scratch_bridge").main()