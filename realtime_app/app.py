import json
import os
import threading
from collections import deque
from datetime import datetime
from typing import Any

import pandas as pd
import requests
import streamlit as st
from sseclient import SSEClient
from streamlit_autorefresh import st_autorefresh

BASE_URL = "https://add.piotrkojalowicz.dev"
TICKERS_ENDPOINT = "/api/tickers"
STREAM_ENDPOINT = "/api/stream"
MAX_TICKS = 30
REQUEST_TIMEOUT = 10
TICKERS_CACHE_TTL_SECONDS = 600


def api_headers(api_key: str) -> dict[str, str]:
    return {"X-API-Key": api_key}


def _extract_tickers(payload: Any) -> list[str]:
    tickers: list[str] = []

    if isinstance(payload, dict):
        if isinstance(payload.get("tickers"), list):
            payload = payload["tickers"]
        elif isinstance(payload.get("data"), list):
            payload = payload["data"]
        else:
            payload = []

    if isinstance(payload, list):
        for item in payload:
            if isinstance(item, str):
                tickers.append(item)
            elif isinstance(item, dict):
                ticker = item.get("ticker") or item.get("symbol")
                if isinstance(ticker, str):
                    tickers.append(ticker)

    return sorted(set(tickers))


@st.cache_data(ttl=TICKERS_CACHE_TTL_SECONDS, show_spinner=False)
def fetch_tickers(api_key: str) -> list[str]:
    response = requests.get(
        f"{BASE_URL}{TICKERS_ENDPOINT}",
        headers=api_headers(api_key),
        timeout=REQUEST_TIMEOUT,
    )
    response.raise_for_status()
    payload = response.json()
    return _extract_tickers(payload)


def parse_tick(raw_data: dict[str, Any], fallback_ticker: str) -> dict[str, Any]:
    ticker = raw_data.get("ticker") or raw_data.get("symbol") or fallback_ticker
    price = raw_data.get("price")
    ts = raw_data.get("timestamp") or raw_data.get("time")

    if ts:
        try:
            dt = datetime.fromisoformat(str(ts).replace("Z", "+00:00"))
            ts_display = dt.strftime("%Y-%m-%d %H:%M:%S")
        except ValueError:
            ts_display = str(ts)
    else:
        ts_display = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    return {"ticker": str(ticker), "price": price, "timestamp": ts_display}


def stream_ticker(ticker: str, api_key: str, stop_event: threading.Event) -> None:
    try:
        response = requests.get(
            f"{BASE_URL}{STREAM_ENDPOINT}",
            headers=api_headers(api_key),
            params={"ticker": ticker},
            stream=True,
            timeout=REQUEST_TIMEOUT,
        )
        response.raise_for_status()

        client = SSEClient(response)
        for event in client.events():
            if stop_event.is_set():
                break
            if not event.data:
                continue

            try:
                data = json.loads(event.data)
            except json.JSONDecodeError:
                continue

            tick = parse_tick(data, ticker)
            with st.session_state["ticks_lock"]:
                st.session_state["ticks"].append(tick)
    except Exception as exc:
        with st.session_state["ticks_lock"]:
            st.session_state["errors"].append(f"{ticker}: {exc}")


def init_state() -> None:
    if "ticks" not in st.session_state:
        st.session_state["ticks"] = deque(maxlen=MAX_TICKS)
    if "errors" not in st.session_state:
        st.session_state["errors"] = deque(maxlen=10)
    if "workers" not in st.session_state:
        st.session_state["workers"] = {}
    if "ticks_lock" not in st.session_state:
        st.session_state["ticks_lock"] = threading.Lock()


def sync_stream_workers(selected_tickers: list[str], api_key: str) -> None:
    workers = st.session_state["workers"]
    selected_set = set(selected_tickers)
    running_set = set(workers.keys())

    for ticker in running_set - selected_set:
        workers[ticker]["stop_event"].set()
        del workers[ticker]

    for ticker in selected_set - running_set:
        stop_event = threading.Event()
        thread = threading.Thread(
            target=stream_ticker,
            args=(ticker, api_key, stop_event),
            daemon=True,
        )
        workers[ticker] = {"thread": thread, "stop_event": stop_event}
        thread.start()


def render_ticks() -> None:
    ticks = list(st.session_state["ticks"])
    if not ticks:
        st.info("No live ticks yet. Select at least one ticker and wait for updates.")
        return

    ticks_df = pd.DataFrame(ticks)
    ticks_df = ticks_df.tail(MAX_TICKS).reset_index(drop=True)

    st.subheader("Recent Ticks")
    st.dataframe(ticks_df, use_container_width=True)

    chart_df = ticks_df.copy()
    chart_df["price"] = pd.to_numeric(chart_df["price"], errors="coerce")
    chart_df = chart_df.dropna(subset=["price"])

    if not chart_df.empty:
        chart_df["row"] = range(len(chart_df))
        pivot_df = chart_df.pivot(index="row", columns="ticker", values="price")
        st.subheader("Price Chart")
        st.line_chart(pivot_df)
    else:
        st.warning("No numeric price values available yet for charting.")


def main() -> None:
    st.set_page_config(page_title="Realtime Stock Dashboard", layout="wide")
    st.title("Realtime Stock Dashboard")
    st.caption("Live data from /api/stream via Server-Sent Events (SSE)")

    api_key = os.getenv("ADD_API_KEY")
    if not api_key:
        st.error(
            "Missing ADD_API_KEY environment variable. "
            "Set it locally before running this app."
        )
        st.stop()

    init_state()
    st_autorefresh(interval=2000, key="dashboard_refresh")

    try:
        tickers = fetch_tickers(api_key)
    except requests.HTTPError as exc:
        status_code = exc.response.status_code if exc.response is not None else None
        if status_code == 429:
            st.warning(
                "Too many requests while loading tickers (429). "
                "Please wait a moment and try again."
            )
        else:
            st.error("Failed to load tickers from /api/tickers. Please try again.")
        st.stop()
    except requests.RequestException:
        st.error("Could not connect to /api/tickers. Please check your network and try again.")
        st.stop()

    if not tickers:
        st.warning("No tickers were returned by /api/tickers.")
        st.stop()

    selected_tickers = st.multiselect(
        "Select one or more tickers",
        options=tickers,
        default=tickers[:1],
    )

    sync_stream_workers(selected_tickers, api_key)
    st.write(f"Active streams: {', '.join(selected_tickers) if selected_tickers else 'None'}")

    if st.session_state["errors"]:
        st.error("Connection/API errors:")
        for err in list(st.session_state["errors"]):
            st.write(f"- {err}")

    render_ticks()


if __name__ == "__main__":
    main()
