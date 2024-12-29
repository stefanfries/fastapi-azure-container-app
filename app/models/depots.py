"""
Module: depots
This module defines the data models related to depots using Pydantic BaseModel.
It includes the following classes:
- InstrumentBought: Represents an instrument that has been bought.
- Depot: Represents a depot containing a list of instruments, cash, and timestamps for creation and modification.
Classes:
    InstrumentBought: A Pydantic model representing an instrument that has been bought.
        Attributes:
            instrument (InstrumentId): The ID of the bought instrument.
    Depot: A Pydantic model representing a depot.
        Attributes:
            id (str): The unique identifier of the depot.
            name (str): The name of the depot.
            items (List[InstrumentId]): A list of instrument IDs contained in the depot.
            cash (float): The amount of cash available in the depot.
            created_at (datetime): The timestamp when the depot was created.
            changed_at (datetime): The timestamp when the depot was last modified.
"""

from datetime import datetime
from typing import List

from pydantic import BaseModel

from app.models.instruments import InstrumentId


class InstrumentBought(BaseModel):
    """
    Represents an instrument that has been bought.
    Attributes:
        instrument (InstrumentId): The ID of the instrument that has been purchased.
    """

    instrument: InstrumentId


class Depot(BaseModel):
    """
    Represents a depot containing financial instruments and cash.
    Attributes:
        id (str): Unique identifier for the depot.
        name (str): Name of the depot.
        items (List[InstrumentId]): List of financial instruments in the depot.
        cash (float): Amount of cash available in the depot.
        created_at (datetime): Timestamp when the depot was created.
        changed_at (datetime): Timestamp when the depot was last modified.
    """

    id: str
    name: str
    items: List[InstrumentId]
    cash: float
    created_at: datetime
    changed_at: datetime
