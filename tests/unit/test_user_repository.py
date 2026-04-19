"""
Unit tests for UserRepository.

All MongoDB interactions are mocked — no real Atlas connection required.
"""

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.models.users import Roles, UserStoreDB
from app.repositories.users import UserRepository


def _make_user(**overrides) -> UserStoreDB:
    defaults = dict(
        first_name="Alice",
        last_name="Smith",
        username="alice",
        role=Roles.REGULAR,
        email="alice@example.com",
        hashed_password="hashed_secret",
        created_at=datetime(2024, 1, 1),
        changed_at=datetime(2024, 1, 1),
    )
    defaults.update(overrides)
    return UserStoreDB(**defaults)


def _make_repo(collection_mock: MagicMock) -> UserRepository:
    repo = UserRepository()
    with patch("app.repositories.users.get_collection", return_value=collection_mock):
        _ = repo.collection  # trigger property to cache the mock
    return repo


@pytest.fixture
def collection():
    col = MagicMock()
    col.find_one = AsyncMock(return_value=None)
    col.insert_one = AsyncMock(return_value=MagicMock(inserted_id="fake_id"))
    col.update_one = AsyncMock(return_value=MagicMock(modified_count=1))
    col.delete_one = AsyncMock(return_value=MagicMock(deleted_count=1))
    return col


@pytest.fixture
def repo(collection):
    r = UserRepository()
    with patch("app.repositories.users.get_collection", return_value=collection):
        _ = r.collection
    return r


# --- find_by_username ---

async def test_find_by_username_returns_user(repo, collection):
    user = _make_user()
    collection.find_one.return_value = user.model_dump()

    result = await repo.find_by_username("alice")

    collection.find_one.assert_awaited_once_with({"username": "alice"})
    assert result is not None
    assert result.username == "alice"


async def test_find_by_username_not_found(repo, collection):
    collection.find_one.return_value = None

    result = await repo.find_by_username("ghost")

    assert result is None


# --- find_by_email ---

async def test_find_by_email_returns_user(repo, collection):
    user = _make_user()
    collection.find_one.return_value = user.model_dump()

    result = await repo.find_by_email("alice@example.com")

    assert result is not None
    assert result.email == "alice@example.com"


# --- create ---

async def test_create_inserts_user(repo, collection):
    collection.find_one.return_value = None  # no duplicate
    user = _make_user()

    result = await repo.create(user)

    collection.insert_one.assert_awaited_once()
    assert result.username == "alice"


async def test_create_raises_on_duplicate(repo, collection):
    user = _make_user()
    collection.find_one.return_value = user.model_dump()  # simulate existing

    with pytest.raises(ValueError, match="already exists"):
        await repo.create(user)


# --- update ---

async def test_update_returns_true_on_success(repo, collection):
    result = await repo.update("alice", {"is_active": True})
    assert result is True


async def test_update_returns_false_when_no_match(repo, collection):
    collection.update_one.return_value = MagicMock(modified_count=0)
    result = await repo.update("ghost", {"is_active": True})
    assert result is False


# --- delete ---

async def test_delete_returns_true_on_success(repo, collection):
    result = await repo.delete("alice")
    assert result is True


async def test_delete_returns_false_when_not_found(repo, collection):
    collection.delete_one.return_value = MagicMock(deleted_count=0)
    result = await repo.delete("ghost")
    assert result is False
