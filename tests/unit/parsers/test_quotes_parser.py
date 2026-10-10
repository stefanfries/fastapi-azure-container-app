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


class TestParseQuoteTimestamp:
    @pytest.mark.asyncio
    async def test_returns_berlin_timestamp_and_utc_timestamp(self):
        from datetime import UTC, datetime

        from app.parsers.quotes import parse_quote

        instrument = _instrument(AssetClass.STOCK)
        html = """
        <html>
          <head><meta itemprop="priceCurrency" content="EUR"></head>
          <body><div><h2>Kursdaten</h2><table>
            <tr><th>Geld</th><td>100,00</td></tr>
            <tr><th>Brief</th><td>101,00</td></tr>
            <tr><th>Zeit</th><td>05.05.26 22:02</td></tr>
            <tr><th>Börse</th><td>Xetra</td></tr>
          </table></div></body>
        </html>
        """
        with (
            patch(
                "app.parsers.quotes.parse_instrument_data",
                new_callable=AsyncMock,
                return_value=instrument,
            ),
            patch(
                "app.parsers.quotes.fetch_one",
                new_callable=AsyncMock,
                return_value=MagicMock(content=html.encode()),
            ),
            patch("app.parsers.quotes.extract_name_from_h1", return_value="Example"),
            patch("app.parsers.quotes.extract_wkn_from_h2", return_value="846900"),
        ):
            quote = await parse_quote("846900", None)

        assert quote.timestamp == datetime(2026, 5, 5, 22, 2)
        assert quote.timestamp_utc == datetime(2026, 5, 5, 20, 2, tzinfo=UTC)


class TestParseQuoteOHLC:
    async def _parse(self, asset_class: AssetClass, rows: str):
        from app.parsers.quotes import parse_quote

        html = f"""
        <html>
          <head><meta itemprop="priceCurrency" content="EUR"></head>
          <body><div><h2>Kursdaten</h2><table>
            <tr><th>Börse</th><td>Tradegate</td></tr>
            <tr><th>Diff. Vortag</th><td>+3,16 %</td></tr>
            <tr><th>Geld</th><td>105,50</td></tr>
            <tr><th>Brief</th><td>105,74</td></tr>
            <tr><th>Zeit</th><td>09.10.26 22:00</td></tr>
            {rows}
          </table></div></body>
        </html>
        """
        with (
            patch(
                "app.parsers.quotes.parse_instrument_data",
                new_callable=AsyncMock,
                return_value=_instrument(asset_class),
            ),
            patch(
                "app.parsers.quotes.fetch_one",
                new_callable=AsyncMock,
                return_value=MagicMock(content=html.encode()),
            ),
            patch("app.parsers.quotes.extract_name_from_h1", return_value="Example"),
            patch("app.parsers.quotes.extract_wkn_from_h2", return_value="846900"),
        ):
            return await parse_quote("846900", None)

    @pytest.mark.asyncio
    async def test_stock_layout(self):
        quote = await self._parse(
            AssetClass.STOCK,
            """
            <tr><th>Schluss Vortag</th><td>102,46</td></tr>
            <tr><th>Eröffnung</th><td>102,60</td></tr>
            <tr><th>Hoch</th><td>105,82</td></tr>
            <tr><th>Tief</th><td>102,42</td></tr>
            <tr><th>52W Hoch</th><td>112,30</td></tr>
            <tr><th>52W Tief</th><td>57,80</td></tr>
            """,
        )
        assert quote.prev_close == pytest.approx(102.46)
        assert quote.open == pytest.approx(102.60)
        assert quote.high == pytest.approx(105.82)
        assert quote.low == pytest.approx(102.42)

    @pytest.mark.asyncio
    async def test_warrant_layout(self):
        quote = await self._parse(
            AssetClass.WARRANT,
            """
            <tr><th>Vortag</th><td>3,225</td></tr>
            <tr><th>Eröffnung</th><td>3,415</td></tr>
            <tr><th>Hoch</th><td>3,605</td></tr>
            <tr><th>Tief</th><td>3,095</td></tr>
            """,
        )
        assert quote.prev_close == pytest.approx(3.225)
        assert quote.open == pytest.approx(3.415)
        assert quote.high == pytest.approx(3.605)
        assert quote.low == pytest.approx(3.095)

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        ("isin", "prev_close", "open_", "high", "low"),
        [
            ("DE000CT0UC86", 9.87, 9.82, 10.10, 9.82),
            ("DE000PA02VF4", 91.84, 92.11, 95.32, 92.06),
            ("DE000TD0MAP6", 84.84, 85.18, 88.33, 85.08),
            ("DE000CJ5LG63", 6.85, 6.86, 7.19, 6.85),
            ("DE000PF3CSC3", 5.35, 5.41, 5.88, 5.39),
        ],
    )
    async def test_certificate_layout(self, isin, prev_close, open_, high, low):
        # Real values from comdirect pages (09.10.26); certificates use the warrant labels
        quote = await self._parse(
            AssetClass.CERTIFICATE,
            f"""
            <tr><th>Spread homogen.</th><td>0,10</td></tr>
            <tr><th>Vortag</th><td>{prev_close:.2f}</td></tr>
            <tr><th>Eröffnung</th><td>{open_:.2f}</td></tr>
            <tr><th>Hoch</th><td>{high:.2f}</td></tr>
            <tr><th>Tief</th><td>{low:.2f}</td></tr>
            """.replace(".", ","),
        )
        assert quote.prev_close == pytest.approx(prev_close)
        assert quote.open == pytest.approx(open_)
        assert quote.high == pytest.approx(high)
        assert quote.low == pytest.approx(low)

    @pytest.mark.asyncio
    async def test_etf_layout_without_ohlc_rows(self):
        quote = await self._parse(AssetClass.ETF, "")
        assert quote.prev_close is None
        assert quote.open is None
        assert quote.high is None
        assert quote.low is None
