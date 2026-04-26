"""Unit tests for app.parsers.plugins.certificate_parser.CertificateParser."""

import textwrap
from datetime import date

import pytest
from bs4 import BeautifulSoup

from app.models.instrument_details import CertificateDetails
from app.parsers.plugins.certificate_parser import CertificateParser


def _make_soup(html: str) -> BeautifulSoup:
    return BeautifulSoup(textwrap.dedent(html), "html.parser")


def _section_page(section_header: str, rows: list[tuple[str, str]]) -> BeautifulSoup:
    row_html = "\n".join(
        f"            <tr><th scope='row'>{label}</th><td>{value}</td></tr>"
        for label, value in rows
    )
    html = f"""
    <html><body>
      <div class="col__content">
        <p class="headline headline--h3">{section_header}</p>
        <div class="table__container--scroll">
          <table class="simple-table">
{row_html}
          </table>
        </div>
      </div>
    </body></html>
    """
    return _make_soup(html)


def _certificate_page(
    *,
    cert_type: str = "Discount",
    basiswert: str = "DAX",
    cap: str = "18.000,00 EUR",
    barrier: str = "14.000,00 EUR",
    participation: str = "100,00 %",
    faelligkeit: str = "20.12.2025",
    emittent: str = "DZ BANK AG",
    waehrung: str = "EUR",
) -> BeautifulSoup:
    return _section_page("Stammdaten", [
        ("Typ", cert_type),
        ("Basiswert", basiswert),
        ("Cap-Niveau", cap),
        ("Barriere", barrier),
        ("Partizipationsrate", participation),
        ("Fälligkeit", faelligkeit),
        ("Emittent", emittent),
        ("Währung", waehrung),
    ])


_parser = CertificateParser()


class TestCertificateDetailsParser:
    def test_returns_certificate_details_instance(self):
        assert isinstance(_parser.parse_details(_certificate_page()), CertificateDetails)

    def test_discriminator(self):
        assert _parser.parse_details(_certificate_page()).asset_class == "Certificate"

    def test_certificate_type(self):
        assert _parser.parse_details(_certificate_page(cert_type="Discount")).certificate_type == "Discount"

    def test_underlying_name(self):
        assert _parser.parse_details(_certificate_page(basiswert="DAX")).underlying_name == "DAX"

    def test_cap_value_and_currency(self):
        result = _parser.parse_details(_certificate_page(cap="18.000,00 EUR"))
        assert result.cap == pytest.approx(18_000.0)
        assert result.cap_currency == "EUR"

    def test_barrier_value_and_currency(self):
        result = _parser.parse_details(_certificate_page(barrier="14.000,00 EUR"))
        assert result.barrier == pytest.approx(14_000.0)
        assert result.barrier_currency == "EUR"

    def test_participation_rate(self):
        assert _parser.parse_details(_certificate_page(participation="100,00 %")).participation_rate == pytest.approx(100.0)

    def test_maturity_date(self):
        assert _parser.parse_details(_certificate_page(faelligkeit="20.12.2025")).maturity_date == date(2025, 12, 20)

    def test_open_end_maturity_is_none(self):
        assert _parser.parse_details(_certificate_page(faelligkeit="Open End")).maturity_date is None

    def test_issuer(self):
        assert _parser.parse_details(_certificate_page(emittent="DZ BANK AG")).issuer == "DZ BANK AG"

    def test_currency(self):
        assert _parser.parse_details(_certificate_page(waehrung="EUR")).currency == "EUR"

    def test_placeholder_cap_becomes_none(self):
        result = _parser.parse_details(_certificate_page(cap="--", barrier="--"))
        assert result.cap is None
        assert result.cap_currency is None
        assert result.barrier is None
        assert result.barrier_currency is None

    def test_missing_section_returns_empty_certificate_details(self):
        result = _parser.parse_details(_make_soup("<html><body><p>No data</p></body></html>"))
        assert isinstance(result, CertificateDetails)
        assert result.certificate_type is None
        assert result.maturity_date is None

    def test_no_cap_barrier_for_tracker(self):
        result = _parser.parse_details(_certificate_page(cert_type="Tracker", cap="--", barrier="--"))
        assert result.cap is None
        assert result.barrier is None
