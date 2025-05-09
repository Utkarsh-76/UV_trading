import pytz
import datetime
from datetime import datetime as dt


def get_ist_date_time(days=0):

    ist_timezone = pytz.timezone('Asia/Kolkata')

    now_utc = datetime.datetime.now(pytz.utc)

    now_ist = now_utc.astimezone(ist_timezone)

    updated_ist = now_ist + datetime.timedelta(days=days)

    time_ist = updated_ist.time()

    date_ist = updated_ist.date()

    date_ist_str = str(date_ist).replace('-', '')

    return date_ist_str, date_ist, time_ist


def calculate_expiry_date(date_ist):

    next_same_weekday = date_ist + datetime.timedelta(days=7)

    if next_same_weekday.month != date_ist.month:
        return date_ist.strftime('%y%b').upper()
    elif date_ist.month == 12:
        return date_ist.strftime('%yD%d')
    else:
        return date_ist.strftime('%y%-m%d')


def check_month_end(date_ist):

    next_same_weekday = date_ist + datetime.timedelta(days=7)

    if next_same_weekday.month != date_ist.month:
        return True
    else:
        return False


def get_index_by_day(date_ist, index_no=1):
    weekday = date_ist.weekday()
    if weekday == 1:
        if index_no == 1:
            return {
                "exchange": "BSE",
                "name": "SENSEX",
                "fno_exchange": "BFO",
                "ohlc_symbol": "SENSEX",
                "ticker": 100,
                "lot_size": 20,
                "no_of_lots": 7,
                "secondary_index_days_till_expiry": 2
            }
        else:
            return {
                "exchange": "BSE",
                "name": "BANKEX",
                "fno_exchange": "BFO",
                "ohlc_symbol": "BANKEX",
                "ticker": 100,
                "lot_size": 30,
                "no_of_lots": 8,
            }
    elif weekday == 3:
        if index_no == 1:
            return {
                "exchange": "NSE",
                "name": "NIFTY",
                "fno_exchange": "NFO",
                "ohlc_symbol": "NIFTY 50",
                "ticker": 50,
                "lot_size": 75,
                "no_of_lots": 6,
                "secondary_index_days_till_expiry": 5
            }
        else:
            return {
                "exchange": "NSE",
                "name": "BANKNIFTY",
                "fno_exchange": "NFO",
                "ohlc_symbol": "NIFTY BANK",
                "ticker": 100,
                "lot_size": 30,
                "no_of_lots": 8
            }
    # elif weekday == 4:
    #     return {
    #         "exchange": "NSE",
    #         "name": "FINNIFTY",
    #         "fno_exchange": "NFO",
    #         "ohlc_symbol": "NIFTY FIN SERVICE",
    #         "ticker": 50,
    #         "lot_size": 25}
    else:
        return None


def get_time_string(hour_, minute_):
    return f"{hour_:02}:{minute_:02}"


def get_ist_to_dubai_time_string(hour_, minute_):
    time_str = get_time_string(hour_, minute_)

    date_ = dt.strptime(time_str, '%H:%M')
    dubai_time = date_ - datetime.timedelta(hours=5, minutes=30)

    return dubai_time.strftime('%H:%M')


def add_minutes(hour, minute, minutes_to_add):
    if minute+minutes_to_add >= 60:
        return hour+1, minute+minutes_to_add-60
    else:
        return hour, minute + minutes_to_add



# print(get_ist_date_time())