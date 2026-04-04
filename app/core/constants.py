"""
Application-wide constants for asset class mappings and comdirect URL paths.

Defines:
    standard_asset_classes: Asset classes whose detail pages follow the standard HTML layout.
    special_asset_classes: Asset classes (indices, commodities, currencies) with a different layout.
    asset_classes: Combined list of all supported asset classes.
    asset_class_to_asset_class_identifier_map: Maps AssetClass enum values to comdirect URL path segments.
    asset_class_identifier_to_asset_class_map: Reverse lookup of the map above.
    ASSET_CLASS_DETAILS_PATH: Maps AssetClass enum values to comdirect detail-page URL paths.
    BASE_URL: Root URL of the comdirect website.
    SEARCH_PATH: Relative path for the comdirect instrument search endpoint.
    HISTORY_PATH: Relative path for the comdirect historical price CSV download endpoint.
"""

from app.models.instruments import AssetClass

standard_asset_classes = [
    AssetClass.STOCK,
    AssetClass.BOND,
    AssetClass.ETF,
    AssetClass.FONDS,
    AssetClass.WARRANT,
    AssetClass.CERTIFICATE,
]

special_asset_classes = [
    AssetClass.INDEX,
    AssetClass.COMMODITY,
    AssetClass.CURRENCY,
]

asset_classes = standard_asset_classes + special_asset_classes

asset_class_to_asset_class_identifier_map = {
    AssetClass.STOCK: "aktien",
    AssetClass.BOND: "anleihen",
    AssetClass.ETF: "etfs",
    AssetClass.FONDS: "fonds",
    AssetClass.WARRANT: "optionsscheine",
    AssetClass.CERTIFICATE: "zertifikate",
    AssetClass.INDEX: "indizes",
    AssetClass.COMMODITY: "rohstoffe",
    AssetClass.CURRENCY: "waehrungen",
}

asset_class_identifier_to_asset_class_map = {
    v: k for k, v in asset_class_to_asset_class_identifier_map.items()
}

ASSET_CLASS_DETAILS_PATH = {
    AssetClass.STOCK: "/inf/aktien/detail/uebersicht.html",
    AssetClass.BOND: "/inf/anleihen/detail/uebersicht.html",
    AssetClass.ETF: "/inf/etfs/detail/uebersicht.html",
    AssetClass.FONDS: "/inf/fonds/detail/uebersicht.html",
    AssetClass.WARRANT: "/inf/optionsscheine/detail/uebersicht/uebersicht.html",
    AssetClass.CERTIFICATE: "/inf/zertifikate/detail/uebersicht.html",
    AssetClass.INDEX: "/inf/indizes/detail/uebersicht.html",
    AssetClass.COMMODITY: "/inf/rohstoffe/detail/uebersicht.html",
    AssetClass.CURRENCY: "/inf/waehrungen/detail/uebersicht.html",
}

BASE_URL = "https://www.comdirect.de"
SEARCH_PATH = "/inf/search/all.html"
HISTORY_PATH = "/inf/kursdaten/historic.csv"
