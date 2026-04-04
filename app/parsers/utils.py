"""
Shared parser utility functions.

Provides validation helpers for id_notation values and date/time rounding
utilities used by the history parser when normalising partial date strings.

Functions:
    check_valid_id_notation: Validate an id_notation against an instrument's known venues.
    get_id_notations_dict:   Build a merged id_notations dict from an instrument.
    get_trading_venues_dict: Build a reverse id_notation → venue mapping.
    get_id_notation:         Look up the id_notation for a given trading venue.
    get_trading_venue:       Look up the trading venue for a given id_notation.
    round_time:              Round a partial time string up or down to a full time string.
    round_datetime:          Round a partial ISO-8601 datetime string up or down.
"""

from calendar import monthrange
from datetime import date, time

from fastapi import HTTPException, status

from app.logging_config import logger
from app.models.instruments import Instrument


def check_valid_id_notation(instrument_data, id_notation) -> None:
    """
    Validates the given id_notation against the instrument_data.
    This function checks if the provided id_notation is present in either
    the id_notations_life_trading or id_notations_exchange_trading values
    of the instrument_data. If the id_notation is not found in either, an HTTPException
    is raised with a 400 status code.
    Args:
        instrument_data: An object containing id_notations_life_trading and id_notations_exchange_trading.
        id_notation: The id_notation to be validated.
    Raises:
        HTTPException: If the id_notation is not valid for the given instrument_data.
    """

    if (
        id_notation in instrument_data.id_notations_life_trading.values()
        or id_notation in instrument_data.id_notations_exchange_trading.values()
    ):
        return None
    else:
        logger.error(
            "Invalid id_notation: %s for instrument %s",
            id_notation,
            instrument_data.wkn,
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid id_notation {id_notation} for instrument {instrument_data.name}",
        )


def get_id_notations_dict(instrument_data: Instrument) -> dict:
    """
    Get the id_notations dictionary for the given instrument_data instance.
    Args:
        instrument_data (Instrument): An instance of Instrument containing id notations.
    Returns:
        dict: A dictionary containing all id_notations for the given instrument_data.
    """
    return {
        **(instrument_data.id_notations_life_trading or {}),
        **(instrument_data.id_notations_exchange_trading or {}),
    }


def get_trading_venues_dict(instrument_data: Instrument) -> dict:
    """
    Get the trading venues dictionary for the given instrument_data instance.
    Args:
        instrument_data (Instrument): An instance of Instrument containing trading venues.
    Returns:
        dict: A dictionary containing all trading venues for the given instrument_data.
    """
    id_notatations_dict = get_id_notations_dict(instrument_data)
    trading_venues_dict = {v: k for k, v in id_notatations_dict.items()}
    return trading_venues_dict


def get_id_notation(instrument_data: Instrument, trading_venue: str) -> str:
    """
    Get the id_notation for the given trading_venue in the provided Instrument instance.
    Args:
        instrument_data (Instrument): An instance of Instrument containing id notations.
        trading_venue (str): The trading venue to get the id_notation for.
    Returns:
        str: The id_notation of the given trading_venue in the instrument_data.
    """
    id_notations_dict = get_id_notations_dict(instrument_data)

    if trading_venue not in id_notations_dict:
        logger.error(
            "Invalid trading_venue: %s for instrument %s", trading_venue, instrument_data.wkn
        )
        raise ValueError(
            f"Invalid trading_venue {trading_venue} for instrument {instrument_data.wkn}"
        )
    return id_notations_dict.get(trading_venue, "")


def get_trading_venue(instrument_data: Instrument, id_notation: str) -> str:
    """
    Get the trading venue for the given id_notation in the provided Instrument instance.
    Args:
        instrument_data (Instrument): An instance of Instrument containing id notations.
        id_notation (str): The id notation to get the trading venue for.
    Returns:
        str: The trading venue of the given id_notation in the instrument_data.
    """
    trading_venues_dict = get_trading_venues_dict(instrument_data)
    if id_notation not in trading_venues_dict:
        logger.error(
            "Invalid id_notation: %s for instrument %s", id_notation, instrument_data.wkn
        )
        raise ValueError(
            f"Invalid id_notation {id_notation} for instrument {instrument_data.wkn}"
        )
    return trading_venues_dict.get(id_notation, "")


def round_time(time_str: str, up: bool = False) -> str:
    """Round a partial time string to a full ``HH:MM:SS.ffffff`` time string.

    Handles strings with 1, 2, or 3 colon-separated components and an optional
    microseconds fraction.  When *up* is ``True`` the string is rounded toward
    the end of the implied period; when ``False`` it is rounded toward the start.

    Args:
        time_str: Partial or full time string, e.g. ``"14"``, ``"14:30"``,
                  ``"14:30:00"`` or ``"14:30:00.123456"``.
        up:       If ``True``, round toward the latest possible time in the
                  period; if ``False``, round toward the earliest. Defaults to
                  ``False``.

    Returns:
        A fully-qualified time string including microseconds.
    """
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
    """Round a partial ISO-8601 datetime string to a full ``YYYY-MM-DDTHH:MM:SS.ffffff`` string.

    Handles date strings with 1 (year), 2 (year-month), or 3 (year-month-day)
    dash-separated components, optionally followed by a ``T``-separated time
    component.  When *up* is ``True`` the string is rounded toward the end of
    the implied period (e.g. last day of the month, 23:59:59); when ``False``
    toward the start (e.g. first day of the month, 00:00:00).

    Args:
        datetime_str: Partial or full ISO-8601 datetime string, e.g. ``"2024"``,
                      ``"2024-03"``, ``"2024-03-15"`` or ``"2024-03-15T14:30"``.
        up:           If ``True``, round toward the end of the period; if
                      ``False``, toward the start. Defaults to ``False``.

    Returns:
        A fully-qualified ISO-8601 datetime string including microseconds.
    """
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
