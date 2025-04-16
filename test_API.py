import unittest
import responses
from keys import ALPHAVANTAGE_API_KEY
from main import get_stock_price


class TestAPI(unittest.TestCase):
    @responses.activate
    def test_get_stock_price_success(self) -> None:
        """
        Tests the get_stock_price function with a successful API response.
        """
        symbol = "AAPL"
        mock_response_data: dict[str, dict[str, str]] = {
            "Global Quote": {
                "01. symbol": "AAPL",
                "02. open": "170.3000",
                "03. high": "170.9900",
                "04. low": "169.5000",
                "05. price": "170.1200",
                "06. volume": "10943500",
                "07. latest trading day": "2025-04-15",
                "08. previous close": "170.3400",
                "09. change": "-0.2200",
                "10. change percent": "-0.1292%",
            }
        }

        _ = responses.get(
            "https://www.alphavantage.co/query?function=GLOBAL_QUOTE&symbol=AAPL&apikey="
            + ALPHAVANTAGE_API_KEY,
            json=mock_response_data,
            status=200,
        )

        price, error = get_stock_price(symbol)
        assert error is None
        assert price == 170.12

    @responses.activate
    def test_get_stock_price_not_found(self) -> None:
        """
        Tests the get_stock_price function when the symbol is not found.
        """
        symbol = "INVALID"
        mock_response_data: dict[str, str] = {
            "Error Message": "Invalid API call. Please retry or visit the documentation (https://www.alphavantage.co/documentation/)."
        }

        _ = responses.get(
            "https://www.alphavantage.co/query?function=GLOBAL_QUOTE&symbol=INVALID&apikey="
            + ALPHAVANTAGE_API_KEY,
            json=mock_response_data,
            status=200,
        )

        price, error = get_stock_price(symbol)
        assert price is None
        if error is not None:
            assert "Could not retrieve price for INVALID" in error
        else:
            assert False, "Expected an error message but got None"

    @responses.activate
    def test_get_stock_price_api_error(self) -> None:
        """
        Tests the get_stock_price function when the API returns an error status.
        """
        symbol = "GOOG"
        _ = responses.get(
            "https://www.alphavantage.co/query?function=GLOBAL_QUOTE&symbol=GOOG&apikey="
            + ALPHAVANTAGE_API_KEY,
            status=401,
        )

        price, error = get_stock_price(symbol)
        assert price is None
        if error is not None:
            assert "Error during API request" in error
        else:
            assert False, "Expected an error message but got None"


if __name__ == "__main__":
    _ = unittest.main()
