from stock_tracker.main import get_stock_price
import pytest
from pytest_mock import MockerFixture
from unittest.mock import MagicMock


# Fixture 1: Mock just the session
@pytest.fixture
def mock_yfinance_session(mocker: MockerFixture) -> MagicMock:
    mock_session = mocker.MagicMock()
    _ = mocker.patch("stock_tracker.main.get_yfinance_session", return_value=mock_session)
    return mock_session


# Fixture 2: Mock just the Ticker
@pytest.fixture
def mock_yfinance_ticker(mocker: MockerFixture) -> MagicMock:
    mock_ticker = mocker.MagicMock()
    _ = mocker.patch("stock_tracker.main.yf.Ticker", return_value=mock_ticker)
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
    mock_yfinance_session: MagicMock,
    mock_yfinance_ticker: MagicMock,
    last_price: float | None,
    expected_price: float | None,
    expect_error: bool,
) -> None:
    mock_yfinance_ticker.fast_info = {"last_price": last_price}

    price, error = get_stock_price("AAPL", mock_yfinance_session)
    assert price == expected_price

    if expect_error:
        assert error is not None
        assert "Could not retrieve price" in error
    else:
        assert error is None


# Separate test for exception path
def test_get_stock_price_exception(
    mocker: MockerFixture,
    mock_yfinance_ticker: MagicMock,
    mock_yfinance_session: MagicMock,
) -> None:
    _ = mocker.patch("main.get_yfinance_session", side_effect=Exception("Boom!"))

    price, error = get_stock_price("AAPL", mock_yfinance_session)
    assert price is None
    assert error is not None
    assert "Error retrieving price" in error
    assert "Boom!" in error
