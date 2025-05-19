"""Report command implementation."""

import argparse
import logging
from typing import override

from stock_tracker.commands.base import Command, CommandRegistry
from stock_tracker.config import AppConfig
from stock_tracker.container import ServiceContainer
from stock_tracker.db import Database
from stock_tracker.display import display_dividend_report, display_performance
from stock_tracker.models import PortfolioPerformance
from stock_tracker.services.portfolio_service import PortfolioService

logger = logging.getLogger(__name__)


@CommandRegistry.register
class ReportCommand(Command):
    """Command to generate reports."""

    name: str = "report"
    help: str = "Generate reports"

    def __init__(self, config: AppConfig, db: Database, container: ServiceContainer):
        """Initialise the command with config, database connection, and service container."""
        super().__init__(config, db, container)

    @override
    @classmethod
    def setup_parser(cls, subparser) -> None:
        """Configure the argument parser for the report command."""
        parser: argparse.ArgumentParser = subparser.add_parser(cls.name, help=cls.help)
        _ = parser.add_argument(
            "type", choices=["performance", "dividends", "gains"], help="Type of report to generate"
        )

    @override
    def execute(self, args: argparse.Namespace) -> int:
        """Execute the report command."""
        report_type: str = str(args.type)

        # Get the portfolio service from the container
        portfolio_service: PortfolioService = self.container.get_service(PortfolioService)

        try:
            # Portfolio performance report
            if report_type == "performance":
                print("Generating portfolio performance report...")
                performance: PortfolioPerformance = (
                    portfolio_service.calculate_portfolio_performance()
                )
                display_performance(performance)

            # Dividend report
            elif report_type == "dividends":
                print("Generating dividend report...")
                dividend_data = portfolio_service.calculate_dividend_report()
                display_dividend_report(dividend_data)

            # Capital gains report
            elif report_type == "gains":
                print("Generating capital gains report...")
                # TODO: Implement capital gains report
                print("Capital gains report not yet implemented.")

            return 0
        except Exception as e:
            logger.error(f"Error generating report: {e}", exc_info=True)
            print(f"Error: Failed to generate {report_type} report: {e}")
            return 1
