"""
Unit tests for app.models.instrument_details discriminated union.

Covers:
- Discriminator literal on each concrete model
- Round-trip serialisation via model_dump()
- Optional fields defaulting to None
"""

from datetime import date

import pytest

from app.models.instrument_details import (
    BondDetails,
    CertificateDetails,
    CommodityDetails,
    CurrencyDetails,
    ETFDetails,
    FondsDetails,
    IndexDetails,
    StockDetails,
    WarrantDetails,
)


class TestInstrumentDetailsUnion:
    """Ensure each concrete model carries the correct discriminator literal."""

    @pytest.mark.parametrize("model,expected", [
        (StockDetails(),       "Stock"),
        (BondDetails(),        "Bond"),
        (ETFDetails(),         "ETF"),
        (FondsDetails(),       "Fund"),
        (WarrantDetails(),     "Warrant"),
        (CertificateDetails(), "Certificate"),
        (IndexDetails(),       "Index"),
        (CommodityDetails(),   "Commodity"),
        (CurrencyDetails(),    "Currency"),
    ])
    def test_discriminator_value(self, model, expected):
        assert model.asset_class == expected

    def test_stock_details_serialises_to_dict(self):
        details = StockDetails(sector="Halbleiterindustrie", free_float=68.46)
        data = details.model_dump()
        assert data["asset_class"] == "Stock"
        assert data["sector"] == "Halbleiterindustrie"
        assert data["free_float"] == pytest.approx(68.46)

    def test_bond_details_serialises_to_dict(self):
        details = BondDetails(issuer="Bund", coupon_rate_percent=1.5, maturity_date=date(2030, 1, 15))
        data = details.model_dump()
        assert data["asset_class"] == "Bond"
        assert data["coupon_rate_percent"] == pytest.approx(1.5)
        assert data["maturity_date"] == date(2030, 1, 15)

    def test_optional_fields_default_to_none(self):
        details = ETFDetails()
        assert details.tracked_index is None
        assert details.expense_ratio_percent is None
