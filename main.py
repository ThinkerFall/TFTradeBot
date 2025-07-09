import matplotlib.pyplot as plt
import requests
import pandas as pd
from datetime import datetime
import ta

# === CONFIGURATION ===
SYMBOL = "BTCUSDT"
INTERVAL = "15m"
LIMIT = 168

# === TELEGRAM ALERTS ===
def send_telegram_alert(message):
    bot_token = "8131661650:AAEOdal3Y1pNCQXWTdjQmn624402adQXof4"  # Replace with your bot token
    chat_id = "7674848022"      # Replace with your chat ID
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": message,
        "parse_mode": "Markdown"
}
    try:
        response = requests.post(url, data=payload)
        if response.status_code!= 200:
            print("❌ Telegram alert failed:", response.text)
    except Exception as e:
        print("❌ Telegram error:", e)

# === FETCH PRICE DATA FROM BINANCE ===
def fetch_binance_data():
    url = "https://twelvedata.com/"
    params = {"symbol": SYMBOL, "interval": INTERVAL, "limit": LIMIT}
    try:
        response = requests.get(url, params=params)
        response.raise_for_status()
        raw_data = response.json()
    except Exception as e:
        print("❌ Error fetching Binance data:", e)
        return pd.DataFrame()

    df = pd.DataFrame(raw_data, columns=[
        "open_time", "open", "high", "low", "close", "volume",
        "close_time", "quote_asset_volume", "num_trades",
        "taker_buy_base", "taker_buy_quote", "ignore"
    ])
    df["timestamp"] = pd.to_datetime(df["open_time"], unit="ms")
    df["close"] = df["close"].astype(float)
    df["high"] = df["high"].astype(float)
    df["low"] = df["low"].astype(float)
    return df[["timestamp", "close", "high", "low"]]

# === CALCULATE INDICATORS ===
def add_indicators(df):
    close = df["close"]

    df["rsi"] = ta.momentum.RSIIndicator(close=close, window=14).rsi()
    df["macd"] = ta.trend.MACD(close=close).macd_diff()

    bb = ta.volatility.BollingerBands(close=close, window=20, window_dev=2)
    df["bb_upper"] = bb.bollinger_hband()
    df["bb_lower"] = bb.bollinger_lband()

    df["ema_12"] = ta.trend.EMAIndicator(close=close, window=12).ema_indicator()
    df["ema_26"] = ta.trend.EMAIndicator(close=close, window=26).ema_indicator()

    stoch_rsi = ta.momentum.StochRSIIndicator(close=close, window=14)
    df["stoch_rsi_k"] = stoch_rsi.stochrsi_k()
    df["stoch_rsi_d"] = stoch_rsi.stochrsi_d()

    df["adx"] = ta.trend.ADXIndicator(high=df["high"], low=df["low"], close=close).adx()

    df["atr"] = ta.volatility.AverageTrueRange(
        high=df["high"], low=df["low"], close=close, window=14
).average_true_range()

    return df

# === CALCULATE TRADE LEVELS ===
def calculate_trade_levels(df):
    latest = df.iloc[-1]
    entry_price = latest["close"]
    atr = latest["atr"]

    stop_loss = entry_price - (1.5 * atr)
    take_profit_1 = entry_price + (1.5 * atr * 2)
    take_profit_2 = entry_price + (1.5 * atr * 3)

    return {
        "entry": round(entry_price, 5),
        "stop_loss": round(stop_loss, 5),
        "take_profit_1": round(take_profit_1, 5),
        "take_profit_2": round(take_profit_2, 5)
}

