"""
Asset-class-specific detail models for financial instruments.

Each model carries the static "Stammdaten" fields available on the comdirect
detail page for a given asset class.  All fields are optional because they are
populated incrementally by the parser — the ``Instrument`` model is valid with
``details=None`` until a parser fills them in.

The nine concrete classes form a Pydantic v2 discriminated union keyed on the
``asset_class`` literal field, which mirrors the string value of
``AssetClass`` (e.g. ``"Stock"``, ``"Bond"``).  This lets FastAPI / Pydantic
serialise and deserialise them without ambiguity.

Classes (one per AssetClass member):
    StockDetails       — STOCK
    BondDetails        — BOND
    ETFDetails         — ETF
    FondsDetails       — FONDS
    WarrantDetails     — WARRANT
    CertificateDetails — CERTIFICATE
    IndexDetails       — INDEX
    CommodityDetails   — COMMODITY
    CurrencyDetails    — CURRENCY

Union:
    InstrumentDetails  — Annotated discriminated union of all nine classes.
"""

from datetime import date
from typing import Annotated, Literal

from pydantic import BaseModel, Field


class StockDetails(BaseModel):
    """
    Asset-class-specific reference data for a stock (Aktie).

    Fields are sourced from the "Aktieninformationen" (Stammdaten) table on the
    comdirect instrument detail page.  Field names map directly to the German
    table headers used by comdirect.
    """

    asset_class: Literal["Stock"] = "Stock"

    security_type: str | None = Field(
        None, description="Security type (Wertpapiertyp), e.g. 'Stammaktie'"
    )
    market_segment: str | None = Field(
        None, description="Market segment (Marktsegment), e.g. 'Freiverkehr'"
    )
    sector: str | None = Field(
        None, description="Industry / sector (Branche), e.g. 'Halbleiterindustrie'"
    )
    fiscal_year_end: str | None = Field(
        None, description="Fiscal year end as DD-MM, e.g. '25-01' (Geschäftsjahr)"
    )
    market_cap: float | None = Field(
        None, description="Market capitalisation in base currency units (Marktkapital.)"
    )
    market_cap_currency: str | None = Field(
        None, description="ISO 4217 currency of the market capitalisation"
    )
    free_float: float | None = Field(
        None, description="Free-float percentage (Streubesitz), e.g. 68.46"
    )
    nominal_value: float | None = Field(
        None, description="Nominal / face value per share (Nennwert)"
    )
    nominal_value_currency: str | None = Field(
        None, description="ISO 4217 currency of the nominal value"
    )
    shares_outstanding: float | None = Field(
        None, description="Number of shares outstanding (Stücke)"
    )


class BondDetails(BaseModel):
    """
    Asset-class-specific reference data for a bond (Anleihe).

    Fields reflect the "Anleiheinformationen" / "Stammdaten" section on
    the comdirect instrument detail page.
    """

    asset_class: Literal["Bond"] = "Bond"

    issuer: str | None = Field(None, description="Bond issuer (Emittent)")
    coupon_rate_percent: float | None = Field(None, description="Annual coupon rate in % (Zinssatz)")
    coupon_type: str | None = Field(
        None, description="Coupon type: 'fixed', 'floating', or 'zero' (Zinsart)"
    )
    issue_date: date | None = Field(None, description="Issue / settlement date (Ausgabedatum)")
    maturity_date: date | None = Field(None, description="Maturity / redemption date (Fälligkeit)")
    nominal_value: float | None = Field(None, description="Face / nominal value (Nennwert)")
    bond_type: str | None = Field(
        None, description="Bond type, e.g. 'Staatsanleihe', 'Unternehmensanleihe' (Anleihetyp)"
    )
    currency: str | None = Field(None, description="Settlement currency (Währung)")


