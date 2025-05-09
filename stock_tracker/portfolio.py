# Logic for capital gains, dividends


def calculate_order_capital_gains(order: dict[str, str], current_price: float) -> float:
    # Basic gain calculation
    # Diff between order price and current price
    # date,exchange,ticker,quantity,price_paid
    order_price: float = float(order["price_paid"]) * float(order["quantity"])
    current_total_price: float = current_price * float(order["quantity"])
    return current_total_price - order_price
