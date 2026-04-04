from typing import Optional

from pydantic import BaseModel, Field

from app.models.types import ISIN, WKN


class IndexInfo(BaseModel):
    name: str = Field(..., description="Index name")
    wkn: Optional[WKN] = Field(None, description="WKN")
    member_count: int = Field(..., description="Number of index members per comdirect overview")
    link: str = Field(..., description="URL to the index members page on comdirect")


class IndexMember(BaseModel):
    name: str = Field(..., description="Name of the index member")
    isin: ISIN = Field(..., description="ISIN of the index member")
    link: str = Field(..., description="URL to the instrument page on comdirect")
    asset_class: Optional[str] = Field(None, description="Asset class of the index member")
