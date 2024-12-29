from enum import Enum
from typing import List, Optional

from pydantic import BaseModel


class InstrumentType(Enum):
    AKTIEN = "Aktie"
    ANLEIHEN = "Anleihe"
    ETFS = "ETF"
    FONDS = "Fonds"
    OPTIONSSCHEINE = "Optionsschein"
    ZERTIFIKATE = "Zertifikat"
    ROHSTOFFE = "Rohstoff"
    INDIZES = "Index"
    WAEHRUNGEN = "Währung"


class NotationType(Enum):
    LIFE_TRADING = "LiveTrading"
    EXCH_TRADING = "Börse"


class InstrumentId(BaseModel):
    name: str
    wkn: str
    isin: str
    symbol: Optional[str] = None


class NotationInfo(BaseModel):
    notation_name: str
    notation_id: str
    notation_type: str
    notation_link: str


class NotationsList(BaseModel):
    notations_list: List[NotationInfo]


class InstrumentBaseData(BaseModel):
    instrument_id: InstrumentId
    instrument_type: InstrumentType
    instrument_notations: NotationsList
