"""CLI entrypoint for the local HPS backend service."""

from __future__ import annotations

import argparse


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the local HPS backend service.")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", default=8765, type=int)
    args = parser.parse_args()

    import uvicorn

    uvicorn.run("hps.api.app:app", host=args.host, port=args.port, reload=False, log_level="warning")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
