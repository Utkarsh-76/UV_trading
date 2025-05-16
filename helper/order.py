import os
from datetime import datetime, timedelta
import json
from alpaca.data.historical import StockHistoricalDataClient
from alpaca.data.requests import StockLatestBarRequest
from alpaca.trading.client import TradingClient
from alpaca.trading.requests import MarketOrderRequest
from alpaca.trading.enums import OrderSide, TimeInForce
from dir_path import base_dirname
from log_config import configure_logging
import logging

from dotenv import load_dotenv

load_dotenv()

configure_logging()

API_KEY = os.getenv("ALP_KEY")
API_SECRET = os.getenv("ALP_SECRET")


def place_order(trading_client, symbol, qty, side, order_type="market", time_in_force="day", limit_price=None):
    """
    Generic function to place an order on Alpaca

    Parameters:
    - trading_client: Alpaca TradingClient instance
    - symbol: The symbol to trade (stock or option)
    - qty: Quantity to trade
    - side: 'buy' or 'sell'
    - order_type: 'market' or 'limit'
    - time_in_force: 'day', 'gtc', etc.
    - limit_price: Price for limit orders

    Returns:
    - dict: Order details including the order ID
    """
    try:
        # Convert string parameters to enums
        order_side = OrderSide.BUY if side.lower() == 'buy' else OrderSide.SELL
        order_tif = TimeInForce.DAY if time_in_force.lower() == 'day' else TimeInForce.GTC

        # Create order request
        order_data = {
            "symbol": symbol,
            "qty": qty,
            "side": order_side,
            "time_in_force": order_tif
        }

        # Add limit price if it's a limit order
        if order_type.lower() == 'limit' and limit_price is not None:
            order_data["limit_price"] = limit_price

        # Create the order request
        order_request = MarketOrderRequest(**order_data)

        # Submit the order
        order_result = trading_client.submit_order(order_data=order_request)

        # Return order details
        return {
            "order_id": order_result.id,
            "client_order_id": order_result.client_order_id,
            "symbol": symbol,
            "qty": qty,
            "side": side,
            "type": order_type,
            "time_in_force": time_in_force,
            "limit_price": limit_price,
            "status": order_result.status,
            "created_at": order_result.created_at.isoformat() if hasattr(order_result, 'created_at') else None,
            "updated_at": order_result.updated_at.isoformat() if hasattr(order_result, 'updated_at') else None
        }

    except Exception as e:
        logging.error(f"Error placing order for {symbol}: {str(e)}")
        raise


def save_order_ids(orders, strategy_name):
    """
    Saves order IDs to a text file with the date as the filename

    Parameters:
    - orders: List of order details
    - strategy_name: Name of the strategy (for file naming)

    Returns:
    - str: Path to the saved file
    """
    try:
        # Create directory if it doesn't exist
        order_dir = os.path.join(base_dirname, "data", "orders")
        os.makedirs(order_dir, exist_ok=True)

        # Create filename with current date
        today = datetime.now().strftime("%d%m%Y")
        filename = os.path.join(order_dir, f"{strategy_name}_{today}.txt")

        # Extract order IDs and details
        order_details = []
        for order in orders:
            order_details.append({
                "order_id": order["order_id"],
                "symbol": order["symbol"],
                "side": order["side"],
                "qty": order["qty"],
                "timestamp": datetime.now().isoformat()
            })

        # Save to file
        with open(filename, 'a') as file:  # Append mode in case we have multiple orders on the same day
            for order in order_details:
                file.write(json.dumps(order) + "\n")

        logging.info(f"Saved {len(orders)} order IDs to {filename}")
        return filename

    except Exception as e:
        logging.error(f"Error saving order IDs: {str(e)}")
        return None


def close_all_option_positions():
    """
    Closes only option positions in the Alpaca account.

    Returns:
    - dict: Information about closed option positions
    """
    try:
        # Initialize trading client
        trading_client = TradingClient(API_KEY, API_SECRET, paper=True)

        # Get all open positions
        positions = trading_client.get_all_positions()

        if not positions:
            logging.info("No open positions to close.")
            return {"status": "success", "message": "No open positions found"}

        # Filter for option positions only (based on symbol format)
        option_positions = [p for p in positions if len(p.symbol) > 6]  # Simple check for options

        if not option_positions:
            logging.info("No open option positions to close.")
            return {"status": "success", "message": "No open option positions found"}

        # Log the number of option positions to close
        logging.info(f"Closing {len(option_positions)} open option positions...")

        results = {
            "status": "success",
            "closed_positions": [],
            "failed_positions": []
        }

        # Close each option position one by one
        for position in option_positions:
            try:
                symbol = position.symbol
                qty = abs(float(position.qty))

                # Determine the side for closing order (opposite of current position)
                side = OrderSide.SELL if float(position.qty) > 0 else OrderSide.BUY

                logging.info(f"Closing option position: {qty} units of {symbol} with {side.name} order")

                # Create order request
                order_request = MarketOrderRequest(
                    symbol=symbol,
                    qty=qty,
                    side=side,
                    time_in_force=TimeInForce.DAY
                )

                # Submit the order
                order_result = trading_client.submit_order(order_data=order_request)

                # Add to successful results
                results["closed_positions"].append({
                    "symbol": symbol,
                    "qty": qty,
                    "side": side.name,
                    "order_id": order_result.id,
                    "order_status": order_result.status
                })

                logging.info(
                    f"Successfully placed order to close {symbol} option position. Order ID: {order_result.id}")

            except Exception as e:
                error_message = f"Failed to close option position for {symbol}: {str(e)}"
                logging.error(error_message)

                # Add to failed results
                results["failed_positions"].append({
                    "symbol": symbol,
                    "qty": qty if 'qty' in locals() else None,
                    "error": str(e)
                })

        # Check if all option positions were successfully closed
        if results["failed_positions"]:
            results["status"] = "partial_success"
            logging.warning(
                f"Closed {len(results['closed_positions'])} option positions, but failed to close {len(results['failed_positions'])} option positions.")
        else:
            logging.info(f"Successfully closed all {len(results['closed_positions'])} option positions.")

        return results

    except Exception as e:
        error_message = f"Error closing option positions: {str(e)}"
        logging.error(error_message)
        return {"status": "error", "message": error_message}