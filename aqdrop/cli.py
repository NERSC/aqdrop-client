#!/usr/bin/env python3

import importlib
import argparse


def print_available_actions():
    print("The following actions are available. For more detailed usage information, type \"aqdrop <action> --help\".")
    import aqdrop.actions
    import pkgutil
    import importlib

    header = f" {'Action':<20} {'LDAP access':<34} {'Description':<40}"
    print(header)
    print("-" * len(header))

    for info in pkgutil.iter_modules(path=aqdrop.actions.__path__):
        module = importlib.import_module(f"aqdrop.actions.{info.name}")
        action_info = getattr(module, "action_info")()
        print(f" {info.name:<20} {action_info['access']:<34} {action_info['description']:<40}")


def main():
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("action", nargs="?", default=None, help="The action to be performed.")
    pre_args, remaining = parser.parse_known_args()

    if pre_args.action is None:
        parser.add_argument("-h", "--help", action="store_true")
        pre_args, remaining = parser.parse_known_args()
        if not pre_args.help:
            print("Usage: aqdrop <action> [args...]. Use aqdrop --help for help.")
        print_available_actions()
        return

    try:
        my_module = importlib.import_module(f"aqdrop.actions.{pre_args.action}")
    except ModuleNotFoundError:
        print(f"Error: '{pre_args.action}' is not a supported action.")
        print()
        print_available_actions()
        return

    # Create a new parser for the specific action to avoid mixing all action args into the main help
    action_parser = argparse.ArgumentParser(prog=f"aqdrop {pre_args.action}")
    my_module.add_args(action_parser)

    # Parse the remaining arguments using the action-specific parser
    args = action_parser.parse_args(remaining)

    my_module.main(args)


if __name__ == "__main__":
    main()
