import logging

from stock_tracker.models import PortfolioPerformance, StockPerformance

logger = logging.getLogger(__name__)


def display_performance(performance: PortfolioPerformance) -> None:
    """
    Display portfolio performance metrics in a formatted ASCII table.

    Args:
        performance: Portfolio performance object to display
    """
    if not performance or not performance.stocks:
        print("No portfolio data to display.")
        return

    # Print header
    print("\n╔════════════════════════════════════════════════════════════════════════════════╗")
    print("║                              PORTFOLIO SUMMARY                                 ║")
    print("╠════════════╦═══════════╦═══════════╦════════════╦═══════════════╦═════════════╣")
    print("║ Metric     ║ Value ($) ║   % ROI   ║ Breakdown  ║ Asset Count   ║ % Portfolio ║")
    print("╠════════════╬═══════════╬═══════════╬════════════╬═══════════════╬═════════════╣")

    # Print portfolio level metrics
    print(
        f"║ Total Cost ║ {performance.total_cost:9.2f} ║           ║            ║ {len(performance.stocks):13} ║ 100.00%    ║"
    )
    print(
        f"║ Current    ║ {performance.current_value:9.2f} ║           ║            ║               ║             ║"
    )
    print(
        f"║ Cap. Gains ║ {performance.capital_gain:9.2f} ║ {performance.capital_gain_percentage:8.2f}% ║            ║               ║             ║"
    )
    print(
        f"║ Dividends  ║ {performance.dividends_received:9.2f} ║           ║            ║               ║             ║"
    )
    print(
        f"║ TOTAL ROI  ║ {performance.total_return:9.2f} ║ {performance.total_return_percentage:8.2f}% ║            ║               ║             ║"
    )

    print("╠════════════╩═══════════╩═══════════╩════════════╩═══════════════╩═════════════╣")
    print("║                               STOCK BREAKDOWN                                  ║")
    print("╠═════════════╦═══════════╦═════════╦═══════════╦═══════════╦═══════════╦═══════╣")
    print("║ Stock       ║ Shares    ║ Cost    ║ Value     ║ Gain/Loss ║ Return %  ║ Div $ ║")
    print("╠═════════════╬═══════════╬═════════╬═══════════╬═══════════╬═══════════╬═══════╣")

    # Sort stocks by value (descending)
    sorted_stocks = sorted(performance.stocks, key=lambda x: x.current_value, reverse=True)

    # Print each stock
    for stock in sorted_stocks:
        ticker_display = f"{stock.ticker}.{stock.exchange}"
        if len(ticker_display) > 11:
            ticker_display = ticker_display[:10] + "…"

        print(
            f"║ {ticker_display:<11} ║ "
            f"{stock.total_shares:9.2f} ║ "
            f"{stock.total_cost:7.2f} ║ "
            f"{stock.current_value:9.2f} ║ "
            f"{stock.capital_gain:9.2f} ║ "
            f"{stock.total_return_percentage:9.2f}% ║ "
            f"{stock.dividends_received:5.2f} ║"
        )

    print("╚═════════════╩═══════════╩═════════╩═══════════╩═══════════╩═══════════╩═══════╝")

    # Provide a text summary of the results
    print("\nSUMMARY:")
    print(f"Your portfolio currently has a total value of ${performance.current_value:.2f}.")
    print(
        f"Overall return: ${performance.total_return:.2f} ({performance.total_return_percentage:.2f}%)."
    )

    if performance.total_return > 0:
        print("Congratulations! Your investments are performing well.")
    else:
        print("Your portfolio is currently at a loss. Consider reviewing your investment strategy.")

    # Print top and bottom performers
    if len(sorted_stocks) >= 3:
        print("\nTOP PERFORMERS:")
        top_stocks = sorted(sorted_stocks, key=lambda x: x.total_return_percentage, reverse=True)[
            :3
        ]
        for i, stock in enumerate(top_stocks, 1):
            print(f"{i}. {stock.ticker}.{stock.exchange}: {stock.total_return_percentage:.2f}%")

        print("\nBOTTOM PERFORMERS:")
        bottom_stocks = sorted(sorted_stocks, key=lambda x: x.total_return_percentage)[:3]
        for i, stock in enumerate(bottom_stocks, 1):
            print(f"{i}. {stock.ticker}.{stock.exchange}: {stock.total_return_percentage:.2f}%")
