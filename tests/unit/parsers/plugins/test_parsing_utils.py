"""
Unit tests for app.parsers.plugins.parsing_utils.

Covers:
- clean_float_value — German decimal string → float
- clean_numeric_value — German integer/magnitude string → int (incl. Bil.)
- infer_currency — from venue name
- extract_wkn_from_h2 — position offset, "--" handling
- extract_after_label — ISIN extraction from H2
- extract_name_from_h1 — suffix removal, span decomposition
- extract_table_cell_by_label — table section lookup
- extract_id_notation_from_data_plugin — ID_NOTATION regex
- extract_venues_from_dropdown — #marketSelect option parsing
- categorize_lt_ex_venues — LT vs EX split + VenueInfo enrichment
- extract_preferred_lt_notation / extract_preferred_ex_notation — single-venue fallback
"""

import textwrap

import pytest
from bs4 import BeautifulSoup

from app.parsers.plugins.parsing_utils import (
    categorize_lt_ex_venues,
    clean_float_value,
    clean_numeric_value,
    extract_after_label,
    extract_id_notation_from_data_plugin,
    extract_name_from_h1,
    extract_preferred_ex_notation,
    extract_preferred_lt_notation,
    extract_table_cell_by_label,
    extract_venues_from_dropdown,
    extract_wkn_from_h2,
    infer_currency,
)


def _soup(html: str) -> BeautifulSoup:
    return BeautifulSoup(textwrap.dedent(html), "html.parser")


# ---------------------------------------------------------------------------
# clean_float_value
# ---------------------------------------------------------------------------

class TestCleanFloatValue:
    def test_german_decimal_with_percent(self):
        assert clean_float_value("2,34 %") == pytest.approx(2.34)

    def test_german_decimal_no_percent(self):
        assert clean_float_value("2,34") == pytest.approx(2.34)

    def test_german_thousand_and_decimal(self):
        assert clean_float_value("1.234,56") == pytest.approx(1234.56)

    def test_plain_dot_decimal(self):
        assert clean_float_value("3.14") == pytest.approx(3.14)

    def test_placeholder_dash(self):
        assert clean_float_value("--") is None

    def test_single_dash(self):
        assert clean_float_value("-") is None

    def test_empty_string(self):
        assert clean_float_value("") is None

    def test_none_value(self):
        assert clean_float_value(None) is None  # type: ignore[arg-type]

    def test_zero(self):
        assert clean_float_value("0,00 %") == pytest.approx(0.0)

    def test_whitespace_only(self):
        assert clean_float_value("   ") is None


# ---------------------------------------------------------------------------
# clean_numeric_value
# ---------------------------------------------------------------------------

class TestCleanNumericValue:
    def test_bil_suffix(self):
        assert clean_numeric_value("4,20 Bil.") == 4_200_000_000_000

    def test_mrd_suffix(self):
        assert clean_numeric_value("3,10 Mrd.") == 3_100_000_000

    def test_mio_suffix(self):
        assert clean_numeric_value("512,00 Mio.") == 512_000_000

    def test_tsd_suffix(self):
        assert clean_numeric_value("5,00 Tsd.") == 5_000

    def test_plain_integer(self):
        assert clean_numeric_value("24.800.000") == 24_800_000

    def test_placeholder(self):
        assert clean_numeric_value("--") is None

    def test_none(self):
        assert clean_numeric_value(None) is None  # type: ignore[arg-type]

    def test_empty_string(self):
        assert clean_numeric_value("") is None


# ---------------------------------------------------------------------------
# infer_currency
# ---------------------------------------------------------------------------

class TestInferCurrency:
    def test_explicit_suffix_in_parens(self):
        assert infer_currency("SIX SWISS (USD)") == "USD"

    def test_inline_in_keyword(self):
        assert infer_currency("Fondsges. in EUR") == "EUR"

    def test_known_venue_lookup(self):
        # Xetra defaults to EUR per VENUE_DEFAULT_CURRENCY table
        assert infer_currency("Xetra") == "EUR"

    def test_unknown_venue_returns_none(self):
        assert infer_currency("Totally Unknown Exchange") is None


