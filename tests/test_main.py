"""
Test the main module.
"""

from app.main import main


def test_main() -> None:
    assert main() is None
