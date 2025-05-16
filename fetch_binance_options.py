import requests
from datetime import datetime, timedelta
import pandas as pd
import os

BASE_URL = "https://eapi.binance.com"

def get_all_option_symbols():
    url = BASE_URL + "/eapi/v1/exchangeInfo"
    try:
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()
        symbols = [s['symbol'] for s in data.get('optionSymbols', []) if s['symbol'].startswith('BTC')]
        return symbols
    except Exception as e:
        print(f"Error fetching option symbols: {e}")
        return []

def filter_symbols_by_expiry(symbols, max_days=6):
    filtered = []
    today = datetime.now()
    max_expiry_date = today + timedelta(days=max_days)

    for sym in symbols:
        parts = sym.split('-')
        if len(parts) < 4:
            continue
        expiry_str = parts[1]
        try:
            expiry_date = datetime.strptime(expiry_str, "%y%m%d")
            if expiry_date <= max_expiry_date:
                filtered.append(sym)
        except Exception as e:
            print(f"Skipping symbol with invalid expiry format {sym}: {e}")
    return filtered

def get_btc_spot_price():
    url = "https://api.binance.com/api/v3/ticker/price"
    params = {"symbol": "BTCUSDT"}
    try:
        response = requests.get(url, params=params)
        response.raise_for_status()
        data = response.json()
        if "price" not in data:
            print(f"'price' not found in response: {data}")
            return None
        return float(data["price"])
    except Exception as e:
        print(f"Error fetching BTC spot price: {e}")
        return None
    
def get_option_mark_price(symbol):
    url = BASE_URL + "/eapi/v1/mark"
    params = {"symbol": symbol}
    try:
        response = requests.get(url, params=params)
        response.raise_for_status()
        data = response.json()
        if isinstance(data, list) and len(data) > 0:
            return float(data[0].get("markPrice", 0))
        else:
            print(f"No mark price found for {symbol}")
            return None
    except Exception as e:
        print(f"Failed to get mark price for {symbol}: {e}")
        return None

def build_option_dataframe(symbols):
    btc_spot = get_btc_spot_price()
    if btc_spot is None:
        print("Could not get BTC spot price, skipping data build.")
        return pd.DataFrame()

    data = []
    current_date = datetime.now().date()

    for symbol in symbols:
        mark_price = get_option_mark_price(symbol)
        if mark_price is not None:
            parts = symbol.split('-')
            expiry_str = parts[1]
            try:
                expiry_date = datetime.strptime(expiry_str, "%y%m%d")
                strike_price = float(parts[2])
                option_type = parts[3]

                data.append({
                    "Date": current_date,
                    "Expiry": expiry_date,
                    "Strike": strike_price,
                    "Option Type": option_type,
                    "Mark Price": mark_price,
                    "BTC Spot Price": btc_spot,
                    "Symbol": symbol
                })
            except Exception as e:
                print(f"Skipping symbol {symbol} due to parsing error: {e}")

    df = pd.DataFrame(data)
    return df


def main():
    all_btc_symbols = get_all_option_symbols()
    btc_symbols_near_expiry = filter_symbols_by_expiry(all_btc_symbols, max_days=6)
    print(f"Found {len(btc_symbols_near_expiry)} BTC options expiring in the next 6 days")

    df_new = build_option_dataframe(btc_symbols_near_expiry)

    csv_file = "btc_options_near_expiry.csv"

    if os.path.exists(csv_file):
        df_existing = pd.read_csv(csv_file, parse_dates=["Date", "Expiry"])
        df_combined = pd.concat([df_existing, df_new], ignore_index=True)
        df_combined.drop_duplicates(subset=["Symbol"], inplace=True)  # optional: avoid repeated entries per hour
    else:
        df_combined = df_new

    df_combined.to_csv(csv_file, index=False)

if __name__ == "__main__":
    main()