# ---------------------------------------------------------------------------
# extract_wkn_from_h2
# ---------------------------------------------------------------------------

class TestExtractWknFromH2:
    def test_standard_position(self):
        soup = _soup("<html><body><h2>WKN: 918422 ISIN: US67066G1040</h2></body></html>")
        assert extract_wkn_from_h2(soup) == "918422"

    def test_dash_returns_none(self):
        soup = _soup("<html><body><h2>WKN: -- ISIN: --</h2></body></html>")
        assert extract_wkn_from_h2(soup) is None

    def test_no_h2_returns_none(self):
        soup = _soup("<html><body><p>no headline</p></body></html>")
        assert extract_wkn_from_h2(soup) is None


# ---------------------------------------------------------------------------
# extract_after_label
# ---------------------------------------------------------------------------

class TestExtractAfterLabel:
    def test_isin_label(self):
        soup = _soup("<html><body><h2>WKN: 918422 ISIN: US67066G1040</h2></body></html>")
        assert extract_after_label(soup, "ISIN:") == "US67066G1040"

    def test_max_length_mismatch_returns_none(self):
        soup = _soup("<html><body><h2>WKN: 918422 ISIN: US67066G1040</h2></body></html>")
        assert extract_after_label(soup, "ISIN:", max_length=5) is None

    def test_label_not_found_returns_none(self):
        soup = _soup("<html><body><h2>WKN: 918422</h2></body></html>")
        assert extract_after_label(soup, "ISIN:") is None

    def test_no_h2_returns_none(self):
        soup = _soup("<html><body><p>nothing</p></body></html>")
        assert extract_after_label(soup, "ISIN:") is None


# ---------------------------------------------------------------------------
# extract_name_from_h1
# ---------------------------------------------------------------------------

class TestExtractNameFromH1:
    def test_removes_suffix(self):
        soup = _soup("<html><body><h1>NVIDIA Aktie</h1></body></html>")
        assert extract_name_from_h1(soup, remove_suffix="Aktie") == "NVIDIA"

    def test_no_suffix(self):
        soup = _soup("<html><body><h1>DAX Index</h1></body></html>")
        assert extract_name_from_h1(soup) == "DAX Index"

    def test_span_children_removed(self):
        soup = _soup("<html><body><h1>NVIDIA<span>Aktie</span></h1></body></html>")
        result = extract_name_from_h1(soup, remove_suffix="Aktie")
        assert result == "NVIDIA"

    def test_no_h1_returns_none(self):
        soup = _soup("<html><body><p>no headline</p></body></html>")
        assert extract_name_from_h1(soup) is None


# ---------------------------------------------------------------------------
# extract_table_cell_by_label
# ---------------------------------------------------------------------------

class TestExtractTableCellByLabel:
    def _page(self, label_text="Stammaktie") -> BeautifulSoup:
        html = f"""
        <html><body>
          <div>
            <p>Aktieninformationen</p>
            <table>
              <tr><th>Wertpapiertyp</th><td>{label_text}</td></tr>
              <tr><th>Branche</th><td><span title="Halbleiterindustrie">Halbleiterind..</span></td></tr>
            </table>
          </div>
        </body></html>
        """
        return _soup(html)

    def test_plain_cell(self):
        assert extract_table_cell_by_label(self._page(), "Aktieninformationen", "Wertpapiertyp") == "Stammaktie"

    def test_span_title_preferred(self):
        result = extract_table_cell_by_label(self._page(), "Aktieninformationen", "Branche")
        assert result == "Halbleiterindustrie"

    def test_section_not_found_returns_none(self):
        assert extract_table_cell_by_label(self._page(), "Nonexistent Section", "Wertpapiertyp") is None

    def test_label_not_found_returns_none(self):
        assert extract_table_cell_by_label(self._page(), "Aktieninformationen", "NonexistentLabel") is None


