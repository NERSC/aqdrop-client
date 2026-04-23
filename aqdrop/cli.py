#/usr/bin/env python3

import importlib
import argparse


def main():
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("action", nargs="?", default=None, help="The action to be performed.")
    pre_args, remaining = parser.parse_known_args()

    if pre_args.action is None:
        parser.add_argument("-h", "--help", action="store_true")
        pre_args, remaining = parser.parse_known_args()
        if not pre_args.help:
            print("Usage: aqdrop <action> [args...]. Use aqdrop --help for help.")
        print("The following actions are available. For more detailed usage information, type \"aqdrop <action> --help\".")

        import aqdrop.actions
        import pkgutil
        for info in pkgutil.iter_modules(path=aqdrop.actions.__path__):
            print(f"\t{info.name}")

        return

    my_module = importlib.import_module(f"aqdrop.actions.{pre_args.action}")
    parser.add_argument('-h', '--help', action='help', default='==SUPPRESS==', help="Show help for module.")
    my_module.add_args(parser)

    args = parser.parse_args()

    my_module.main(args)


if __name__ == "__main__":
    main()
