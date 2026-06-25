"""Unit tests for app.services.log_level_manager."""

import logging
from unittest.mock import patch

from app.services.log_level_manager import get_runtime_log_level


class TestGetRuntimeLogLevel:
    def test_returns_effective_level_name(self):
        with patch("app.services.log_level_manager.logger.getEffectiveLevel", return_value=logging.WARNING):
            assert get_runtime_log_level() == "WARNING"
