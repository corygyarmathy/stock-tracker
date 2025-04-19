import pytest
from pytest_mock import MockerFixture
from unittest.mock import MagicMock
from main import get_stock_price


# Shared fixture to mock get_yfinance_session and yf.Ticker
@pytest.fixture
def mock_yfinance(mocker: MockerFixture) -> MagicMock:
    mock_session = mocker.MagicMock()
    _ = mocker.patch("main.get_yfinance_session", return_value=mock_session)

    mock_ticker = mocker.MagicMock()
    _ = mocker.patch("main.yf.Ticker", return_value=mock_ticker)

    return mock_ticker


# Parameterized test for different fast_info["last_price"] values
@pytest.mark.parametrize(
    "last_price,expected_price,expect_error",
    [
        (150.00, 150.00, False),
        (None, None, True),
    ],
)
def test_get_stock_price_varied_prices(
    mock_yfinance: MagicMock,
    last_price: float | None,
    expected_price: float | None,
    expect_error: bool,
) -> None:
    mock_yfinance.fast_info = {"last_price": last_price}

    price, error = get_stock_price("AAPL")
    assert price == expected_price

    if expect_error:
        assert error is not None
        assert "Could not retrieve price" in error
    else:
        assert error is None


# Separate test for exception path
def test_get_stock_price_exception(mocker: MockerFixture) -> None:
    _ = mocker.patch("main.get_yfinance_session", side_effect=Exception("Boom!"))

    price, error = get_stock_price("AAPL")
    assert price is None
    assert error is not None
    assert "Error retrieving price" in error
    assert "Boom!" in error
