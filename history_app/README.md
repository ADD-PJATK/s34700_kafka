# History App

This app will be the recent stock data viewer and downloader.

## Goal

- Call `https://add.piotrkojalowicz.dev/api/latest`
- Display recent stock data
- Allow saving output as CSV or JSON

## Security

- Read API key from environment variable: `ADD_API_KEY`
- Send key in request header: `X-API-Key`
- Never hardcode or commit real API keys
