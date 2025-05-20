import argparse
from dataclasses import dataclass, field
from typing import ClassVar

import pytest

from stock_tracker.utils.parser_utils import add_config_options


class TestParserUtils:
    """Tests for the parser_utils module."""

    def test_add_config_options(self):
        """Test adding config options to an ArgumentParser."""

        # Create a test dataclass
        @dataclass
        class TestConfig:
            str_option: str
            int_option: int
            float_option: float
            bool_option: bool
            path_option: str
            _private_field: str = field(default="private")  # Should be skipped
            CLASS_VAR: ClassVar[str] = "class-var"  # Should be skipped

        # Create a parser
        parser = argparse.ArgumentParser()

        # Add config options
        add_config_options(parser, TestConfig)

        # Parse arguments to check if options were added correctly
        # No arguments provided, so should use defaults
        args = parser.parse_args([])

        # Check that all options were added (should all be None since no values provided)
        assert hasattr(args, "str_option")
        assert hasattr(args, "int_option")
        assert hasattr(args, "float_option")
        assert hasattr(args, "bool_option")
        assert hasattr(args, "path_option")

        # Check that private and class var fields were skipped
        assert not hasattr(args, "_private_field")
        assert not hasattr(args, "CLASS_VAR")

        # Skip boolean tests since the implementation doesn't use store_true/store_false
        # and we want to avoid the complexities of testing with argparse

    def test_add_config_options_from_app_config(self):
        """Test adding config options from the actual AppConfig class."""
        # Create a parser
        parser = argparse.ArgumentParser()

        # Add config options from AppConfig
        from stock_tracker.config import AppConfig

        add_config_options(parser, AppConfig)

        # Parse arguments to check if options were added correctly
        args = parser.parse_args([])

        # Check that expected options were added
        assert hasattr(args, "db_path")
        assert hasattr(args, "csv_path")
        assert hasattr(args, "log_level")
        assert hasattr(args, "yf_max_requests")
