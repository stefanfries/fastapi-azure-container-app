"""Tests for scripts.backfill_mapping_overrides."""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest

from scripts.backfill_mapping_overrides import (
    INDEX_MEMBER_NAME_OVERRIDES,
    INSTRUMENT_SYMBOL_OVERRIDES,
    apply_backfill,
)


@pytest.mark.asyncio
async def test_backfill_overrides_include_bunge_ch_isin() -> None:
    assert INSTRUMENT_SYMBOL_OVERRIDES["CH1300646267"] == "BG"
    assert INDEX_MEMBER_NAME_OVERRIDES["CH1300646267"] == "Bunge Global S.A."


@pytest.mark.asyncio
async def test_apply_backfill_updates_symbol_and_refreshes_cache() -> None:
    instruments = MagicMock()
    index_members = MagicMock()
    instruments.update_many = AsyncMock(return_value=MagicMock(modified_count=1))
    index_members.update_many = AsyncMock(return_value=MagicMock(modified_count=2))

    instrument_updates, member_updates = await apply_backfill(instruments, index_members)

    assert instrument_updates == len(INSTRUMENT_SYMBOL_OVERRIDES)
    assert member_updates == 2 * len(INDEX_MEMBER_NAME_OVERRIDES)

    # First instrument update call must enforce BG for CH1300646267 and refresh cache timestamp.
    call_args = instruments.update_many.await_args_list[0].args
    assert call_args[0] == {"isin": "CH1300646267"}
    update_doc = call_args[1]
    assert update_doc["$set"]["global_identifiers.symbol_yfinance"] == "BG"
    assert isinstance(update_doc["$set"]["cached_at"], datetime)
    assert update_doc["$set"]["cached_at"].tzinfo == UTC

    # First index member update call must normalize Bunge name by CH ISIN.
    member_call = index_members.update_many.await_args_list[0]
    assert member_call.args[0] == {"members.isin": "CH1300646267"}
    assert member_call.args[1]["$set"]["members.$[m].name"] == "Bunge Global S.A."
    assert member_call.kwargs["array_filters"] == [{"m.isin": "CH1300646267"}]