class ETFDetails(BaseModel):
    """
    Asset-class-specific reference data for an ETF.

    Fields reflect the "ETF-Informationen" / "Stammdaten" section on
    the comdirect instrument detail page.
    """

    asset_class: Literal["ETF"] = "ETF"

    tracked_index: str | None = Field(
        None, description="Index tracked by the ETF (Abgebildeter Index)"
    )
    expense_ratio_percent: float | None = Field(
        None, description="Total expense ratio in % (TER / Gesamtkostenquote)"
    )
    replication_method: str | None = Field(
        None,
        description="Replication method, e.g. 'physisch', 'synthetisch' (Replikationsmethode)",
    )
    distribution_policy: str | None = Field(
        None,
        description="Distribution policy: 'ausschüttend' or 'thesaurierend' (Ausschüttungsart)",
    )
    inception_date: date | None = Field(None, description="Fund inception / launch date (Auflagedatum)")
    fund_currency: str | None = Field(None, description="Fund base currency (Fondswährung)")
    fund_size: float | None = Field(
        None, description="Assets under management in fund currency (Fondsvermögen)"
    )


class FondsDetails(BaseModel):
    """
    Asset-class-specific reference data for a mutual fund (Fonds).

    Fields reflect the "Fondsinformationen" / "Stammdaten" section on
    the comdirect instrument detail page.
    """

    asset_class: Literal["Fund"] = "Fund"

    fund_type: str | None = Field(None, description="Fund type / category (Fondstyp)")
    fund_manager: str | None = Field(None, description="Fund manager name (Fondsmanager)")
    inception_date: date | None = Field(None, description="Fund inception / launch date (Auflagedatum)")
    distribution_policy: str | None = Field(
        None,
        description="Distribution policy: 'ausschüttend' or 'thesaurierend' (Ausschüttungsart)",
    )
    expense_ratio_percent: float | None = Field(
        None, description="Total expense ratio in % (TER / Gesamtkostenquote)"
    )
    fund_currency: str | None = Field(None, description="Fund base currency (Fondswährung)")
    fund_size: float | None = Field(
        None, description="Assets under management in fund currency (Fondsvermögen)"
    )


class WarrantDetails(BaseModel):
    """
    Asset-class-specific reference data for a warrant (Optionsschein).

    This is a compact version of ``WarrantReferenceData`` (from
    ``app.models.warrants``) suitable for embedding in the ``Instrument``
    master-data model.  The full analytics and live market data are only
    available via the dedicated ``GET /v1/warrants/{identifier}`` endpoint.
    """

    asset_class: Literal["Warrant"] = "Warrant"

    warrant_type: str | None = Field(
        None, description="Warrant type with full exercise style, e.g. 'Call (Amerikanisch)'"
    )
    underlying_name: str | None = Field(
        None, description="Full underlying instrument name from span title (Basiswert)"
    )
    underlying_link: str | None = Field(
        None, description="Absolute URL to the underlying instrument page on comdirect"
    )
    strike: float | None = Field(None, description="Strike price (Basispreis)")
    strike_currency: str | None = Field(None, description="Currency of the strike price")
    ratio: str | None = Field(
        None, description="Subscription ratio (Bezugsverhältnis), e.g. '10 : 1'"
    )
    maturity_date: date | None = Field(None, description="Maturity / expiry date (Fälligkeit)")
    last_trading_day: date | None = Field(None, description="Last trading day (Letzter Handelstag)")
    issuer: str | None = Field(
        None, description="Full issuer name from a title attribute, e.g. 'HSBC, Deutschland, Düsseldorf'"
    )