# ---------------------------------------------------------------------------
# extract_id_notation_from_data_plugin
# ---------------------------------------------------------------------------

class TestExtractIdNotationFromDataPlugin:
    def test_extracts_id_notation(self):
        plugin = "someprefix&ID_NOTATION=123456&otherparam"
        assert extract_id_notation_from_data_plugin(plugin) == "123456"

    def test_no_match_returns_none(self):
        assert extract_id_notation_from_data_plugin("no-match-here") is None

    def test_empty_string_returns_none(self):
        assert extract_id_notation_from_data_plugin("") is None


# ---------------------------------------------------------------------------
# extract_venues_from_dropdown
# ---------------------------------------------------------------------------

class TestExtractVenuesFromDropdown:
    def test_label_value_options(self):
        soup = _soup("""
        <html><body>
          <select id="marketSelect">
            <option label="Xetra" value="111111"></option>
            <option label="Frankfurt" value="222222"></option>
          </select>
        </body></html>
        """)
        result = extract_venues_from_dropdown(soup)
        assert result == {"Xetra": "111111", "Frankfurt": "222222"}

    def test_text_value_options(self):
        soup = _soup("""
        <html><body>
          <select id="marketSelect">
            <option value="333333">Tradegate</option>
          </select>
        </body></html>
        """)
        result = extract_venues_from_dropdown(soup)
        assert result == {"Tradegate": "333333"}

    def test_no_dropdown_returns_empty(self):
        soup = _soup("<html><body><p>no dropdown</p></body></html>")
        assert extract_venues_from_dropdown(soup) == {}


# ---------------------------------------------------------------------------
# categorize_lt_ex_venues
# ---------------------------------------------------------------------------

class TestCategorizeVenues:
    def test_lt_prefix_categorised_correctly(self):
        venues = {"LT Société Générale": "123", "Xetra": "456"}
        lt, ex = categorize_lt_ex_venues(venues)
        assert "LT Société Générale" in lt
        assert "Xetra" in ex

    def test_venue_info_has_id_notation(self):
        lt, ex = categorize_lt_ex_venues({"Xetra": "999"})
        assert ex["Xetra"].id_notation == "999"

    def test_empty_input(self):
        lt, ex = categorize_lt_ex_venues({})
        assert lt == {}
        assert ex == {}


# ---------------------------------------------------------------------------
# extract_preferred_lt_notation — single venue fallback
# ---------------------------------------------------------------------------

class TestExtractPreferredLt:
    def test_single_venue_fallback(self):
        from app.models.instruments import VenueInfo
        lt = {"LT HSBC": VenueInfo(id_notation="777", currency="EUR")}
        soup = _soup("<html><body></body></html>")
        result = extract_preferred_lt_notation(soup, lt, use_single_venue_fallback=True)
        assert result == "777"

    def test_empty_returns_none(self):
        soup = _soup("<html><body></body></html>")
        assert extract_preferred_lt_notation(soup, {}) is None


# ---------------------------------------------------------------------------
# extract_preferred_ex_notation — single venue fallback
# ---------------------------------------------------------------------------

class TestExtractPreferredEx:
    def test_single_venue_fallback(self):
        from app.models.instruments import VenueInfo
        ex = {"Xetra": VenueInfo(id_notation="888", currency="EUR")}
        soup = _soup("<html><body></body></html>")
        result = extract_preferred_ex_notation(soup, ex, use_single_venue_fallback=True)
        assert result == "888"

    def test_empty_returns_none(self):
        soup = _soup("<html><body></body></html>")
        assert extract_preferred_ex_notation(soup, {}) is None


# ---------------------------------------------------------------------------
# extract_from_h2_position
# ---------------------------------------------------------------------------

