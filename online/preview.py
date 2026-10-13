"""Online-mode UI preview on loopback only; NOT a production server."""
import argparse
from shared_ui.server import serve


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=8766)
    args = parser.parse_args()
    serve("online", args.port)


if __name__ == "__main__":
    main()
