import os
from datetime import datetime, timedelta
from alpaca.data.historical import StockHistoricalDataClient
from alpaca.data.requests import StockLatestBarRequest
from alpaca.trading.client import TradingClient
from helper.order import place_order, save_order_ids

from dir_path import base_dirname
from log_config import configure_logging
import logging

from dotenv import load_dotenv

load_dotenv()

configure_logging()

API_KEY = os.getenv("ALP_KEY")
API_SECRET = os.getenv("ALP_SECRET")


def place_qqq_option_spread_orders():
    """
    Implements the QQQ option spread strategies:

    1. Put Spread Strategy: 
       If yest_price < current_price < 1.01*yest_price:
       - Buy put with strike at 0.98*yest_price
       - Sell put with strike at 0.99*yest_price

    2. Call Spread Strategy:
       If 0.99*yest_price < current_price < yest_price:
       - Buy call with strike at 1.02*yest_price
       - Sell call with strike at 1.01*yest_price

    Both with today's expiry

    Returns:
    - dict: Information about the order execution or None if no order placed
    """
    try:
        # Get yesterday's date and file path
        yesterday = datetime.now() - timedelta(days=1)
        yesterday_str = yesterday.strftime("%d%m%Y")
        yesterday_file = os.path.join(base_dirname, "data", "qqq_price", f"{yesterday_str}.txt")

        # Check if yesterday's file exists
        if not os.path.exists(yesterday_file):
            logging.error(f"Yesterday's QQQ price file not found: {yesterday_file}")
            return None

        # Read yesterday's price
        with open(yesterday_file, 'r') as file:
            yesterday_price = float(file.read().strip())

        logging.info(f"Yesterday's QQQ price: ${yesterday_price:.2f}")

        # Get current QQQ price
        data_client = StockHistoricalDataClient(API_KEY, API_SECRET)
        request_params = StockLatestBarRequest(symbol_or_symbols="QQQ")
        latest_bar = data_client.get_stock_latest_bar(request_params)
        current_price = latest_bar["QQQ"].close

        logging.info(f"Current QQQ price: ${current_price:.2f}")

        # Initialize trading client
        trading_client = TradingClient(API_KEY, API_SECRET, paper=True)

        # Get today's date for expiration
        today = datetime.now()
        expiration_date = today.strftime("%Y-%m-%d")

        result = {}

        # Check Put Spread Strategy condition
        if yesterday_price < current_price < (1.01 * yesterday_price):
            logging.info("Put Spread Strategy condition met! Placing options spread order")

            # Calculate strike prices for put spread
            buy_put_strike = round(0.98 * yesterday_price)
            sell_put_strike = round(0.99 * yesterday_price)

            # Create and place the put spread order
            put_result = execute_qqq_put_spread(
                trading_client,
                buy_put_strike,
                sell_put_strike,
                expiration_date,
                quantity=1
            )

            logging.info(f"Put Spread order executed: {put_result}")
            result["put_spread"] = put_result
        else:
            logging.info("Put Spread Strategy condition not met.")

        # Check Call Spread Strategy condition
        if (0.99 * yesterday_price) < current_price < yesterday_price:
            logging.info("Call Spread Strategy condition met! Placing options spread order")

            # Calculate strike prices for call spread
            buy_call_strike = round(1.02 * yesterday_price)
            sell_call_strike = round(1.01 * yesterday_price)

            # Create and place the call spread order
            call_result = execute_qqq_call_spread(
                trading_client,
                buy_call_strike,
                sell_call_strike,
                expiration_date,
                quantity=1
            )

            logging.info(f"Call Spread order executed: {call_result}")
            result["call_spread"] = call_result
        else:
            logging.info("Call Spread Strategy condition not met.")

        # Return results
        if result:
            return result
        else:
            logging.info("No strategy conditions met. No orders placed.")
            return None

    except Exception as e:
        logging.error(f"Error in QQQ option spread strategies: {str(e)}")
        return None


