from strategy.simple_strategy import place_qqq_option_spread_orders
from data_process.post_market import fetch_and_save_qqq_price
from helper.order import close_all_option_positions
from utility import get_est_to_local_time_string, get_est_date_time
from data_process.pnl import check_pnl
from datetime import time as time_check
import schedule
import time

from log_config import configure_logging
import logging
configure_logging()

market_start_hour, market_start_minute = 9, 30
market_end_hour, market_end_minute = 16, 0

entry_hour, entry_minute = 9, 31
exit_hour, exit_minute = 15, 45

pnl_check_start_hour, pnl_check_start_minute = 9, 35
pnl_check_end_hour, pnl_check_end_minute = 15, 50

post_market_calc_hour, post_market_calc_minute = 16, 25

program_end_hour, program_end_minute = 16, 30


def check_pnl_conditionally():

    pnl_check_start_time = time_check(pnl_check_start_hour, pnl_check_start_minute)
    pnl_check_end_time = time_check(pnl_check_end_hour, pnl_check_end_minute)

    current_est_date_str, current_date_est, current_est_time = get_est_date_time()
    if pnl_check_start_time <= current_est_time <= pnl_check_end_time:
        try:
            logging.info(f"Executing PNL check")
            check_pnl()
        except Exception as e:
            logging.error(f"Error during PNL check at {current_est_time}: {str(e)}")
            raise


def run_scheduled_jobs():
    logging.info("Initializing scheduled jobs")

    entry_time = get_est_to_local_time_string(entry_hour, entry_minute)
    schedule.every().day.at(entry_time).do(place_qqq_option_spread_orders)

    schedule.every(15).seconds.do(check_pnl_conditionally)

    exit_time = get_est_to_local_time_string(exit_hour, exit_minute)
    schedule.every().day.at(exit_time).do(close_all_option_positions)

    post_market_calc_time = get_est_to_local_time_string(post_market_calc_hour, post_market_calc_minute)
    schedule.every().day.at(post_market_calc_time).do(fetch_and_save_qqq_price)

    program_end_time = time_check(program_end_hour, program_end_minute)

    last_log_time = 0
    while True:
        try:
            schedule.run_pending()
            current_est_time = get_est_date_time()[2]

            # Log status every 5 minutes to avoid excessive logging
            current_time = time.time()
            if current_time - last_log_time >= 300:  # 300 seconds = 5 minutes
                logging.debug(f"Scheduler running. Current EST time: {current_est_time}")
                last_log_time = current_time

            if current_est_time >= program_end_time:
                logging.info(f"Reached program end time ({program_end_time}). Exiting.")
                exit()

            time.sleep(1)

        except Exception as e:
            logging.error(f"Error in scheduler loop: {str(e)}")
            raise


if __name__ == "__main__":
    try:
        run_scheduled_jobs()
    except Exception as e:
        logging.critical(f"Fatal error in main program: {str(e)}")
        raise
