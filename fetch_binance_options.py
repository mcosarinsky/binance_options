import requests
from datetime import datetime, timedelta
import pandas as pd
import os

BASE_URL = "https://eapi.binance.com"

def get_all_option_symbols():
    url = BASE_URL + "/eapi/v1/exchangeInfo"
    response = requests.get(url)
    data = response.json()
    symbols = [s['symbol'] for s in data.get('optionSymbols', []) if s['symbol'].startswith('BTC')]
    return symbols

def filter_symbols_by_expiry(symbols, max_days=6):
    filtered = []
    today = datetime.now()
    max_expiry_date = today + timedelta(days=max_days)

    for sym in symbols:
        parts = sym.split('-')
        if len(parts) < 4:
            continue
        expiry_str = parts[1]
        expiry_date = datetime.strptime(expiry_str, "%y%m%d")
        if expiry_date <= max_expiry_date:
            filtered.append(sym)
    return filtered

def get_btc_spot_price():
    url = "https://api.binance.com/api/v3/ticker/price"
    params = {"symbol": "BTCUSDT"}
    response = requests.get(url, params=params)
    data = response.json()
    return float(data["price"])
    
def get_option_mark_price(symbol):
    url = BASE_URL + "/eapi/v1/mark"
    params = {"symbol": symbol}
    response = requests.get(url, params=params)
    if response.status_code == 200:
        data = response.json()
        if isinstance(data, list) and len(data) > 0:
            return float(data[0].get("markPrice", 0))
        else:
            print(f"No mark price found for {symbol}")
            return None
    else:
        print(f"Failed to get mark price for {symbol}: {response.text}")
        return None

def build_option_dataframe(symbols):
    btc_spot = get_btc_spot_price()
    data = []
    current_date = datetime.now().date()

    for symbol in symbols:
        mark_price = get_option_mark_price(symbol)
        if mark_price is not None:
            parts = symbol.split('-')
            expiry_str = parts[1]
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
