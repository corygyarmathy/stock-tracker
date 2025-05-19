from stock_tracker.models import (
    Dividend,
    PortfolioPerformance,
    Stock,
    StockInfo,
    StockOrder,
    StockPerformance,
)
from stock_tracker.repositories.dividend_repository import DividendRepository
from stock_tracker.repositories.order_repository import OrderRepository
from stock_tracker.repositories.stock_info_repository import StockInfoRepository
from stock_tracker.repositories.stock_repository import StockRepository


class PortfolioService:
    """Service for portfolio-level operations and calculations."""

    def __init__(
        self,
        stock_repo: StockRepository,
        order_repo: OrderRepository,
        stock_info_repo: StockInfoRepository,
        dividend_repo: DividendRepository,
    ):
        self.stock_repo = stock_repo
        self.order_repo = order_repo
        self.stock_info_repo = stock_info_repo
        self.dividend_repo = dividend_repo

    def calculate_portfolio_performance(self) -> PortfolioPerformance:
        """Calculate the performance of the entire portfolio."""
        # Get all stocks
        all_stocks: list[Stock] = self.stock_repo.get_all()

        stock_performances = []
        total_cost = 0.0
        total_current_value = 0.0
        total_dividends = 0.0

        for stock in all_stocks:
            if not stock.id:
                continue

            # Get orders for this stock
            orders = self.order_repo.get_orders_for_stock(stock.id)
            if not orders:
                continue

            # Get current stock info
            stock_info = self.stock_info_repo.get_by_stock_id(stock.id)
            if not stock_info:
                continue

            # Calculate stock performance
            performance = self._calculate_stock_performance(stock, orders, stock_info)
            stock_performances.append(performance)

            # Update portfolio totals
            total_cost += performance.total_cost
            total_current_value += performance.current_value
            total_dividends += performance.dividends_received

        # Calculate overall portfolio performance
        capital_gain = total_current_value - total_cost
        capital_gain_percentage = (capital_gain / total_cost * 100) if total_cost > 0 else 0
        total_return = capital_gain + total_dividends
        total_return_percentage = (total_return / total_cost * 100) if total_cost > 0 else 0

        return PortfolioPerformance(
            stocks=stock_performances,
            total_cost=total_cost,
            current_value=total_current_value,
            capital_gain=capital_gain,
            capital_gain_percentage=capital_gain_percentage,
            dividends_received=total_dividends,
            total_return=total_return,
            total_return_percentage=total_return_percentage,
        )

    def calculate_dividend_report(self) -> list[dict[str, str | int | float]]:
        """Calculate dividend report data for all stocks.

        Returns:
            A list of dictionaries containing dividend report data for each stock
        """
        dividend_data = []

        # Get all stocks
        all_stocks: list[Stock] = self.stock_repo.get_all()

        for stock in all_stocks:
            if not stock.id:
                continue

            # Get dividends for this stock
            dividends: list[Dividend] = self.dividend_repo.get_dividends_for_stock(stock.id)
            if not dividends:
                continue

            # Calculate total dividends and find the most recent ex-date
            stock_total = sum(d.amount for d in dividends)
            last_date = max(d.ex_date for d in dividends)

            # Add stock's dividend data to the report
            dividend_data.append(
                {
                    "stock": stock,
                    "total_amount": stock_total,
                    "last_ex_date": last_date,
                    "dividends_count": len(dividends),
                }
            )

        return dividend_data

    def _calculate_stock_performance(
        self, stock: Stock, orders: list[StockOrder], stock_info: StockInfo
    ) -> StockPerformance:
        """Calculate performance metrics for a single stock."""
        total_shares = sum(order.quantity for order in orders)
        total_cost = sum(order.quantity * order.price_paid + order.fee for order in orders)
        current_value = total_shares * stock_info.current_price

        capital_gain = current_value - total_cost
        capital_gain_percentage = (capital_gain / total_cost * 100) if total_cost > 0 else 0.0

        # Calculate dividends received
        dividends_received = 0.0
        if stock.id:
            dividends_received = self.dividend_repo.calculate_dividends_received(stock.id)

        total_return = capital_gain + dividends_received
        total_return_percentage = (total_return / total_cost * 100) if total_cost > 0 else 0.0

        return StockPerformance(
            stock_id=stock.id if stock.id else -1,
            ticker=stock.ticker,
            exchange=stock.exchange,
            name=stock.name if stock.name else "",
            total_shares=total_shares,
            total_cost=total_cost,
            current_value=current_value,
            capital_gain=capital_gain,
            capital_gain_percentage=capital_gain_percentage,
            dividends_received=dividends_received,
            total_return=total_return,
            total_return_percentage=total_return_percentage,
        )
