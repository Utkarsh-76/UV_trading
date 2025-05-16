import os
from datetime import datetime
import json
from alpaca.data.historical import StockHistoricalDataClient
from alpaca.data.requests import StockLatestBarRequest, StockLatestQuoteRequest
from alpaca.trading.client import TradingClient
from helper.order import close_all_option_positions
from dir_path import base_dirname
from log_config import configure_logging
import logging

from dotenv import load_dotenv

load_dotenv()

configure_logging()

API_KEY = os.getenv("ALP_KEY")
API_SECRET = os.getenv("ALP_SECRET")


def load_order_history(strategy_name=None, date=None):
    """
    Loads order history from saved files

    Parameters:
    - strategy_name: Optional filter by strategy name
    - date: Optional specific date to load (format: DDMMYYYY string or datetime object)

    Returns:
    - list: Order details
    """
    orders = []

    try:
        # Set up the directory
        order_dir = os.path.join(base_dirname, "data", "orders")

        # Convert date to string if it's a datetime object
        if isinstance(date, datetime):
            date = date.strftime("%d%m%Y")

        # Get list of files to process
        if strategy_name and date:
            # Specific strategy and date
            files = [os.path.join(order_dir, f"{strategy_name}_{date}.txt")]
        elif strategy_name:
            # All files for a specific strategy
            files = [f for f in os.listdir(order_dir) if f.startswith(f"{strategy_name}_")]
            files = [os.path.join(order_dir, f) for f in files]
        elif date:
            # All strategies for a specific date
            files = [f for f in os.listdir(order_dir) if f.endswith(f"_{date}.txt")]
            files = [os.path.join(order_dir, f) for f in files]
        else:
            # All files
            files = [os.path.join(order_dir, f) for f in os.listdir(order_dir) if f.endswith(".txt")]

        # Process each file
        for file_path in files:
            if os.path.exists(file_path):
                with open(file_path, 'r') as file:
                    for line in file:
                        line = line.strip()
                        if line:
                            try:
                                order = json.loads(line)
                                orders.append(order)
                            except json.JSONDecodeError:
                                logging.warning(f"Could not parse line: {line}")

        return orders

    except Exception as e:
        logging.error(f"Error loading order history: {str(e)}")
        return []


def get_current_option_prices(symbols):
    """
    Gets current market prices for option symbols

    Parameters:
    - symbols: List of option symbols

    Returns:
    - dict: Symbol to price mapping
    """
    prices = {}

    try:
        # Initialize client for market data
        data_client = StockHistoricalDataClient(API_KEY, API_SECRET)

        # Get latest quotes for all symbols
        request_params = StockLatestQuoteRequest(symbol_or_symbols=symbols)

        try:
            latest_quotes = data_client.get_stock_latest_quote(request_params)

            # Extract midpoint prices from quotes
            for symbol in symbols:
                if symbol in latest_quotes:
                    # Calculate midpoint of bid and ask
                    bid = latest_quotes[symbol].bid_price
                    ask = latest_quotes[symbol].ask_price

                    # Use midpoint if both bid and ask are available
                    if bid and ask:
                        prices[symbol] = (bid + ask) / 2
                    # Otherwise use whichever is available
                    elif bid:
                        prices[symbol] = bid
                    elif ask:
                        prices[symbol] = ask
        except Exception as e:
            logging.warning(f"Error getting quotes: {str(e)}")

            # Fallback to getting latest trades
            for symbol in symbols:
                try:
                    # Try to get latest bar for individual symbol
                    bar_params = StockLatestBarRequest(symbol_or_symbols=symbol)
                    latest_bar = data_client.get_stock_latest_bar(bar_params)

                    if symbol in latest_bar:
                        prices[symbol] = latest_bar[symbol].close
                except Exception as bar_error:
                    logging.warning(f"Could not get price for {symbol}: {str(bar_error)}")

        return prices

    except Exception as e:
        logging.error(f"Error getting current option prices: {str(e)}")
        return {}


