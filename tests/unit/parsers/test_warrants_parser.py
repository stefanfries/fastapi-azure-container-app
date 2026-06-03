"""Unit tests for app.parsers.warrants — pure helpers (no HTTP, no mocking)."""

from datetime import date
from urllib.parse import parse_qs, urlparse

import pytest
from bs4 import BeautifulSoup

from app.core.constants import BASE_URL
from app.parsers.warrants import (
    WARRANT_FINDER_RESULTS_URL,
    _get_total_pages,
    _greek_filter_pairs,
    _parse_date,
    _parse_maturity_param,
    _parse_warrant_rows,
    build_warrant_finder_url,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_BASE_URL_ARGS = dict(
    id_notation_underlying="9386126",
    underlying_name="NVIDIA CORPORATION",
)


def _qs(url: str) -> dict[str, list[str]]:
    """Parse the query string of *url* into a dict of lists."""
    return parse_qs(urlparse(url).query, keep_blank_values=True)


def _build(**kwargs) -> dict[str, list[str]]:
    """Call build_warrant_finder_url with base args + overrides, return parsed QS."""
    return _qs(build_warrant_finder_url(**{**_BASE_URL_ARGS, **kwargs}))


def _pagination_html(pages: list[int]) -> BeautifulSoup:
    spans = "".join(f'<span class="pagination__page">{p}</span>' for p in pages)
    return BeautifulSoup(f'<div class="pagination">{spans}</div>', "html.parser")


def _table_row(
    isin: str,
    wkn: str = "MK9L2L",
    strike: str = "220,00 USD",
    ratio: str = "10 : 1",
    maturity: str = "16.06.27",
    last_day: str = "16.06.27",
    issuer: str = "Morgan Stanley",
    link_path: str = "/inf/optionsscheine/detail/uebersicht.html?wkn=MK9L2L",
) -> str:
    return f"""
    <tr>
        <td data-label="ISIN">{isin}</td>
        <td data-label="WKN">{wkn}</td>
        <td data-label="ISINWKN"><a href="{link_path}">{wkn}</a></td>
        <td data-label="Basispreis">{strike}</td>
        <td data-label="Bez.Verh.">{ratio}</td>
        <td data-label="Fälligkeit">{maturity}</td>
        <td data-label="letzter H.Tag">{last_day}</td>
        <td data-label="Emittent">{issuer}</td>
    </tr>"""


def _warrant_table(*rows: str) -> BeautifulSoup:
    return BeautifulSoup(
        f'<table class="table--comparison"><tbody>{"".join(rows)}</tbody></table>',
        "html.parser",
    )


# ---------------------------------------------------------------------------
# _greek_filter_pairs
# ---------------------------------------------------------------------------


class TestGreekFilterPairs:
    def test_both_none_emits_disabled_placeholder(self):
        pairs = _greek_filter_pairs("DELTA", None, None)
        assert pairs == [("DELTA_VALUE", ""), ("DELTA_COMPARATOR", "gt")]

    def test_min_only_emits_gt(self):
        pairs = _greek_filter_pairs("DELTA", 0.5, None)
        assert pairs == [("DELTA_VALUE", "0.5"), ("DELTA_COMPARATOR", "gt")]

    def test_max_only_emits_lt(self):
        pairs = _greek_filter_pairs("DELTA", None, 0.8)
        assert pairs == [("DELTA_VALUE", "0.8"), ("DELTA_COMPARATOR", "lt")]

    def test_both_bounds_emits_four_params(self):
        pairs = _greek_filter_pairs("DELTA", 0.5, 0.8)
        assert pairs == [
            ("DELTA_VALUE", "0.5"),
            ("DELTA_COMPARATOR", "gt"),
            ("DELTA_VALUE", "0.8"),
            ("DELTA_COMPARATOR", "lt"),
        ]

    def test_prefix_propagated(self):
        pairs = _greek_filter_pairs("GEARING", 2.0, None)
        assert pairs[0] == ("GEARING_VALUE", "2.0")
        assert pairs[1] == ("GEARING_COMPARATOR", "gt")


# ---------------------------------------------------------------------------
# _parse_maturity_param
# ---------------------------------------------------------------------------


class TestParseMaturityParam:
    def test_none_disables_filter(self):
        assert _parse_maturity_param(None) == ("", "", False)

    def test_range_code_passed_through(self):
        assert _parse_maturity_param("Range_6M") == ("Range_6M", "", False)

    def test_range_now(self):
        assert _parse_maturity_param("Range_NOW") == ("Range_NOW", "", False)

    def test_iso_date_converted(self):
        result = _parse_maturity_param("2027-06-16")
        assert result == ("Range_CHOOSE_DATE", "16.06.2027", True)

    def test_comdirect_date_passed_through(self):
        result = _parse_maturity_param("16.06.2027")
        assert result == ("Range_CHOOSE_DATE", "16.06.2027", True)

    def test_invalid_string_raises(self):
        with pytest.raises(ValueError, match="Invalid maturity date"):
            _parse_maturity_param("not-a-date")


# ---------------------------------------------------------------------------
# _parse_date
# ---------------------------------------------------------------------------


class TestParseDate:
    def test_two_digit_year(self):
        assert _parse_date("16.06.27") == date(2027, 6, 16)

    def test_dash_returns_none(self):
        assert _parse_date("--") is None

    def test_empty_returns_none(self):
        assert _parse_date("") is None

    def test_whitespace_stripped(self):
        assert _parse_date("  16.06.27  ") == date(2027, 6, 16)

    def test_unparseable_returns_none(self):
        assert _parse_date("not-a-date") is None


# ---------------------------------------------------------------------------
# build_warrant_finder_url
# ---------------------------------------------------------------------------


class TestBuildWarrantFinderUrl:
    def test_url_starts_with_results_base(self):
        url = build_warrant_finder_url(**_BASE_URL_ARGS)
        assert url.startswith(WARRANT_FINDER_RESULTS_URL)

    def test_id_notation_in_url(self):
        qs = _build()
        assert qs["ID_NOTATION_UNDERLYING"] == ["9386126"]

    def test_underlying_name_in_url(self):
        qs = _build()
        assert qs["UNDERLYING_NAME_SEARCH"] == ["NVIDIA CORPORATION"]

    def test_default_preselection_is_all(self):
        qs = _build()
        assert qs["PRESELECTION"] == ["ALL"]

    def test_preselection_call(self):
        from app.models.warrants import WarrantPreselection

        qs = _build(preselection=WarrantPreselection.CALL)
        assert qs["PRESELECTION"] == ["CALL"]

    def test_issuer_action_default_false(self):
        qs = _build()
        assert qs["ISSUER_ACTION"] == ["false"]

    def test_issuer_action_true(self):
        qs = _build(issuer_action=True)
        assert qs["ISSUER_ACTION"] == ["true"]

    def test_integer_strike_serialised_without_decimal(self):
        qs = _build(strike_min=220.0, strike_max=220.0)
        assert qs["STRIKE_ABS_FROM"] == ["220"]
        assert qs["STRIKE_ABS_TO"] == ["220"]

    def test_fractional_strike_serialised_with_decimal(self):
        qs = _build(strike_min=220.5)
        assert qs["STRIKE_ABS_FROM"] == ["220.5"]

    def test_no_strike_emits_empty(self):
        qs = _build()
        assert qs["STRIKE_ABS_FROM"] == [""]
        assert qs["STRIKE_ABS_TO"] == [""]

    def test_maturity_from_range_code(self):
        qs = _build(maturity_from="Range_6M")
        assert qs["DATE_TIME_MATURITY_FROM"] == ["Range_6M"]

    def test_maturity_from_iso_date(self):
        qs = _build(maturity_from="2027-06-01")
        assert qs["DATE_TIME_MATURITY_FROM"] == ["Range_CHOOSE_DATE"]
        assert qs["DATE_TIME_MATURITY_FROM_CAL"] == ["01.06.2027"]
        assert qs["date-DATE_TIME_MATURITY_FROM_CAL"] == ["on"]

    def test_maturity_to_iso_date_adds_checkbox(self):
        qs = _build(maturity_to="2027-06-30")
        assert qs.get("date-DATE_TIME_MATURITY_TO_CAL") == ["on"]

    def test_all_14_greek_prefixes_present_when_disabled(self):
        qs = _build()
        for prefix in (
            "IMPLIED_VOLATILITY",
            "DELTA",
            "LEVERAGE",
            "PREMIUM_PER_ANNUM",
            "GEARING",
            "PRESENT_VALUE",
            "SPREAD_ASK_PCT",
            "THETA_DAY",
            "THEORETICAL_VALUE",
            "INTRINSIC_VALUE",
            "BREAK_EVEN",
            "MONEYNESS",
            "VEGA",
            "GAMMA",
        ):
            assert f"{prefix}_VALUE" in qs, f"{prefix}_VALUE missing from URL"
            assert f"{prefix}_COMPARATOR" in qs, f"{prefix}_COMPARATOR missing from URL"

    def test_delta_min_max_repeated_params(self):
        url = build_warrant_finder_url(**_BASE_URL_ARGS, delta_min=0.5, delta_max=0.8)
        # parse_qs collapses repeated keys into a list
        qs = _qs(url)
        assert qs["DELTA_VALUE"] == ["0.5", "0.8"]
        assert qs["DELTA_COMPARATOR"] == ["gt", "lt"]

    def test_omega_maps_to_gearing(self):
        qs = _build(omega_min=5.0)
        assert qs["GEARING_VALUE"] == ["5.0"]
        assert qs["GEARING_COMPARATOR"] == ["gt"]

    def test_issuer_group_id_included(self):
        qs = _build(issuer_group_id="123")
        assert qs["ID_GROUP_ISSUER"] == ["123"]

    def test_no_issuer_group_id_emits_empty(self):
        qs = _build()
        assert qs["ID_GROUP_ISSUER"] == [""]

    def test_keep_cookie_appended(self):
        qs = _build()
        assert qs["keepCookie"] == ["true"]


# ---------------------------------------------------------------------------
# _get_total_pages
# ---------------------------------------------------------------------------


class TestGetTotalPages:
    def test_no_pagination_returns_1(self):
        soup = BeautifulSoup("<div>no pager here</div>", "html.parser")
        assert _get_total_pages(soup) == 1

    def test_single_page_returns_1(self):
        # Pagination widget present but only page "1"
        assert _get_total_pages(_pagination_html([1])) == 1

    def test_three_pages(self):
        assert _get_total_pages(_pagination_html([1, 2, 3])) == 3

    def test_non_digit_spans_ignored(self):
        soup = BeautifulSoup(
            '<div class="pagination">'
            '<span class="pagination__page">prev</span>'
            '<span class="pagination__page">1</span>'
            '<span class="pagination__page">2</span>'
            "</div>",
            "html.parser",
        )
        assert _get_total_pages(soup) == 2


# ---------------------------------------------------------------------------
# _parse_warrant_rows
# ---------------------------------------------------------------------------


class TestParseWarrantRows:
    def test_no_table_returns_empty(self):
        soup = BeautifulSoup("<div>nothing</div>", "html.parser")
        assert _parse_warrant_rows(soup) == []

    def test_table_without_isin_rows_returns_empty(self):
        soup = BeautifulSoup(
            '<table class="table--comparison"><tr><td>no isin</td></tr></table>',
            "html.parser",
        )
        assert _parse_warrant_rows(soup) == []

    def test_single_row_parsed(self):
        soup = _warrant_table(_table_row("DE000MK9L2L9"))
        result = _parse_warrant_rows(soup)
        assert len(result) == 1
        w = result[0]
        assert w.isin == "DE000MK9L2L9"
        assert w.wkn == "MK9L2L"
        assert w.strike == pytest.approx(220.0)
        assert w.strike_currency == "USD"
        assert w.ratio == "10 : 1"
        assert w.maturity_date == date(2027, 6, 16)
        assert w.last_trading_day == date(2027, 6, 16)
        assert w.issuer == "Morgan Stanley"

    def test_link_prepended_with_base_url_when_relative(self):
        soup = _warrant_table(_table_row("DE000MK9L2L9"))
        w = _parse_warrant_rows(soup)[0]
        assert w.link.startswith(BASE_URL)

    def test_link_kept_as_is_when_absolute(self):
        row = _table_row("DE000MK9L2L9", link_path="https://other.example.com/page")
        soup = _warrant_table(row)
        w = _parse_warrant_rows(soup)[0]
        assert w.link == "https://other.example.com/page"

    def test_double_dash_issuer_becomes_none(self):
        soup = _warrant_table(_table_row("DE000MK9L2L9", issuer="--"))
        w = _parse_warrant_rows(soup)[0]
        assert w.issuer is None

    def test_double_dash_strike_becomes_none(self):
        soup = _warrant_table(_table_row("DE000MK9L2L9", strike="--"))
        w = _parse_warrant_rows(soup)[0]
        assert w.strike is None
        assert w.strike_currency is None

    def test_double_dash_maturity_becomes_none(self):
        soup = _warrant_table(_table_row("DE000MK9L2L9", maturity="--"))
        w = _parse_warrant_rows(soup)[0]
        assert w.maturity_date is None

    def test_multiple_rows_all_parsed(self):
        soup = _warrant_table(
            _table_row("DE000AA1111A", wkn="AA1111"),
            _table_row("DE000BB2222B", wkn="BB2222"),
        )
        result = _parse_warrant_rows(soup)
        assert len(result) == 2
        assert {w.wkn for w in result} == {"AA1111", "BB2222"}

    def test_no_wkn_cell_falls_back_to_dash(self):
        # Row with ISIN but no WKN cell
        html = (
            '<table class="table--comparison">'
            '<tr><td data-label="ISIN">DE000XX9999X</td></tr>'
            "</table>"
        )
        soup = BeautifulSoup(html, "html.parser")
        w = _parse_warrant_rows(soup)[0]
        assert w.wkn == "--"
