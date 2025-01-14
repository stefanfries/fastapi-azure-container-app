from datetime import datetime

# import pandas as pd
from pydantic import BaseModel, Field


class HistoryData(BaseModel):
    name: str
    wkn: str = Field(..., pattern=r"^[A-HJ-NP-Z0-9]{6}$")
    starttime: datetime
    endtime: datetime
    trading_venue: str
    id_notation: str
    currency: str = Field(..., pattern="^EUR|USD|CHF$")


#    data: pd.DataFrame
