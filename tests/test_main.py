"""
Test the main module.
"""

from unittest.mock import patch

import pytest

from app.main import main


@patch("uvicorn.run")
def test_main(mock_run) -> None:
    """
    Test the main function to ensure that uvicorn.run is called with the correct parameters.

    Args:
        mock_run (Mock): A mock object for the uvicorn.run function.

    Asserts:
        The uvicorn.run function is called once with the specified arguments:
        - "app.main:app"
        - host="0.0.0.0"
        - port=8080
        - reload=True
    """

    main()
    mock_run.assert_called_once_with(
        "app.main:app", host="0.0.0.0", port=8080, reload=True
    )


def test_main_no_exception() -> None:
    """
    Test the main function to ensure it does not raise an exception and calls uvicorn.run with the correct parameters.

    Asserts:
        The uvicorn.run function is called once with the specified arguments:
        - "app.main:app"
        - host="0.0.0.0"
        - port=8080
        - reload=False
    """
    with patch("uvicorn.run") as mock_run:
        try:
            main()
        except RuntimeError as e:
            pytest.fail(f"main() raised an exception: {e}")
        mock_run.assert_called_once_with(
            "app.main:app", host="0.0.0.0", port=8080, reload=True
        )
