"""
Unit tests for app.core.database — guard logic only.

connect_to_database / close_database_connection require a live MongoDB connection
and belong in integration tests.  What can be verified here is the module-level
guard in get_database() and the Collection name constants.
"""

import pytest

import app.core.database as db_module
from app.core.database import Collections, get_collection, get_database

# ---------------------------------------------------------------------------
# get_database — RuntimeError when uninitialised
# ---------------------------------------------------------------------------

class TestGetDatabase:
    def setup_method(self):
        """Ensure _database is None before each test."""
        self._original = db_module._database
        db_module._database = None

    def teardown_method(self):
        """Restore original state so other tests are unaffected."""
        db_module._database = self._original

    def test_raises_runtime_error_when_not_connected(self):
        with pytest.raises(RuntimeError, match="Database connection not initialized"):
            get_database()

    def test_returns_value_when_set(self):
        fake_db = object()
        db_module._database = fake_db
        assert get_database() is fake_db


# ---------------------------------------------------------------------------
# get_collection — delegates to get_database
# ---------------------------------------------------------------------------

class TestGetCollection:
    def setup_method(self):
        self._original = db_module._database
        db_module._database = None

    def teardown_method(self):
        db_module._database = self._original

    def test_raises_when_not_connected(self):
        with pytest.raises(RuntimeError):
            get_collection("instruments")

    def test_returns_collection_from_database(self):
        class FakeDB:
            def __getitem__(self, name):
                return f"collection:{name}"

        db_module._database = FakeDB()
        assert get_collection("instruments") == "collection:instruments"
        assert get_collection("depots") == "collection:depots"


# ---------------------------------------------------------------------------
# Collections constants
# ---------------------------------------------------------------------------

class TestCollections:
    def test_instruments_constant(self):
        assert Collections.INSTRUMENTS == "instruments"

    def test_depots_constant(self):
        assert Collections.DEPOTS == "depots"

    def test_quotes_constant(self):
        assert Collections.QUOTES == "quotes"

    def test_history_constant(self):
        assert Collections.HISTORY == "history"

    def test_users_constant(self):
        assert Collections.USERS == "users"
