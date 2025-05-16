import os
from datetime import datetime
from alpaca.data.historical import StockHistoricalDataClient
from alpaca.data.requests import StockLatestBarRequest
from dir_path import base_dirname
from log_config import configure_logging
import logging

from dotenv import load_dotenv
load_dotenv()

configure_logging()


API_KEY = os.getenv("ALP_KEY")
API_SECRET = os.getenv("ALP_SECRET")


def fetch_and_save_qqq_price():
    """
    Fetches the current price of QQQ ETF using Alpaca's Market Data API
    and saves it to a text file with the filename in format DDMMYYYY.txt

    Returns:
    - current_price: The latest price of QQQ
    """

    now = datetime.now()
    date_str = now.strftime("%d%m%Y")
    filename = os.path.join(base_dirname, "data", "qqq_price", f"{date_str}.txt")

    # Initialize the Stock Historical Data client
    client = StockHistoricalDataClient(API_KEY, API_SECRET)

    # Method 1: Get the latest bar data for QQQ
    request_params = StockLatestBarRequest(symbol_or_symbols="QQQ")
    latest_bar = client.get_stock_latest_bar(request_params)

    # Extract the closing price
    current_price = str(latest_bar["QQQ"].close)

    # Save to file
    with open(filename, 'w') as file:
        file.write(current_price)

    logging.info(f"Successfully saved QQQ price to {filename}")
    return current_price, filename