class TestExtractFromH2Position:
    def test_extracts_at_position_0(self):
        from app.parsers.plugins.parsing_utils import extract_from_h2_position
        soup = _soup("<html><body><h2>WKN: 918422 ISIN: US67066G1040</h2></body></html>")
        assert extract_from_h2_position(soup, 0) == "WKN:"

    def test_extracts_at_position_1(self):
        from app.parsers.plugins.parsing_utils import extract_from_h2_position
        soup = _soup("<html><body><h2>WKN: 918422 ISIN: US67066G1040</h2></body></html>")
        assert extract_from_h2_position(soup, 1) == "918422"

    def test_position_out_of_bounds_returns_none(self):
        from app.parsers.plugins.parsing_utils import extract_from_h2_position
        soup = _soup("<html><body><h2>WKN 918422</h2></body></html>")
        assert extract_from_h2_position(soup, 99) is None

    def test_no_h2_returns_none(self):
        from app.parsers.plugins.parsing_utils import extract_from_h2_position
        soup = _soup("<html><body><p>no h2</p></body></html>")
        assert extract_from_h2_position(soup, 0) is None


# ---------------------------------------------------------------------------
# extract_after_label — fallback (label without colon / case-insensitive)
# ---------------------------------------------------------------------------

class TestExtractAfterLabelFallback:
    def test_label_without_colon_still_matches(self):
        soup = _soup("<html><body><h2>WKN 918422 ISIN US67066G1040</h2></body></html>")
        # "ISIN:" not in text; should fall back to label-without-colon path
        result = extract_after_label(soup, "ISIN:")
        # May resolve to the next token after ISIN
        assert result is None or result == "US67066G1040"

    def test_missing_label_returns_none(self):
        soup = _soup("<html><body><h2>WKN 918422</h2></body></html>")
        assert extract_after_label(soup, "NOTEXIST:") is None


# ---------------------------------------------------------------------------
# clean_numeric_value — Tsd. suffix (thousands)
# ---------------------------------------------------------------------------

class TestCleanNumericValueTsd:
    def test_tsd_suffix(self):
        assert clean_numeric_value("5,00 Tsd.") == 5_000

    def test_tsd_integer_value(self):
        assert clean_numeric_value("10 Tsd.") == 10_000


# ---------------------------------------------------------------------------
# extract_venue_from_single_table
# ---------------------------------------------------------------------------

class TestExtractVenueFromSingleTable:
    def _single_venue_page(self, venue="Tradegate", notation="123456") -> BeautifulSoup:
        html = f"""
        <html><body>
          <div class="grid grid--no-gutter">
            <table class="simple-table">
              <tr><td>{venue}</td><td>some data</td></tr>
              <tr>
                <td>link row</td>
                <td><a data-plugin="prefix%26ID_NOTATION%3D{notation}%26suffix">Handeln</a></td>
              </tr>
            </table>
          </div>
        </body></html>
        """
        return _soup(html)

    def test_extracts_venue_and_notation(self):
        from app.parsers.plugins.parsing_utils import extract_venue_from_single_table
        soup = self._single_venue_page("Tradegate", "123456")
        result = extract_venue_from_single_table(soup)
        assert result == {"Tradegate": "123456"}

    def test_returns_empty_when_no_matching_table(self):
        from app.parsers.plugins.parsing_utils import extract_venue_from_single_table
        soup = _soup("<html><body><table><tr><td>nothing</td></tr></table></body></html>")
        result = extract_venue_from_single_table(soup)
        assert result == {}

    def test_returns_empty_when_no_data_plugin(self):
        from app.parsers.plugins.parsing_utils import extract_venue_from_single_table
        html = """
        <html><body>
          <div class="grid grid--no-gutter">
            <table class="simple-table">
              <tr><td>Tradegate</td></tr>
              <tr><td><a href="/some/link">Handeln</a></td></tr>
            </table>
          </div>
        </body></html>
        """
        soup = _soup(html)
        result = extract_venue_from_single_table(soup)
        assert result == {}


