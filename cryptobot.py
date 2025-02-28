import logging
import requests
import pandas as pd
import numpy as np
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackContext

# Telegram bot tokenınızı buraya ekleyin
TOKEN = "8006669173:AAGSDqbGPWBolRT6L5mQ77Dg0bpGx43mfNk"

# Binance API üzerinden veri alma fonksiyonu
def get_binance_data(symbol='BTCUSDT', interval='1h', limit=100):
    url = f'https://api.binance.com/api/v3/klines?symbol={symbol}&interval={interval}&limit={limit}'
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        data = response.json()
        if not isinstance(data, list):
            logging.error("Unexpected response format from Binance API")
            return None
    except requests.exceptions.RequestException as e:
        logging.error(f"Binance API request failed: {e}")
        return None

    df = pd.DataFrame(data, columns=[
        'timestamp', 'open', 'high', 'low', 'close', 'volume', 'close_time',
        'quote_asset_volume', 'trades', 'taker_base_vol', 'taker_quote_vol', 'ignore'
    ])
    df = df[['timestamp', 'open', 'high', 'low', 'close', 'volume']]
    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
    df.set_index('timestamp', inplace=True)
    df = df.astype(float)
    return df

# Hareketli ortalamalara göre al-sat sinyali üreten fonksiyon
def moving_average_strategy(df, short_window=5, long_window=20):
    if df is None or df.empty:
        return None
    df = df.copy()
    df['SMA_short'] = df['close'].rolling(window=short_window).mean()
    df['SMA_long'] = df['close'].rolling(window=long_window).mean()
    df['Signal'] = np.where(df['SMA_short'] > df['SMA_long'], 'Buy', 'Sell')
    return df[['close', 'SMA_short', 'SMA_long', 'Signal']]

# Telegram botu başlatma komutu
async def start(update: Update, context: CallbackContext) -> None:
    await update.message.reply_text("Merhaba! Binance verilerini analiz etmek için /analyze komutunu kullanın.")


# Telegram botu için analiz komutu
async def analyze(update: Update, context: CallbackContext) -> None:
    symbols = ['BTCUSDT', 'BNBUSDT', 'ETHUSDT', 'DOGEUSDT','SOLUSDT']

    for symbol in symbols:
        df = get_binance_data(symbol)
        if df is None:
            await update.message.reply_text(f"{symbol}: Veri alınamadı ❌")
            continue

        analysis = moving_average_strategy(df)
        if analysis is None:
            await update.message.reply_text(f"{symbol}: Yetersiz veri ❌")
            continue

        last_row = analysis.iloc[-1]
        message = (
            f"📊 Symbol: {symbol}\n"
            f"📈 Close Price: {last_row['close']:.2f}\n"
            f"📉 Short MA: {last_row['SMA_short']:.4f}\n"
            f"📊 Long MA: {last_row['SMA_long']:.4f}\n"
            f"🚦 Signal: {last_row['Signal']}\n"
        )
        await update.message.reply_text(message)


# Telegram botunu çalıştırma
if __name__ == "__main__":
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("analyze", analyze))
    app.run_polling()
