from unittest.mock import MagicMock

import pytest
from pytest_mock import MockerFixture

from stock_tracker.yfinance_api import get_stock_price


# # Mock the ticker
# @pytest.fixture
# def mock_yfinance_ticker(mocker: MockerFixture) -> MagicMock:
#     mock_ticker = mocker.MagicMock()
#     _ = mocker.patch("stock_tracker.main.yf.Ticker", return_value=mock_ticker)
#     return mock_ticker
#
#
# # Parameterised test for different fast_info["last_price"] values
# @pytest.mark.parametrize(
#     "last_price,expected_price,expect_error",
#     [
#         (150.00, 150.00, False),
#         (None, None, True),
#     ],
# )
# def test_get_stock_price_varied_prices(
#     mock_yfinance_session: MagicMock,
#     mock_yfinance_ticker: MagicMock,
#     last_price: float | None,
#     expected_price: float | None,
#     expect_error: bool,
# ) -> None:
#     import stock_tracker.main
#
#     print("Using main.py at:", stock_tracker.main.__file__)
#     mock_yfinance_ticker.fast_info = {"last_price": last_price}
#
#     if expect_error:
#         with pytest.raises(ValueError):
#             _ = get_stock_price("AAPL", mock_yfinance_session)
#     else:
#         price: float = get_stock_price("AAPL", mock_yfinance_session)
#         assert price == expected_price


# Separate test for exception path
# def test_get_stock_price_exception(
#     mocker: MockerFixture,
#     mock_yfinance_ticker: MagicMock,
#     mock_yfinance_session: MagicMock,
# ) -> None:
#     _ = mocker.patch("main.get_yfinance_session")
#
#     price = get_stock_price("AAPL", mock_yfinance_session)
#     assert price is None
#     assert error is not None
#     assert "Error retrieving price" in error
#     assert "Boom!" in error
