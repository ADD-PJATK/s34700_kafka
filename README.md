# Real-time Stock Data Project (Kafka/SSE)

This project is a beginner-friendly university assignment setup for working with real-time and recent stock data from an API.

## Project Structure

- `realtime_app/` - Live dashboard app that will connect to `/api/stream` using Server-Sent Events (SSE) and display live stock price updates.
- `history_app/` - Recent data viewer/downloader app that will call `/api/latest`, show recent stock data, and support saving as CSV or JSON.
- `screenshots/` - Folder for assignment screenshots.

## API Configuration

- Base URL: `https://add.piotrkojalowicz.dev`
- Authentication header: `X-API-Key`
- API key environment variable: `ADD_API_KEY`

Important: configure your API key locally (for example in a `.env` file) and never commit real secrets to git.
