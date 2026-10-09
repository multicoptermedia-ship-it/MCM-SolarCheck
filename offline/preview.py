"""Offline shared-UI preview. Does not replace the existing PySide6 application yet."""
import argparse
from shared_ui.server import serve


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=8765)
    args = parser.parse_args()
    serve("offline", args.port)


if __name__ == "__main__":
    main()
