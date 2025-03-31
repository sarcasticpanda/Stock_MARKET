import yfinance as yf
import pandas as pd
import plotly.graph_objs as go
from datetime import datetime, timedelta
import schedule
import time
import json
import os

# Cache for real-time data
stock_cache = {}

# Watchlist and pinned charts storage
WATCHLIST_FILE = "watchlist.json"
PINNED_FILE = "pinned.json"

def load_json(file):
    if os.path.exists(file):
        with open(file, "r") as f:
            return json.load(f)
    return []

def save_json(file, data):
    with open(file, "w") as f:
        json.dump(data, f)

def fetch_stock_data(symbol, period="1d", interval="1h"):
    try:
        stock = yf.Ticker(symbol)
        data = stock.history(period=period, interval=interval)
        if data.empty:
            print(f"No data found for {symbol} with period={period}, interval={interval}")
            return pd.DataFrame()
        
        required_columns = ["Open", "High", "Low", "Close", "Volume"]
        if not all(col in data.columns for col in required_columns):
            print(f"Missing required columns in data for {symbol}: {data.columns}")
            return pd.DataFrame()
        return data
    except Exception as e:
        print(f"Error fetching data for {symbol}: {e}")
        return pd.DataFrame()

def fetch_historical_data(symbol, start_date, end_date):
    try:
        stock = yf.Ticker(symbol)
        data = stock.history(start=start_date, end=end_date)
        if data.empty:
            print(f"No historical data found for {symbol} between {start_date} and {end_date}")
            return pd.DataFrame()
        return data
    except Exception as e:
        print(f"Error fetching historical data for {symbol}: {e}")
        return pd.DataFrame()

def get_stock_chart(data, symbol, historical_data=None, period="1d", chart_type="candlestick"):
    if data.empty:
        return "<p>No data available to display chart.</p>"
    
    print(f"Data for {symbol} (period={period}): {data.head()}")  # Debugging output

    fig = go.Figure()

    # Define chart based on chart_type
    if chart_type == "candlestick":
        # Enhanced Candlestick chart
        fig.add_trace(go.Candlestick(
            x=data.index,
            open=data["Open"],
            high=data["High"],
            low=data["Low"],
            close=data["Close"],
            name=f"{symbol} Price",
            increasing_line_color='#00E676',  # Bright lime green for uptrend
            decreasing_line_color='#FF1744',  # Bright red for downtrend
        ))
        # Historical data (if available)
        if historical_data is not None and not historical_data.empty:
            print(f"Historical data for {symbol}: {historical_data.head()}")
            fig.add_trace(go.Candlestick(
                x=historical_data.index,
                open=historical_data["Open"],
                high=historical_data["High"],
                low=historical_data["Low"],
                close=historical_data["Close"],
                name=f"{symbol} Historical",
                increasing_line_color='#26C6DA',  # Cyan for historical uptrend
                decreasing_line_color='#EF5350',  # Light red for historical downtrend
                opacity=0.4
            ))
    elif chart_type == "line":
        # Line chart
        fig.add_trace(go.Scatter(
            x=data.index,
            y=data["Close"],
            mode="lines",
            name=f"{symbol} Price",
            line=dict(color='#00E676', width=2)  # Bright lime green
        ))
        if historical_data is not None and not historical_data.empty:
            fig.add_trace(go.Scatter(
                x=historical_data.index,
                y=historical_data["Close"],
                mode="lines",
                name=f"{symbol} Historical",
                line=dict(color='#26C6DA', width=2, dash="dash"),  # Cyan dashed line
                opacity=0.4
            ))
    elif chart_type == "ohlc":
        # OHLC chart
        fig.add_trace(go.Ohlc(
            x=data.index,
            open=data["Open"],
            high=data["High"],
            low=data["Low"],
            close=data["Close"],
            name=f"{symbol} Price",
            increasing_line_color='#00E676',  # Bright lime green
            decreasing_line_color='#FF1744'   # Bright red
        ))
        if historical_data is not None and not historical_data.empty:
            fig.add_trace(go.Ohlc(
                x=historical_data.index,
                open=historical_data["Open"],
                high=historical_data["High"],
                low=historical_data["Low"],
                close=historical_data["Close"],
                name=f"{symbol} Historical",
                increasing_line_color='#26C6DA',
                decreasing_line_color='#EF5350',
                opacity=0.4
            ))

    # Enhanced Volume bars
    fig.add_trace(go.Bar(
        x=data.index,
        y=data["Volume"],
        name="Volume",
        yaxis="y2",
        opacity=0.5,  # Semi-transparent
        marker_color='#FFD600'  # Bright yellow for volume
    ))

    # Improved Layout
    fig.update_layout(
        title=f"<b>{symbol} Stock Analysis ({period})</b>",
        title_font=dict(size=22, color="white"),
        yaxis_title="Price (USD)",
        yaxis2=dict(
            title="Volume",
            overlaying="y",
            side="right",
            gridcolor="rgba(255, 255, 255, 0.1)"  # Softer grid
        ),
        template="plotly_dark",
        height=650,
        margin=dict(l=40, r=40, t=40, b=40),
        showlegend=True,
        hovermode="x unified",
        xaxis=dict(
            rangeslider=dict(visible=True),
            type="date",
            title="Date/Time",
            showgrid=True,
            gridcolor="rgba(255, 255, 255, 0.1)"
        ),
        yaxis=dict(
            title="Price (USD)",
            gridcolor="rgba(255, 255, 255, 0.1)"
        ),
        legend=dict(
            font=dict(size=12),
            bgcolor="rgba(0,0,0,0.3)",  # Slightly transparent background
            bordercolor="white",
            borderwidth=1
        )
    )

    return fig.to_html(full_html=False, include_plotlyjs="cdn")

def check_alerts(symbol, threshold, current_price):
    if current_price >= threshold:
        return f"Alert: {symbol} crossed {threshold} (Current: {current_price})"
    return None

def update_cache():
    global stock_cache
    for symbol in stock_cache.keys():
        period = "1d"
        interval = "1h"
        if period == "1mo":
            interval = "1d"
        elif period == "5d":
            interval = "4h"
        data = fetch_stock_data(symbol, period=period, interval=interval)
        stock_cache[symbol] = data

schedule.every(1).minutes.do(update_cache)

def run_scheduler():
    while True:
        schedule.run_pending()
        time.sleep(1)

def add_to_watchlist(symbol):
    watchlist = load_json(WATCHLIST_FILE)
    if symbol not in watchlist:
        watchlist.append(symbol)
        save_json(WATCHLIST_FILE, watchlist)

def remove_from_watchlist(symbol):
    watchlist = load_json(WATCHLIST_FILE)
    if symbol in watchlist:
        watchlist.remove(symbol)
        save_json(WATCHLIST_FILE, watchlist)

def add_to_pinned(symbol):
    pinned = load_json(PINNED_FILE)
    if symbol not in pinned:
        pinned.append(symbol)
        save_json(PINNED_FILE, pinned)

def remove_from_pinned(symbol):
    pinned = load_json(PINNED_FILE)
    if symbol in pinned:
        pinned.remove(symbol)
        save_json(PINNED_FILE, pinned)