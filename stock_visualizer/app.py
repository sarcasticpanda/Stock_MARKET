from flask import Flask, render_template, request, send_file, redirect, url_for
from stock_data import fetch_stock_data, fetch_historical_data, get_stock_chart, stock_cache, add_to_watchlist, remove_from_watchlist, add_to_pinned, remove_from_pinned, load_json
import pandas as pd
import io
from threading import Thread
import stock_data

app = Flask(__name__)

# Start scheduler in a separate thread
scheduler_thread = Thread(target=stock_data.run_scheduler, daemon=True)
scheduler_thread.start()

@app.route("/", methods=["GET", "POST"])
def index():
    symbols = list(stock_cache.keys())
    charts = []
    for symbol in symbols:
        data = stock_cache.get(symbol)
        if data is not None and not data.empty:
            chart = get_stock_chart(data, symbol, period="1d", chart_type="candlestick")
            charts.append((symbol, chart))
    return render_template("index.html", charts=charts)

@app.route("/stock/<symbol>", methods=["GET", "POST"])
def stock(symbol):
    chart = None
    alert = None
    error_message = None
    historical_data = None
    data = None  
    period = "1d"  
    interval = "1h"  
    chart_type = "candlestick"  

    if request.method == "POST":
        if "update" in request.form:
            threshold_str = request.form.get("threshold", "0")
            try:
                threshold = float(threshold_str) if threshold_str else 0.0
            except ValueError:
                threshold = 0.0  
            period = request.form.get("period", "1d")
            chart_type = request.form.get("chart_type", "candlestick")
            compare = request.form.get("compare", "no")

            interval = "1d" if period == "1mo" else "4h" if period == "5d" else "1h"
            stock_cache[symbol] = fetch_stock_data(symbol, period=period, interval=interval)
            data = stock_cache.get(symbol)

            if data is None or data.empty:
                error_message = f"Could not fetch data for {symbol}. Please check the symbol and try again."
            else:
                if compare == "yes":
                    start_date = request.form.get("start_date")
                    end_date = request.form.get("end_date")
                    if start_date and end_date:
                        historical_data = fetch_historical_data(symbol, start_date, end_date)

                chart = get_stock_chart(data, symbol, historical_data, period, chart_type)
                current_price = data["Close"].iloc[-1]
                alert = stock_data.check_alerts(symbol, threshold, current_price)

        if "export_csv" in request.form:
            start_date = request.form.get("start_date")
            end_date = request.form.get("end_date")
            if start_date and end_date:
                hist_data = fetch_historical_data(symbol, start_date, end_date)
                if not hist_data.empty:
                    output = io.StringIO()
                    hist_data.to_csv(output)
                    output.seek(0)

                    return send_file(
                        io.BytesIO(output.getvalue().encode()),
                        mimetype="text/csv",
                        as_attachment=True,
                        download_name=f"{symbol}_historical.csv"
                    )
                else:
                    error_message = f"No historical data found for {symbol} between {start_date} and {end_date}."

    return render_template("stock.html", symbol=symbol, chart=chart, alert=alert, error_message=error_message, data=data)

@app.route("/watchlist")
def watchlist():
    watchlist = load_json("watchlist.json")
    return render_template("watchlist.html", watchlist=watchlist)

@app.route("/pinned")
def pinned():
    pinned = load_json("pinned.json")
    charts = []
    for symbol in pinned:
        data = fetch_stock_data(symbol, period="1d", interval="1h")
        if not data.empty:
            chart = get_stock_chart(data, symbol, period="1d", chart_type="candlestick")
            charts.append((symbol, chart))
    return render_template("pinned.html", charts=charts)

@app.route("/symbols", methods=["GET", "POST"])
def symbols():
    popular_symbols = ["AAPL", "TSLA", "GOOGL", "MSFT", "AMZN", "META", "NFLX"]
    error_message = None

    if request.method == "POST":
        custom_symbol = request.form.get("custom_symbol", "").upper().strip()
        if custom_symbol:
            test_data = fetch_stock_data(custom_symbol, period="1d", interval="1h")
            if test_data.empty:
                error_message = f"Invalid symbol '{custom_symbol}' or no data available. Please try another symbol."
            else:
                return redirect(url_for("stock", symbol=custom_symbol))

    return render_template("symbols.html", symbols=popular_symbols, error_message=error_message)

if __name__ == "__main__":
    app.run(debug=True)