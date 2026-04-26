"""Parser for FONDS (mutual fund) asset class."""

from bs4 import BeautifulSoup

from app.models.instrument_details import FondsDetails, InstrumentDetails
from app.models.instruments import AssetClass
from app.parsers.plugins.parsing_utils import (
    clean_float_value,
    clean_numeric_value,
    extract_table_cell_by_label,
)
from app.parsers.standard_asset_parser import StandardAssetParser


class FondsParser(StandardAssetParser):
    """Parser for FONDS asset class (Investmentfonds)."""

    @property
    def asset_class(self) -> AssetClass:
        return AssetClass.FONDS

    def parse_details(self, soup: BeautifulSoup) -> InstrumentDetails:
        return self._parse_fonds_details(soup)

    def _parse_fonds_details(self, soup: BeautifulSoup) -> FondsDetails:
        """
        Parse the "Stammdaten" table on the comdirect mutual-fund page.

        German label → field mapping:
            Fondskategorie    → fund_type
            Fondsmanager      → fund_manager
            Auflagedatum      → inception_date
            Art               → distribution_policy
            Laufende Kosten   → expense_ratio_percent  (e.g. "1,50 %")
            Währung           → fund_currency
            Fondsvolumen      → fund_size  (e.g. "512,00 Mio.")
        """
        section = "Stammdaten"

        def _get(label: str) -> str | None:
            v = extract_table_cell_by_label(soup, section, label)
            return v if v and v.strip() not in ("--", "k. A.") else None

        fund_type = _get("Fondskategorie")
        fund_manager = _get("Fondsmanager")
        inception_date = self._parse_date(_get("Auflagedatum"))
        distribution_policy_raw = _get("Art")
        distribution_policy = " ".join(distribution_policy_raw.split()) if distribution_policy_raw else None
        expense_ratio_percent = clean_float_value(_get("Laufende Kosten"))
        fund_currency = _get("Währung")

        fund_size_raw = _get("Fondsvolumen")
        fund_size: float | None = None
        if fund_size_raw:
            # Strip trailing currency code before parsing magnitude (e.g. "512,00 Mio. EUR")
            parts = fund_size_raw.split()
            if parts and len(parts[-1]) == 3 and parts[-1].isupper():
                parts = parts[:-1]
            numeric = clean_numeric_value(" ".join(parts))
            fund_size = float(numeric) if numeric is not None else None

        return FondsDetails(
            fund_type=fund_type,
            fund_manager=fund_manager,
            inception_date=inception_date,
            distribution_policy=distribution_policy,
            expense_ratio_percent=expense_ratio_percent,
            fund_currency=fund_currency,
            fund_size=fund_size,
        )
