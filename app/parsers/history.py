# import re
from datetime import datetime

# from app.logging_config import logger
from app.models.history import HistoryData

# import pandas as pd


# from app.scrapers.scrape_url import fetch_one

# from urllib.parse import parse_qs, urlparse

# from bs4 import BeautifulSoup


async def parse_history_data(instrument_id: str) -> HistoryData:

    print(f"parse_history_data: {instrument_id}")
    return HistoryData(
        name="Apple",
        wkn="123456",
        starttime=datetime.now(),
        endtime=datetime.now(),
        trading_venue="123456",
        id_notation="123456",
        currency="USD",
        # data=pd.DataFrame(),
    )
