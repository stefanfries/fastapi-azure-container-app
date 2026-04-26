"""Unit tests for app.routers.warrants — GET /v1/warrants/ and GET /v1/warrants/{id}."""

from unittest.mock import AsyncMock, patch

from app.models.warrants import (
    WarrantAnalytics,
    WarrantDetailResponse,
    WarrantFinderResponse,
    WarrantMarketData,
    WarrantReferenceData,
)


def _finder_response() -> WarrantFinderResponse:
    return WarrantFinderResponse(url="https://example.com", count=0, results=[])


def _detail_response() -> WarrantDetailResponse:
    return WarrantDetailResponse(
        isin="DE000SB6B1Y3",
        wkn="SB6B1Y",
        reference_data=WarrantReferenceData(),
        market_data=WarrantMarketData(),
        analytics=WarrantAnalytics(),
    )


class TestGetWarrants:
    def test_returns_200_with_finder_result(self, client):
        with patch(
            "app.routers.warrants.fetch_warrants",
            new_callable=AsyncMock,
            return_value=_finder_response(),
        ):
            response = client.get(
                "/v1/warrants/?underlying=918422",
                headers={"X-API-Key": "test"},
            )
        assert response.status_code == 200
        body = response.json()
        assert body["count"] == 0
        assert body["results"] == []


class TestGetWarrantDetail:
    def test_returns_200_with_detail(self, client):
        with patch(
            "app.routers.warrants.parse_warrant_detail",
            new_callable=AsyncMock,
            return_value=_detail_response(),
        ):
            response = client.get(
                "/v1/warrants/SB6B1Y",
                headers={"X-API-Key": "test"},
            )
        assert response.status_code == 200
        body = response.json()
        assert body["wkn"] == "SB6B1Y"
        assert body["isin"] == "DE000SB6B1Y3"