def calculate_option_pnl(positions, today_orders=None):
    """
    Calculates current P&L for option positions

    Parameters:
    - positions: List of current option positions
    - today_orders: Optional list of today's orders with premium information

    Returns:
    - dict: P&L information for each position and the total P&L
    """
    try:
        # Get symbols from positions
        symbols = [p.symbol for p in positions]

        if not symbols:
            return {"total_pnl": 0, "positions": {}}

        # Get current prices
        current_prices = get_current_option_prices(symbols)

        # Initialize results
        pnl_info = {
            "total_pnl": 0,
            "positions": {},
            "premiums": {}  # To store premium information if available
        }

        # If today's orders are provided, extract premium information
        order_premium_map = {}

        if today_orders:
            # Calculate total premium for the strategy
            premium_paid = 0
            premium_received = 0

            for order in today_orders:
                if order.get("side") == "buy":
                    # For simplicity, we'll assume the fills happened at the limit price
                    # In a production system, you'd use the actual fill price
                    premium_paid += order.get("limit_price", 0) * order.get("qty",
                                                                            0) * 100  # * 100 for option contracts
                elif order.get("side") == "sell":
                    premium_received += order.get("limit_price", 0) * order.get("qty", 0) * 100

                # Map order symbol to premium
                order_premium_map[order.get("symbol")] = order.get("limit_price", 0) * 100

            # Net premium is what you paid minus what you received
            net_premium = premium_paid - premium_received

            pnl_info["strategy_premium"] = {
                "paid": premium_paid,
                "received": premium_received,
                "net": net_premium
            }

            # Stop-loss is at -2x the premium (a negative number)
            pnl_info["stop_loss"] = -2 * net_premium

        # Calculate P&L for each position
        for position in positions:
            symbol = position.symbol
            qty = float(position.qty)
            avg_entry_price = float(position.avg_entry_price) if hasattr(position, 'avg_entry_price') else 0

            # If we have current price for this symbol
            if symbol in current_prices:
                current_price = current_prices[symbol]

                # Calculate P&L based on position direction
                if qty > 0:  # Long position
                    pnl = (current_price - avg_entry_price) * qty * 100  # * 100 for option contracts
                else:  # Short position
                    pnl = (avg_entry_price - current_price) * abs(qty) * 100

                # Store position details
                pnl_info["positions"][symbol] = {
                    "symbol": symbol,
                    "qty": qty,
                    "avg_entry_price": avg_entry_price,
                    "current_price": current_price,
                    "pnl": pnl,
                    "pnl_percentage": (pnl / (avg_entry_price * abs(qty) * 100)) * 100 if avg_entry_price > 0 else 0
                }

                # Add premium information if available
                if symbol in order_premium_map:
                    pnl_info["positions"][symbol]["premium"] = order_premium_map[symbol]

                # Add to total P&L
                pnl_info["total_pnl"] += pnl

        return pnl_info

    except Exception as e:
        logging.error(f"Error calculating option P&L: {str(e)}")
        return {"total_pnl": 0, "positions": {}, "error": str(e)}


def check_and_close_losing_positions():
    """
    Checks if current loss exceeds 2x the premium paid and closes positions if it does.
    This is a stop-loss function that triggers only on significant losses.

    Returns:
    - dict: Results of the check and any actions taken
    """
    try:
        # Initialize trading client
        trading_client = TradingClient(API_KEY, API_SECRET, paper=True)

        # Get today's date
        today = datetime.now().strftime("%d%m%Y")

        # Get all open option positions
        all_positions = trading_client.get_all_positions()
        option_positions = [p for p in all_positions if len(p.symbol) > 6]  # Simple filter for options

        if not option_positions:
            logging.info("No open option positions found")
            return {"status": "info", "message": "No open option positions"}

        # Get today's orders for premium information
        today_orders = load_order_history(date=today)

        # Calculate current P&L
        pnl_info = calculate_option_pnl(option_positions, today_orders)

        logging.info(f"Current total P&L: ${pnl_info['total_pnl']:.2f}")

        # Check if we have stop-loss information
        if "stop_loss" in pnl_info:
            stop_loss = pnl_info["stop_loss"]
            current_pnl = pnl_info["total_pnl"]

            logging.info(f"Stop-loss level (2x premium): ${stop_loss:.2f}")

            # If P&L is below stop-loss (more negative), close all positions
            if current_pnl <= stop_loss:
                logging.info(f"Stop-loss triggered! Current P&L: ${current_pnl:.2f} <= Stop-loss: ${stop_loss:.2f}")
                logging.info("Closing all option positions to limit losses...")

                # Close all option positions
                close_result = close_all_option_positions()

                return {
                    "status": "stop_loss_triggered",
                    "message": "Stop-loss triggered, positions closed",
                    "pnl_info": pnl_info,
                    "close_result": close_result
                }
            else:
                logging.info(
                    f"Current loss not at stop-loss level. Current P&L: ${current_pnl:.2f} > Stop-loss: ${stop_loss:.2f}")
                return {
                    "status": "info",
                    "message": "Stop-loss not triggered",
                    "pnl_info": pnl_info
                }
        else:
            # If we don't have premium information, just report the current P&L
            logging.info("Premium information not available, cannot determine stop-loss level")
            return {
                "status": "info",
                "message": "Premium information not available",
                "pnl_info": pnl_info
            }

    except Exception as e:
        error_message = f"Error checking stop-loss and closing positions: {str(e)}"
        logging.error(error_message)
        return {"status": "error", "message": error_message}


if __name__ == "__main__":
    # Test the stop-loss function
    result = check_and_close_losing_positions()

    print(f"Status: {result['status']}")
    print(f"Message: {result.get('message', 'No message')}")

    if 'pnl_info' in result:
        print(f"Current P&L: ${result['pnl_info']['total_pnl']:.2f}")

        if 'stop_loss' in result['pnl_info']:
            print(f"Stop-loss level: ${result['pnl_info']['stop_loss']:.2f}")

    if 'close_result' in result:
        close_result = result['close_result']
        print(f"Closed {len(close_result.get('closed_positions', []))} positions")