def execute_qqq_put_spread(trading_client, buy_put_strike, sell_put_strike, expiration_date, quantity=1):
    """
    Executes a put spread by:
    1. Buying a put at the lower strike price
    2. Selling a put at the higher strike price
    Both with the same expiration date

    Uses place_order function and saves order IDs to a text file

    Parameters:
    - trading_client: Alpaca TradingClient instance
    - buy_put_strike: Strike price for the put to buy (lower strike)
    - sell_put_strike: Strike price for the put to sell (higher strike)
    - expiration_date: Expiration date in format YYYY-MM-DD
    - quantity: Number of contracts to trade (default 1)

    Returns:
    - dict: Information about the order execution
    """
    # Format expiration date for option symbol (YYMMDD format)
    exp_formatted = datetime.strptime(expiration_date, "%Y-%m-%d").strftime("%y%m%d")

    # Format strike prices for option symbols (multiply by 1000 and format as 8 digits)
    buy_strike_formatted = f"{int(buy_put_strike * 1000):08d}"
    sell_strike_formatted = f"{int(sell_put_strike * 1000):08d}"

    # Create OCC option symbols
    buy_put_symbol = f"QQQ{exp_formatted}P{buy_strike_formatted}"
    sell_put_symbol = f"QQQ{exp_formatted}P{sell_strike_formatted}"

    # Log the option symbols we're using
    logging.info(f"Buying put: {buy_put_symbol}, Selling put: {sell_put_symbol}")

    # Execute the orders using place_order function
    try:
        # Place order to buy put
        buy_order_result = place_order(
            trading_client=trading_client,
            symbol=buy_put_symbol,
            qty=quantity,
            side='buy',
            order_type='market',
            time_in_force='day'
        )

        # Place order to sell put
        sell_order_result = place_order(
            trading_client=trading_client,
            symbol=sell_put_symbol,
            qty=quantity,
            side='sell',
            order_type='market',
            time_in_force='day'
        )

        # Create list of orders to save
        orders = [buy_order_result, sell_order_result]

        # Save order IDs to file
        file_path = save_order_ids(orders, "qqq_put_spread")

        return {
            "buy_put": buy_order_result,
            "sell_put": sell_order_result,
            "strategy": "QQQ Put Spread",
            "buy_strike": buy_put_strike,
            "sell_strike": sell_put_strike,
            "expiration": expiration_date,
            "quantity": quantity,
            "order_file": file_path
        }

    except Exception as e:
        logging.error(f"Error executing put spread orders: {str(e)}")
        raise


def execute_qqq_call_spread(trading_client, buy_call_strike, sell_call_strike, expiration_date, quantity=1):
    """
    Executes a call spread by:
    1. Buying a call at the higher strike price
    2. Selling a call at the lower strike price
    Both with the same expiration date

    Uses place_order function and saves order IDs to a text file

    Parameters:
    - trading_client: Alpaca TradingClient instance
    - buy_call_strike: Strike price for the call to buy (higher strike)
    - sell_call_strike: Strike price for the call to sell (lower strike)
    - expiration_date: Expiration date in format YYYY-MM-DD
    - quantity: Number of contracts to trade (default 1)

    Returns:
    - dict: Information about the order execution
    """
    # Format expiration date for option symbol (YYMMDD format)
    exp_formatted = datetime.strptime(expiration_date, "%Y-%m-%d").strftime("%y%m%d")

    # Format strike prices for option symbols (multiply by 1000 and format as 8 digits)
    buy_strike_formatted = f"{int(buy_call_strike * 1000):08d}"
    sell_strike_formatted = f"{int(sell_call_strike * 1000):08d}"

    # Create OCC option symbols
    buy_call_symbol = f"QQQ{exp_formatted}C{buy_strike_formatted}"
    sell_call_symbol = f"QQQ{exp_formatted}C{sell_strike_formatted}"

    # Log the option symbols we're using
    logging.info(f"Buying call: {buy_call_symbol}, Selling call: {sell_call_symbol}")

    # Execute the orders using place_order function
    try:
        # Place order to buy call
        buy_order_result = place_order(
            trading_client=trading_client,
            symbol=buy_call_symbol,
            qty=quantity,
            side='buy',
            order_type='market',
            time_in_force='day'
        )

        # Place order to sell call
        sell_order_result = place_order(
            trading_client=trading_client,
            symbol=sell_call_symbol,
            qty=quantity,
            side='sell',
            order_type='market',
            time_in_force='day'
        )

        # Create list of orders to save
        orders = [buy_order_result, sell_order_result]

        # Save order IDs to file
        file_path = save_order_ids(orders, "qqq_call_spread")

        return {
            "buy_call": buy_order_result,
            "sell_call": sell_order_result,
            "strategy": "QQQ Call Spread",
            "buy_strike": buy_call_strike,
            "sell_strike": sell_call_strike,
            "expiration": expiration_date,
            "quantity": quantity,
            "order_file": file_path
        }

    except Exception as e:
        logging.error(f"Error executing call spread orders: {str(e)}")
        raise
