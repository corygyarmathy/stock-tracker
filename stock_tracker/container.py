"""
Service container for dependency injection.

This module defines a container that manages the creation and lifecycle of
service objects, repository objects, and other application components.
"""

import logging
from typing import TypeVar, cast

from stock_tracker.config import AppConfig
from stock_tracker.db import Database
from stock_tracker.repositories.corporate_actions_repository import CorporateActionRepository
from stock_tracker.repositories.dividend_repository import DividendRepository
from stock_tracker.repositories.fx_rate_repository import FxRateRepository
from stock_tracker.repositories.order_repository import OrderRepository
from stock_tracker.repositories.stock_info_repository import StockInfoRepository
from stock_tracker.repositories.stock_repository import StockRepository
from stock_tracker.services.dividend_service import DividendService
from stock_tracker.services.portfolio_service import PortfolioService

logger = logging.getLogger(__name__)

T = TypeVar("T")


class ServiceContainer:
    """
    Container for application services and repositories.

    This class is responsible for creating and providing access to various
    application components, ensuring proper dependency injection and lifecycle
    management.
    """

    def __init__(self, config: AppConfig, db: Database):
        """
        Initialise the service container.

        Args:
            config: Application configuration
            db: Database connection
        """
        self.config = config
        self.db = db
        self._repositories: dict[type, object] = {}
        self._services: dict[type, object] = {}

        # Initialise repositories
        self._init_repositories()

        # Initialise services
        self._init_services()

    def _init_repositories(self) -> None:
        """Initialise all repositories."""
        self._repositories[StockRepository] = StockRepository(self.db)
        self._repositories[StockInfoRepository] = StockInfoRepository(self.db)
        self._repositories[OrderRepository] = OrderRepository(self.db)
        self._repositories[DividendRepository] = DividendRepository(self.db)
        self._repositories[FxRateRepository] = FxRateRepository(self.db)
        self._repositories[CorporateActionRepository] = CorporateActionRepository(self.db)

    def _init_services(self) -> None:
        """Initialise all services."""
        dividend_repo: DividendRepository = self.get_repository(DividendRepository)
        self._services[DividendService] = DividendService(dividend_repo)

        # Portfolio service depends on multiple repositories
        stock_repo: StockRepository = self.get_repository(StockRepository)
        order_repo: OrderRepository = self.get_repository(OrderRepository)
        stock_info_repo: StockInfoRepository = self.get_repository(StockInfoRepository)
        self._services[PortfolioService] = PortfolioService(
            stock_repo, order_repo, stock_info_repo, dividend_repo
        )

    def get_repository(self, repo_type: type[T]) -> T:
        """
        Get a repository instance by type.

        Args:
            repo_type: Repository class

        Returns:
            Instance of the requested repository

        Raises:
            KeyError: If repository type is not registered
        """
        if repo_type not in self._repositories:
            raise KeyError(f"Repository {repo_type.__name__} not registered")

        return cast(T, self._repositories[repo_type])

    def get_service(self, service_type: type[T]) -> T:
        """
        Get a service instance by type.

        Args:
            service_type: Service class

        Returns:
            Instance of the requested service

        Raises:
            KeyError: If service type is not registered
        """
        if service_type not in self._services:
            raise KeyError(f"Service {service_type.__name__} not registered")

        return cast(T, self._services[service_type])
