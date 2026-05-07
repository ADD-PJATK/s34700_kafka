"""
Realtime stock dashboard placeholder app.
"""

import os


BASE_URL = "https://add.piotrkojalowicz.dev"
STREAM_ENDPOINT = "/api/stream"


def main() -> None:
    api_key = os.getenv("ADD_API_KEY")

    if not api_key:
        print("Missing ADD_API_KEY environment variable.")
        print("Create a local .env file or export ADD_API_KEY before running.")
        return

    print("Realtime app placeholder")
    print(f"Base URL: {BASE_URL}")
    print(f"Endpoint: {STREAM_ENDPOINT}")
    print("Next step: connect to SSE stream and render live prices.")


if __name__ == "__main__":
    main()
