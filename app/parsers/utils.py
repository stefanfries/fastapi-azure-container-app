from calendar import monthrange
from datetime import date, time


def round_time(time_str: str, up: bool = False) -> str:
    time_str_split = time_str.split(".")
    time_str = time_str_split[0]
    if len(time_str_split) > 1:
        microseconds = time_str_split[1]
    else:
        microseconds = "999999" if up else "000000"
    time_str_split = time_str.split(":")
    match len(time_str_split):
        case 3:  # add microseconds
            time_str = time_str + "." + microseconds
        case 2:  # add seconds and microseconds
            time_str = time_str + ":59.999999" if up else time_str
        case 1:  # add minutes, seconds and microseconds
            time_str = time_str + ":59:59.999999" if up else time_str
        case _:
            time_str = time.max.isoformat() if up else time.min.isoformat()
    return time_str


def round_datetime(datetime_str: str, up: bool = False) -> str:
    datetime_split = datetime_str.split("T")
    date_str = datetime_split[0]
    if len(datetime_split) > 1:
        time_str = datetime_split[1]
    else:
        time_str = time.max.isoformat() if up else time.min.isoformat()
    date_str_split = date_str.split("-")
    match len(date_str_split):
        case 3:  # date & time strings are ok, leave them unchanged
            pass
        case 2:  # append first day of month depending on value of up
            year, month = int(date_str_split[0]), int(date_str_split[1])
            _, days_in_month = monthrange(year, month)
            date_str = date_str + "-" + str(days_in_month) if up else date_str + "-01"
            time_str = time.max.isoformat() if up else time.min.isoformat()
        case 1:  # append first or last month and day depending on value of up
            date_str = date_str + "-12-31" if up else date_str + "-01-01"
            time_str = time.max.isoformat() if up else time.min.isoformat()
        case _:
            date_str = date.max.isoformat() if up else date.min.isoformat()
            time_str = time.max.isoformat() if up else time.min.isoformat()
    return date_str + "T" + round_time(time_str, up=up)
