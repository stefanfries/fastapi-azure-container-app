"""
Test the main module.
"""

from unittest.mock import patch

import pytest

from app.main import main


@patch("uvicorn.run")
def test_main(mock_run) -> None:
    main()
    mock_run.assert_called_once_with(
        "app.main:app", host="0.0.0.0", port=8080, reload=True
    )


def test_main_no_exception() -> None:
    with patch("uvicorn.run") as mock_run:
        try:
            main()
        except Exception as e:
            pytest.fail(f"main() raised an exception: {e}")
        mock_run.assert_called_once_with(
            "app.main:app", host="0.0.0.0", port=8080, reload=True
        )
