"""Unit tests for the ADR-to-primary resolution service (app.services.adr_resolution)."""

from unittest.mock import AsyncMock, patch

from app.models.instrument_details import StockDetails
from app.models.instruments import AssetClass, GlobalIdentifiers, Instrument
from app.services import adr_resolution
from app.services.adr_resolution import (
    _normalize_company_name,
    is_adr,
    looks_like_adr_name,
    resolve_adr_to_primary,
    resolve_member_isin,
)


def _stock(
    *,
    name: str,
    isin: str,
    security_type: str | None,
    name_openfigi: str | None = None,
) -> Instrument:
    return Instrument(
        name=name,
        isin=isin,
        asset_class=AssetClass.STOCK,
        global_identifiers=GlobalIdentifiers(isin=isin, name_openfigi=name_openfigi),
        details=StockDetails(security_type=security_type),
    )


# ---------------------------------------------------------------------------
# is_adr
# ---------------------------------------------------------------------------


class TestIsAdr:
    def test_true_for_adr_stock(self) -> None:
        assert is_adr(_stock(name="ASML ADR", isin="USN070592100", security_type="ADR"))

    def test_false_for_common_stock(self) -> None:
        assert not is_adr(_stock(name="ASML", isin="NL0010273215", security_type="Stammaktie"))

    def test_false_when_details_missing(self) -> None:
        inst = Instrument(name="X", isin="US0378331005", asset_class=AssetClass.STOCK)
        assert not is_adr(inst)

    def test_false_for_non_stock(self) -> None:
        inst = Instrument(name="Idx", isin="DE0008469008", asset_class=AssetClass.INDEX)
        assert not is_adr(inst)


# ---------------------------------------------------------------------------
# looks_like_adr_name / _normalize_company_name
# ---------------------------------------------------------------------------


class TestNameHelpers:
    def test_looks_like_adr_true(self) -> None:
        assert looks_like_adr_name("ASML ADR")
        assert looks_like_adr_name("PINDUODUO INC. SP.ADR/4")

    def test_looks_like_adr_false(self) -> None:
        assert not looks_like_adr_name("ASML Holding")
        # "ADRIATIC" must not match the ADR token.
        assert not looks_like_adr_name("ADRIATIC METALS")

    def test_normalize_strips_suffixes(self) -> None:
        assert _normalize_company_name("ASML HOLDING NV-NY REG SHS") == "ASML HOLDING NV"
        assert _normalize_company_name("ALIBABA GROUP-SP ADR") == "ALIBABA GROUP"
        assert _normalize_company_name("BAIDU INC-SPON ADR") == "BAIDU INC"
        assert _normalize_company_name("ASML ADR") == "ASML"

    def test_normalize_keeps_plain_name(self) -> None:
        assert _normalize_company_name("NOVO NORDISK") == "NOVO NORDISK"


# ---------------------------------------------------------------------------
# resolve_adr_to_primary
# ---------------------------------------------------------------------------


