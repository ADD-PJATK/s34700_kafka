# Realtime App (Streamlit)

This app is a live stock dashboard built with Python + Streamlit.

## Features

- Loads available tickers from `GET /api/tickers`
- Lets you select one or more tickers
- Streams live updates from `GET /api/stream?ticker=...` (SSE)
- Shows ticker, price, and timestamp
- Keeps the latest 30 ticks in memory
- Displays a recent ticks table and simple price chart
- Handles missing API key and API/connection errors gracefully

## Install

```bash
pip install -r requirements.txt
```

## Configure API Key

The API key must come from an environment variable named `ADD_API_KEY`.

macOS/Linux:

```bash
export ADD_API_KEY="your_key_here"
```

Windows PowerShell:

```powershell
$env:ADD_API_KEY="your_key_here"
```

## Run

```bash
streamlit run app.py
```

## API Endpoints Used

- Base URL: `https://add.piotrkojalowicz.dev`
- `GET /api/tickers`
- `GET /api/stream?ticker=...`
- Auth header: `X-API-Key`

## Security Warning

- Never hardcode your API key in source code.
- Never commit `.env` or any file containing real secrets.
