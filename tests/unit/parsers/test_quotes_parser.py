"""Unit tests for app.parsers.quotes — asset-class guard, price extraction, timestamp."""

import textwrap
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from bs4 import BeautifulSoup
from fastapi import HTTPException

from app.models.instruments import AssetClass


def _instrument(asset_class: AssetClass) -> MagicMock:
    """Return a minimal Instrument stub with the given asset class."""
    inst = MagicMock()
    inst.asset_class = asset_class
    inst.wkn = "846900"
    inst.isin = None
    inst.default_id_notation = "12345"
    inst.preferred_id_notation_exchange_trading = "12345"
    inst.preferred_id_notation_life_trading = "12345"
    inst.id_notations_life_trading = None
    inst.id_notations_exchange_trading = None
    return inst


def _table(rows: list[tuple[str, str]]) -> BeautifulSoup:
    """Build a minimal Kursdaten BeautifulSoup table from (label, value) pairs."""
    row_html = "\n".join(f"<tr><th>{label}</th><td>{value}</td></tr>" for label, value in rows)
    return BeautifulSoup(
        f"<table>{row_html}</table>",
        "html.parser",
    ).find("table")


def _table_with_span(rows: list[tuple[str, str]]) -> BeautifulSoup:
    """Build a Kursdaten table where values use the realtime-indicator span layout."""
    row_html = "\n".join(
        f"<tr><th>{label}</th>"
        f'<td><div class="realtime-indicator">'
        f'<span class="realtime-indicator--value">{value}</span>'
        f"</div></td></tr>"
        for label, value in rows
    )
    return BeautifulSoup(
        f"<table>{row_html}</table>",
        "html.parser",
    ).find("table")


# ---------------------------------------------------------------------------
# _extract_table_price
# ---------------------------------------------------------------------------


class TestExtractTablePrice:
    def test_plain_td_integer(self):
        from app.parsers.quotes import _extract_table_price

        table = _table([("Geld", "8,93")])
        assert _extract_table_price(table, "Geld") == pytest.approx(8.93)

    def test_plain_td_thousands_separator(self):
        from app.parsers.quotes import _extract_table_price

        table = _table([("Geld", "1.234,56")])
        assert _extract_table_price(table, "Geld") == pytest.approx(1234.56)

    def test_realtime_span_layout(self):
        from app.parsers.quotes import _extract_table_price

        table = _table_with_span([("Geld", "112,89")])
        assert _extract_table_price(table, "Geld") == pytest.approx(112.89)

    def test_returns_none_for_missing_label(self):
        from app.parsers.quotes import _extract_table_price

        table = _table([("Brief", "9,01")])
        assert _extract_table_price(table, "Geld") is None

    def test_returns_none_for_double_dash(self):
        from app.parsers.quotes import _extract_table_price

        table = _table([("Geld", "--")])
        assert _extract_table_price(table, "Geld") is None

    def test_fonds_ruecknahmepreis(self):
        from app.parsers.quotes import _extract_table_price

        table = _table([("Rücknahmepreis", "92,40"), ("Ausgabepreis", "97,02")])
        assert _extract_table_price(table, "Rücknahmepreis") == pytest.approx(92.40)
        assert _extract_table_price(table, "Ausgabepreis") == pytest.approx(97.02)


# ---------------------------------------------------------------------------
# _extract_timestamp
# ---------------------------------------------------------------------------


class TestExtractTimestamp:
    def test_single_zeit_row(self):
        from datetime import datetime

        from app.parsers.quotes import _extract_timestamp

        table = _table([("Zeit", "05.05.26 22:02")])
        assert _extract_timestamp(table) == datetime(2026, 5, 5, 22, 2)

    def test_two_zeit_rows_uses_one_after_brief(self):
        """ETF layout: first Zeit is for Aktuell, second is for Geld/Brief."""
        from datetime import datetime

        from app.parsers.quotes import _extract_timestamp

        html = textwrap.dedent("""
            <table>
              <tr><th>Aktuell</th><td>8,97</td></tr>
              <tr><th>Zeit</th><td>05.05.26 21:00</td></tr>
              <tr><th>Geld</th><td>8,93</td></tr>
              <tr><th>Brief</th><td>9,01</td></tr>
              <tr><th>Zeit</th><td>05.05.26 22:02</td></tr>
            </table>
        """)
        table = BeautifulSoup(html, "html.parser").find("table")
        assert _extract_timestamp(table) == datetime(2026, 5, 5, 22, 2)

    def test_returns_none_for_dash_timestamp(self):
        from app.parsers.quotes import _extract_timestamp

        table = _table([("Brief", "--"), ("Zeit", "-- --")])
        assert _extract_timestamp(table) is None

    def test_returns_none_when_no_zeit_row(self):
        from app.parsers.quotes import _extract_timestamp

        table = _table([("Geld", "10,00")])
        assert _extract_timestamp(table) is None


# ---------------------------------------------------------------------------
# parse_quote — asset-class guard
# ---------------------------------------------------------------------------


class TestParseQuoteAssetClassGuard:
    """parse_quote raises HTTP 501 for special (non-tradeable) asset classes only."""

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "asset_class",
        [
            AssetClass.INDEX,
            AssetClass.COMMODITY,
            AssetClass.CURRENCY,
        ],
    )
    async def test_raises_501_for_special_asset_classes(self, asset_class):
        from app.parsers.quotes import parse_quote

        with patch(
            "app.parsers.quotes.parse_instrument_data",
            new_callable=AsyncMock,
            return_value=_instrument(asset_class),
        ):
            with pytest.raises(HTTPException) as exc_info:
                await parse_quote("846900", None)
        assert exc_info.value.status_code == 501

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "asset_class",
        [
            AssetClass.STOCK,
            AssetClass.BOND,
            AssetClass.ETF,
            AssetClass.FONDS,
            AssetClass.WARRANT,
            AssetClass.CERTIFICATE,
        ],
    )
    async def test_does_not_raise_501_for_standard_asset_classes(self, asset_class):
        """Standard tradeable assets should pass the guard and attempt to fetch the page."""
        from app.parsers.quotes import parse_quote

        with (
            patch(
                "app.parsers.quotes.parse_instrument_data",
                new_callable=AsyncMock,
                return_value=_instrument(asset_class),
            ),
            patch(
                "app.parsers.quotes.fetch_one",
                new_callable=AsyncMock,
                side_effect=Exception("scraping skipped in unit test"),
            ),
        ):
            with pytest.raises(Exception, match="scraping skipped"):
                await parse_quote("846900", None)