# === SIGNAL LOGIC ===
def generate_signals(df):
    if df.empty:
        print("⚠️ No data to analyze.")
        return None, [], None, []

    latest = df.iloc[-1]
    signals = []
    sell_flags = []
    buy_flags = []
    trade = None

    if latest["rsi"] < 30 and latest["close"] < latest["bb_lower"] and latest["macd"]> 0:
        signals.append("🚀 BUY (RSI+BB+MACD)")
        buy_flags.append("RSI+BB+MACD")
        trade = calculate_trade_levels(df)

    elif latest["rsi"]> 70 and latest["close"]> latest["bb_upper"] and latest["macd"] < 0:
        signals.append("⚠️ SELL (RSI+BB+MACD)")
        sell_flags.append("RSI+BB+MACD")

    if latest["ema_12"]> latest["ema_26"]:
        signals.append("📈 Bullish EMA crossover")
        buy_flags.append("EMA crossover")
    elif latest["ema_12"] < latest["ema_26"]:
        signals.append("📉 Bearish EMA crossover")
        sell_flags.append("EMA crossover")

    if latest["stoch_rsi_k"] < 20 and latest["stoch_rsi_k"]> latest["stoch_rsi_d"]:
        signals.append("🟢 Stoch RSI Buy")
        buy_flags.append("Stoch RSI")
    elif latest["stoch_rsi_k"]> 80 and latest["stoch_rsi_k"] < latest["stoch_rsi_d"]:
        signals.append("🔴 Stoch RSI Sell")
        sell_flags.append("Stoch RSI")

    if latest["adx"]> 25:
        signals.append("💪 Strong Trend (ADX)")
    else:
        signals.append("😴 Weak Trend (ADX)")

    if latest["macd"] < 0:
        sell_flags.append("MACD")

    return trade, sell_flags, latest, buy_flags

#=== MAIN EXECUTION ===


if __name__ == "__main__":
    df = fetch_binance_data()
    if not df.empty:
        df = add_indicators(df)
        trade, sell_flags, latest, buy_flags = generate_signals(df)

        if latest is not None:
            if trade:
                alert_msg = f"""
📈 BUY Signal for {SYMBOL}
Entry: ${trade['entry']}
Stop Loss: ${trade['stop_loss']}
Take Profit 1: ${trade['take_profit_1']}
Take Profit 2: ${trade['take_profit_2']}
"""
                send_telegram_alert(alert_msg)

        if len(sell_flags)>= 2:
            sell_msg = f"""
🚨 SELL ALERT for {SYMBOL}!
Triggered by: {', '.join(sell_flags)}
Price: ${latest['close']:.2f}
"""
            send_telegram_alert(sell_msg)

        print(f"\n[{latest['timestamp']}] Coin: {SYMBOL} Price: ${latest['close']:.5f}")
        print(f"RSI: {latest['rsi']:.2f} | MACD: {latest['macd']:.4f} | ADX: {latest['adx']:.2f}")
        print(f"Stoch RSI: K={latest['stoch_rsi_k']:.2f}, D={latest['stoch_rsi_d']:.2f}")
        print(f"EMA 12: {latest['ema_12']:.5f} | EMA 26: {latest['ema_26']:.5f}")
        print("Signals:", ", ".join(buy_flags + sell_flags if buy_flags or sell_flags else ["No strong signals"]))# Your Telegram alert logic here
else:
    print("⚠️ Skipping run: No data returned from Binance.")

        

# === MARKET SENTIMENT ===
if latest["ema_12"]> latest["ema_26"] and latest["macd"]> 0:
    trend_direction = "📈 *Bullish*"
elif latest["ema_12"] < latest["ema_26"] and latest["macd"] < 0:
    trend_direction = "📉 *Bearish*"
else:
    trend_direction = "🔄 *Sideways / Unclear*"

trend_strength = "💪 *Strong Trend*" if latest["adx"]> 25 else "😴 *Weak Trend*"


# === SEND CONSOLE OUTPUT TO TELEGRAM ===
summary_msg = f"""
🧾 *Signal Summary for {SYMBOL}*
Time: `{latest['timestamp']}`
Price: `${latest['close']:.5f}`

*RSI:* {latest['rsi']:.2f}
*MACD:* {latest['macd']:.4f}
*ADX:* {latest['adx']:.2f}
*Stoch RSI:* K={latest['stoch_rsi_k']:.2f}, D={latest['stoch_rsi_d']:.2f}
*EMA 12:* {latest['ema_12']:.5f}
*EMA 26:* {latest['ema_26']:.5f}

*Market Direction:* {trend_direction}
*Trend Strength:* {trend_strength}
*Signals:* {', '.join(buy_flags + sell_flags if buy_flags or sell_flags else ['No strong signals'])}
"""
send_telegram_alert(summary_msg)
