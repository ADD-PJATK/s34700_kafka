"""
Historical stock data viewer/downloader placeholder app.
"""

import os


BASE_URL = "https://add.piotrkojalowicz.dev"
LATEST_ENDPOINT = "/api/latest"


def main() -> None:
    api_key = os.getenv("ADD_API_KEY")

    if not api_key:
        print("Missing ADD_API_KEY environment variable.")
        print("Create a local .env file or export ADD_API_KEY before running.")
        return

    print("History app placeholder")
    print(f"Base URL: {BASE_URL}")
    print(f"Endpoint: {LATEST_ENDPOINT}")
    print("Next step: fetch latest data and add CSV/JSON download options.")


if __name__ == "__main__":
    main()