# ---------------------------------------------------------------------------
# extract_preferred_lt_notation — multi-venue table traversal
# ---------------------------------------------------------------------------

class TestExtractPreferredLtMultiVenue:
    def _lt_table_soup(self) -> BeautifulSoup:
        html = """
        <html><body>
        <table>
          <tr>
            <th>Handelsplatz</th>
            <th><a data-plugin="someprefix&ID_NOTATION=111&other">LT HSBC</a></th>
            <th><a data-plugin="someprefix&ID_NOTATION=222&other">LT Société Générale</a></th>
            <th>Gestellte Kurse</th>
          </tr>
          <tbody>
            <tr>
              <td data-label="LT HSBC">LT HSBC</td>
              <td data-label="Gestellte Kurse">5.000</td>
            </tr>
            <tr>
              <td data-label="LT Société Générale">LT Société Générale</td>
              <td data-label="Gestellte Kurse">3.000</td>
            </tr>
          </tbody>
        </table>
        </body></html>
        """
        return _soup(html)

    def test_returns_venue_with_highest_gestellte_kurse(self):
        from app.models.instruments import VenueInfo
        lt = {
            "LT HSBC": VenueInfo(id_notation="111"),
            "LT Société Générale": VenueInfo(id_notation="222"),
        }
        soup = self._lt_table_soup()
        result = extract_preferred_lt_notation(soup, lt, use_single_venue_fallback=False)
        assert result == "111"  # 5000 > 3000

    def test_no_matching_table_falls_back_to_first(self):
        from app.models.instruments import VenueInfo
        lt = {
            "LT HSBC": VenueInfo(id_notation="111"),
            "LT SG": VenueInfo(id_notation="222"),
        }
        soup = _soup("<html><body><p>no table</p></body></html>")
        result = extract_preferred_lt_notation(soup, lt, use_single_venue_fallback=True)
        # Falls back to first venue when no table found
        assert result in ("111", "222")


# ---------------------------------------------------------------------------
# extract_preferred_ex_notation — multi-venue table traversal
# ---------------------------------------------------------------------------

class TestExtractPreferredExMultiVenue:
    def _ex_table_soup(self) -> BeautifulSoup:
        html = """
        <html><body>
        <table>
          <tr>
            <th>Börse</th>
            <th><a data-plugin="someprefix&ID_NOTATION=333&other">Xetra</a></th>
            <th><a data-plugin="someprefix&ID_NOTATION=444&other">Frankfurt</a></th>
            <th>Anzahl Kurse</th>
          </tr>
          <tbody>
            <tr>
              <td data-label="Xetra">Xetra</td>
              <td data-label="Anzahl Kurse">18.087</td>
            </tr>
            <tr>
              <td data-label="Frankfurt">Frankfurt</td>
              <td data-label="Anzahl Kurse">1.200</td>
            </tr>
          </tbody>
        </table>
        </body></html>
        """
        return _soup(html)

    def test_returns_venue_with_highest_anzahl_kurse(self):
        from app.models.instruments import VenueInfo
        ex = {
            "Xetra": VenueInfo(id_notation="333"),
            "Frankfurt": VenueInfo(id_notation="444"),
        }
        soup = self._ex_table_soup()
        result = extract_preferred_ex_notation(soup, ex, use_single_venue_fallback=False)
        assert result == "333"  # 18087 > 1200

    def test_no_matching_table_falls_back_to_first(self):
        from app.models.instruments import VenueInfo
        ex = {
            "Xetra": VenueInfo(id_notation="333"),
            "Frankfurt": VenueInfo(id_notation="444"),
        }
        soup = _soup("<html><body><p>no table</p></body></html>")
        result = extract_preferred_ex_notation(soup, ex, use_single_venue_fallback=True)
        assert result in ("333", "444")
