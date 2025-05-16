import pytz
import datetime
from datetime import datetime as dt


def get_est_date_time(days=0):

    ist_timezone = pytz.timezone('America/New_York')

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


def get_time_string(hour_, minute_):
    return f"{hour_:02}:{minute_:02}"


def get_est_to_local_time_string(hour_, minute_):
    time_str = get_time_string(hour_, minute_)

    date_ = dt.strptime(time_str, '%H:%M')
    local_time = date_ + datetime.timedelta(hours=8, minutes=0)

    return local_time.strftime('%H:%M')


def add_minutes(hour, minute, minutes_to_add):
    if minute+minutes_to_add >= 60:
        return hour+1, minute+minutes_to_add-60
    else:
        return hour, minute + minutes_to_add
