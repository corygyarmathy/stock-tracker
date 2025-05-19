"""Base command class and related structures."""

import argparse
from abc import ABC, abstractmethod
from typing import Any

from stock_tracker import container
from stock_tracker.config import AppConfig
from stock_tracker.container import ServiceContainer
from stock_tracker.db import Database


class Command(ABC):
    """Base class for all CLI commands."""

    name: str  # Command name used in CLI
    help: str  # Help text shown in CLI

    def __init__(self, config: AppConfig, db: Database, container: ServiceContainer):
        """
        Initialise command with configuration, database connection, and service container.

        Args:
            config: AppConfig object
            db: Database object
            container: ServiceContainer  object
        """
        self.config: AppConfig = config
        self.db: Database = db
        self.container: ServiceContainer = container

    @classmethod
    @abstractmethod
    def setup_parser(cls, subparser) -> None:
        """
        Configure the argument parser for this command.

        Args:
            subparser: The subparser to configure
        """
        pass

    @abstractmethod
    def execute(self, args: argparse.Namespace) -> int:
        """
        Execute the command with the given arguments.

        Args:
            args: Command line arguments from argparse

        Returns:
            Exit code (0 for success, non-zero for failure)
        """
        pass


class CommandRegistry:
    """Registry of available commands."""

    _commands: dict[str, type[Command]] = {}

    @classmethod
    def register(cls, command_class: type[Command]) -> type[Command]:
        """
        Register a command class with the registry.

        Args:
            command_class: Command class to register

        Returns:
            The registered command class (for decorator use)
        """
        cls._commands[command_class.name] = command_class
        return command_class

    @classmethod
    def get_commands(cls) -> dict[str, type[Command]]:
        """
        Get all registered commands.

        Returns:
            Dictionary mapping command names to command classes
        """
        return cls._commands.copy()
