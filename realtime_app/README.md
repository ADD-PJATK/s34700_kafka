# Realtime App

This app will be the live stock dashboard.

## Goal

- Connect to `https://add.piotrkojalowicz.dev/api/stream` using Server-Sent Events (SSE)
- Display live stock price updates in real time

## Security

- Read API key from environment variable: `ADD_API_KEY`
- Send key in request header: `X-API-Key`
- Never hardcode or commit real API keys