class TestResolveAdrToPrimary:
    async def test_resolves_via_xetra_ticker(self) -> None:
        adr = _stock(
            name="ASML ADR",
            isin="USN070592100",
            security_type="ADR",
            name_openfigi="ASML HOLDING NV-NY REG SHS",
        )
        primary = _stock(name="ASML Holding", isin="NL0010273215", security_type="Stammaktie")

        with (
            patch.object(
                adr_resolution.openfigi_client,
                "search_by_name",
                new=AsyncMock(return_value=[{"ticker": "ASME", "exchCode": "GY"}]),
            ),
            patch(
                "app.parsers.instruments.parse_instrument_data",
                new=AsyncMock(return_value=primary),
            ),
        ):
            result = await resolve_adr_to_primary(adr)

        assert result == "NL0010273215"

    async def test_returns_none_when_no_openfigi_match(self) -> None:
        adr = _stock(
            name="BIONTECH ADR",
            isin="US09075V1026",
            security_type="ADR",
            name_openfigi="BIONTECH SE-ADR",
        )
        with patch.object(
            adr_resolution.openfigi_client,
            "search_by_name",
            new=AsyncMock(return_value=[]),
        ):
            result = await resolve_adr_to_primary(adr)

        assert result is None

    async def test_rejects_resolved_adr_and_returns_none(self) -> None:
        """A candidate ticker that itself resolves to an ADR is rejected."""
        adr = _stock(
            name="FOO ADR",
            isin="US1234567899",
            security_type="ADR",
            name_openfigi="FOO CORP-SP ADR",
        )
        another_adr = _stock(name="FOO ADR", isin="US1234567899", security_type="ADR")

        with (
            patch.object(
                adr_resolution.openfigi_client,
                "search_by_name",
                new=AsyncMock(return_value=[{"ticker": "FOO", "exchCode": "GY"}]),
            ),
            patch(
                "app.parsers.instruments.parse_instrument_data",
                new=AsyncMock(return_value=another_adr),
            ),
        ):
            result = await resolve_adr_to_primary(adr)

        assert result is None

    async def test_skips_failed_ticker_and_tries_next(self) -> None:
        primary = _stock(name="BAR PLC", isin="GB00B03MLX29", security_type="Stammaktie")

        # First Xetra search returns a bad ticker; second (home exch) returns a good one.
        search_mock = AsyncMock(side_effect=[[{"ticker": "BADX"}], [{"ticker": "GOODX"}]])

        async def fake_parse(ticker: str, *, _allow_adr_redirect: bool = True) -> Instrument:
            if ticker == "BADX":
                raise ValueError("not found")
            return primary

        with (
            patch.object(adr_resolution.openfigi_client, "search_by_name", new=search_mock),
            patch("app.parsers.instruments.parse_instrument_data", new=fake_parse),
        ):
            # ISIN country is US (no home-exch fallback), so force GB home by isin.
            adr_gb = _stock(
                name="BAR ADR",
                isin="GB00ADR00008",
                security_type="ADR",
                name_openfigi="BAR PLC-SP ADR",
            )
            result = await resolve_adr_to_primary(adr_gb)

        assert result == "GB00B03MLX29"

    async def test_returns_none_when_no_company_name(self) -> None:
        adr = Instrument(
            name="placeholder",
            isin="US1234567899",
            asset_class=AssetClass.STOCK,
            details=StockDetails(security_type="ADR"),
        )
        # Blank out the name so no company name is available for the search.
        adr.name = ""
        result = await resolve_adr_to_primary(adr)
        assert result is None


# ---------------------------------------------------------------------------
# resolve_member_isin
# ---------------------------------------------------------------------------


class TestResolveMemberIsin:
    async def test_non_adr_name_returns_isin_unchanged(self) -> None:
        # No parse, no OpenFIGI call for plain names.
        result = await resolve_member_isin("ASML Holding", "NL0010273215")
        assert result == "NL0010273215"

    async def test_adr_name_but_not_adr_detail_returns_isin(self) -> None:
        not_adr = _stock(name="X ADR", isin="US0000000002", security_type="Stammaktie")
        with patch(
            "app.parsers.instruments.parse_instrument_data",
            new=AsyncMock(return_value=not_adr),
        ):
            result = await resolve_member_isin("X ADR", "US0000000002")
        assert result == "US0000000002"

    async def test_adr_resolves_to_primary(self) -> None:
        adr = _stock(
            name="ASML ADR",
            isin="USN070592100",
            security_type="ADR",
            name_openfigi="ASML HOLDING NV",
        )
        with (
            patch(
                "app.parsers.instruments.parse_instrument_data",
                new=AsyncMock(return_value=adr),
            ),
            patch.object(
                adr_resolution,
                "resolve_adr_to_primary",
                new=AsyncMock(return_value="NL0010273215"),
            ),
        ):
            result = await resolve_member_isin("ASML ADR", "USN070592100")
        assert result == "NL0010273215"

    async def test_adr_unresolvable_returns_none(self) -> None:
        adr = _stock(name="X ADR", isin="US1111111118", security_type="ADR")
        with (
            patch(
                "app.parsers.instruments.parse_instrument_data",
                new=AsyncMock(return_value=adr),
            ),
            patch.object(
                adr_resolution,
                "resolve_adr_to_primary",
                new=AsyncMock(return_value=None),
            ),
        ):
            result = await resolve_member_isin("X ADR", "US1111111118")
        assert result is None

    async def test_parse_failure_returns_original_isin(self) -> None:
        with patch(
            "app.parsers.instruments.parse_instrument_data",
            new=AsyncMock(side_effect=RuntimeError("boom")),
        ):
            result = await resolve_member_isin("X ADR", "US1111111111")
        assert result == "US1111111111"
