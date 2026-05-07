import json
import os
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


def fetch_first_tick_from_stream(ticker: str, api_key: str) -> dict[str, Any] | None:
    response = requests.get(
        f"{BASE_URL}{STREAM_ENDPOINT}",
        headers=api_headers(api_key),
        params={"ticker": ticker},
        stream=True,
        timeout=REQUEST_TIMEOUT,
    )
    response.raise_for_status()

    client = SSEClient(response)
    try:
        for event in client.events():
            if not event.data:
                continue
            try:
                data = json.loads(event.data)
            except json.JSONDecodeError:
                continue
            return parse_tick(data, ticker)
        return None
    finally:
        response.close()


def init_state() -> None:
    if "ticks" not in st.session_state:
        st.session_state["ticks"] = deque(maxlen=MAX_TICKS)
    if "errors" not in st.session_state:
        st.session_state["errors"] = deque(maxlen=10)
    if "auto_fetch_enabled" not in st.session_state:
        st.session_state["auto_fetch_enabled"] = False


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
        chart_df["timestamp_dt"] = pd.to_datetime(chart_df["timestamp"], errors="coerce")
        chart_df = chart_df.sort_values("timestamp_dt")

        if chart_df["timestamp_dt"].notna().any():
            time_df = chart_df.dropna(subset=["timestamp_dt"])
            time_pivot = (
                time_df.groupby(["timestamp_dt", "ticker"], as_index=False)["price"]
                .last()
                .pivot(index="timestamp_dt", columns="ticker", values="price")
                .sort_index()
            )

            st.subheader("Price Trend Over Time")
            st.line_chart(time_pivot)
        else:
            chart_df["row"] = range(len(chart_df))
            pivot_df = chart_df.pivot(index="row", columns="ticker", values="price")
            st.subheader("Price Trend Over Time")
            st.line_chart(pivot_df)
    else:
        st.warning("No numeric price values available yet for charting.")


def fetch_ticks_for_selected_tickers(selected_tickers: list[str], api_key: str) -> int:
    success_count = 0
    for ticker in selected_tickers:
        try:
            tick = fetch_first_tick_from_stream(ticker, api_key)
            if tick is not None:
                st.session_state["ticks"].append(tick)
                success_count += 1
            else:
                st.session_state["errors"].append(f"{ticker}: Stream did not return a tick event.")
        except requests.HTTPError as exc:
            status_code = exc.response.status_code if exc.response is not None else None
            if status_code == 429:
                st.session_state["errors"].append(
                    f"{ticker}: Too many requests (429). Please wait and try again."
                )
            else:
                st.session_state["errors"].append(
                    f"{ticker}: Stream request failed with status {status_code}."
                )
        except requests.RequestException:
            st.session_state["errors"].append(
                f"{ticker}: Network/API connection issue while reading stream."
            )
        except Exception as exc:
            st.session_state["errors"].append(f"{ticker}: Unexpected error: {exc}")
    return success_count


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

    selected_text = ", ".join(selected_tickers) if selected_tickers else "None"
    st.markdown(f"**Selected tickers: {selected_text}**")
    st.markdown(f"**Successful ticks received: {len(st.session_state['ticks'])}**")
    st.info("Because the API is rate limited, click the fetch button once and wait.")

    fetch_clicked = st.button("Fetch live tick from stream")
    if fetch_clicked:
        if not selected_tickers:
            st.warning("Please select at least one ticker.")
        else:
            st.session_state["auto_fetch_enabled"] = True
            success_count = fetch_ticks_for_selected_tickers(selected_tickers, api_key)
            if success_count > 0:
                st.success(f"Received {success_count} live tick(s) from /api/stream.")

    if st.session_state["auto_fetch_enabled"] and selected_tickers and not fetch_clicked:
        st.caption("Auto-updating every 10 seconds for selected tickers.")
        st_autorefresh(interval=10_000, key="stream_auto_refresh")
        success_count = fetch_ticks_for_selected_tickers(selected_tickers, api_key)
        if success_count > 0:
            st.success(f"Auto-fetched {success_count} live tick(s).")

    if st.session_state["errors"]:
        st.info("Failed ticker messages:")
        for err in list(st.session_state["errors"]):
            st.write(f"- {err}")

    render_ticks()


if __name__ == "__main__":
    main()
