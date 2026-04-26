"""Parser for ETF asset class."""

from bs4 import BeautifulSoup

from app.models.instrument_details import ETFDetails, InstrumentDetails
from app.models.instruments import AssetClass
from app.parsers.plugins.parsing_utils import (
    clean_float_value,
    clean_numeric_value,
    extract_table_cell_by_label,
)
from app.parsers.plugins.standard_asset_parser import StandardAssetParser


class ETFParser(StandardAssetParser):
    """Parser for ETF asset class."""

    @property
    def asset_class(self) -> AssetClass:
        return AssetClass.ETF

    def parse_details(self, soup: BeautifulSoup) -> InstrumentDetails:
        return self._parse_etf_details(soup)

    def _parse_etf_details(self, soup: BeautifulSoup) -> ETFDetails:
        """
        Parse the "Stammdaten" table on the comdirect ETF page.

        German label → field mapping:
            Vergleichsindex      → tracked_index
            Laufende Kosten      → expense_ratio_percent  (e.g. "0,20 %")
            Abbildungsart        → replication_method
            Art                  → distribution_policy
            Auflagedatum         → inception_date
            Währung              → fund_currency
            Fondsvolumen         → fund_size  (e.g. "1,23 Mrd. EUR")
        """
        section = "Stammdaten"

        def _get(label: str) -> str | None:
            v = extract_table_cell_by_label(soup, section, label)
            return v if v and v.strip() not in ("--", "k. A.") else None

        tracked_index = _get("Vergleichsindex")
        expense_ratio_percent = clean_float_value(_get("Laufende Kosten"))
        replication_method = _get("Abbildungsart")
        distribution_policy_raw = _get("Art")
        distribution_policy = " ".join(distribution_policy_raw.split()) if distribution_policy_raw else None
        inception_date = self._parse_date(_get("Auflagedatum"))
        fund_currency = _get("Währung")

        fund_size_raw = _get("Fondsvolumen")
        fund_size: float | None = None
        if fund_size_raw:
            # Strip trailing currency code before parsing magnitude (e.g. "311,39 Mio. EUR")
            parts = fund_size_raw.split()
            if parts and len(parts[-1]) == 3 and parts[-1].isupper():
                parts = parts[:-1]
            numeric = clean_numeric_value(" ".join(parts))
            fund_size = float(numeric) if numeric is not None else None

        return ETFDetails(
            tracked_index=tracked_index,
            expense_ratio_percent=expense_ratio_percent,
            replication_method=replication_method,
            distribution_policy=distribution_policy,
            inception_date=inception_date,
            fund_currency=fund_currency,
            fund_size=fund_size,
        )