class CertificateDetails(BaseModel):
    """
    Asset-class-specific reference data for a certificate (Zertifikat).

    Fields reflect the "Zertifikatinformationen" / "Stammdaten" section on
    the comdirect instrument detail page.
    """

    asset_class: Literal["Certificate"] = "Certificate"

    certificate_type: str | None = Field(
        None,
        description="Certificate type, e.g. 'Discount', 'Bonus', 'Reverse Bonus' (Zertifikattyp)",
    )
    underlying_name: str | None = Field(None, description="Underlying instrument name (Basiswert)")
    cap: float | None = Field(None, description="Cap price level (Cap-Niveau)")
    cap_currency: str | None = Field(None, description="Currency of the cap price")
    barrier: float | None = Field(None, description="Barrier / protection level (Barriere / Absicherungsniveau)")
    barrier_currency: str | None = Field(None, description="Currency of the barrier")
    barrier_breached: bool | None = Field(
        None, description="Whether the barrier has been breached (Absich. erreicht?), Bonus certs only"
    )
    bonus_level: float | None = Field(
        None, description="Bonus payout level for Bonus certificates (Bonusniveau)"
    )
    bonus_level_currency: str | None = Field(None, description="Currency of the bonus level")
    knockout: float | None = Field(None, description="Knock-out level for Turbo/Lever certificates (Knock Out)")
    knockout_currency: str | None = Field(None, description="Currency of the knock-out level")
    strike: float | None = Field(None, description="Strike / base price for Turbo certificates (Basispreis)")
    strike_currency: str | None = Field(None, description="Currency of the strike price")
    participation_rate: float | None = Field(
        None, description="Participation rate in % (Partizipationsrate)"
    )
    maturity_date: date | None = Field(None, description="Maturity / expiry date (Fälligkeit / Laufzeitende)")
    issuer: str | None = Field(None, description="Issuing institution (Emittent)")
    currency: str | None = Field(None, description="Settlement currency (Währung)")
    subscription_ratio: str | None = Field(
        None, description="Subscription / participation ratio, e.g. '100 : 1' (Bez.-Verh.)"
    )
    region: str | None = Field(None, description="Geographic region of the underlying (Region)")
    currency_hedged: bool | None = Field(
        None, description="Whether currency risk is hedged (Währungsgesichert)"
    )


class IndexDetails(BaseModel):
    """
    Asset-class-specific reference data for a market index (Index).

    Fields reflect the "Indexinformationen" / "Stammdaten" section on
    the comdirect instrument detail page.
    """

    asset_class: Literal["Index"] = "Index"

    index_type: str | None = Field(
        None,
        description="Index type, e.g. 'Kursindex' (price) or 'Performanceindex' (total return)",
    )
    index_provider: str | None = Field(
        None, description="Index calculation provider (e.g. 'Deutsche Börse')"
    )
    country: str | None = Field(None, description="Country or region covered by the index")
    base_value: float | None = Field(None, description="Base / starting value (Basiswert)")
    base_date: date | None = Field(None, description="Base date for the index (Basisdatum)")
    num_constituents: int | None = Field(
        None, description="Number of index constituents (Anzahl Bestandteile)"
    )


class CommodityDetails(BaseModel):
    """
    Asset-class-specific reference data for a commodity (Rohstoff).

    Fields reflect the "Rohstoffinformationen" / "Stammdaten" section on
    the comdirect instrument detail page.
    """

    asset_class: Literal["Commodity"] = "Commodity"

    commodity_type: str | None = Field(
        None,
        description="Commodity category, e.g. 'Edelmetall', 'Energie', 'Agrar' (Rohstofftyp)",
    )
    unit: str | None = Field(
        None, description="Pricing unit, e.g. 'USD per troy ounce' (Einheit)"
    )
    source_exchange: str | None = Field(
        None, description="Primary exchange or price source (Herkunftsbörse)"
    )


class CurrencyDetails(BaseModel):
    """
    Asset-class-specific reference data for a currency pair (Währung).

    Fields reflect the "Währungsinformationen" / "Stammdaten" section on
    the comdirect instrument detail page.
    """

    asset_class: Literal["Currency"] = "Currency"

    base_currency: str | None = Field(
        None, description="Base currency of the pair (Basiswährung), e.g. 'EUR'"
    )
    quote_currency: str | None = Field(
        None, description="Quote / price currency (Quotierungswährung), e.g. 'USD'"
    )


# ---------------------------------------------------------------------------
# Discriminated union — used as the type for ``Instrument.details``
# ---------------------------------------------------------------------------

InstrumentDetails = Annotated[
    StockDetails
    | BondDetails
    | ETFDetails
    | FondsDetails
    | WarrantDetails
    | CertificateDetails
    | IndexDetails
    | CommodityDetails
    | CurrencyDetails,
    Field(discriminator="asset_class"),
]

