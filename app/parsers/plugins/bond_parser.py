"""Parser for BOND asset class."""

from bs4 import BeautifulSoup

from app.models.instrument_details import BondDetails, InstrumentDetails
from app.models.instruments import AssetClass
from app.parsers.plugins.parsing_utils import (
    clean_float_value,
    extract_table_cell_by_label,
)
from app.parsers.plugins.standard_asset_parser import StandardAssetParser


class BondParser(StandardAssetParser):
    """Parser for BOND asset class (Anleihen)."""

    @property
    def asset_class(self) -> AssetClass:
        return AssetClass.BOND

    def parse_details(self, soup: BeautifulSoup) -> InstrumentDetails:
        return self._parse_bond_details(soup)

    def _parse_bond_details(self, soup: BeautifulSoup) -> BondDetails:
        """
        Parse the "Stammdaten" table on the comdirect bond page.

        German label → field mapping:
            Emittent          → issuer
            Nominalzinssatz   → coupon_rate_percent  (e.g. "10,250 %")
            Kupon-Art         → coupon_type  (e.g. "Fest")
            Ausgabedatum      → issue_date   (DD.MM.YYYY)
            Fälligkeit        → maturity_date
            Stückelung        → nominal_value + currency
            Typ               → bond_type
            Währung           → currency
        """
        section = "Stammdaten"

        def _get(label: str) -> str | None:
            v = extract_table_cell_by_label(soup, section, label)
            return v if v and v.strip() not in ("--", "k. A.") else None

        issuer = _get("Emittent")
        coupon_rate_percent = clean_float_value(_get("Nominalzinssatz"))
        coupon_type = _get("Kupon-Art")
        issue_date = self._parse_date(_get("Ausgabedatum"))
        maturity_date = self._parse_date(_get("Fälligkeit"))
        nominal_value, currency_nw = self._split_value_currency(_get("Stückelung"))
        bond_type = _get("Typ")
        currency = _get("Währung") or currency_nw

        return BondDetails(
            issuer=issuer,
            coupon_rate_percent=coupon_rate_percent,
            coupon_type=coupon_type,
            issue_date=issue_date,
            maturity_date=maturity_date,
            nominal_value=nominal_value,
            bond_type=bond_type,
            currency=currency,
        )
