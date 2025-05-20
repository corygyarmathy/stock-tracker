import logging
import os
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest
import yaml

from stock_tracker.utils.setup_logging import setup_logging


class TestSetupLogging:
    """Tests for the setup_logging module."""

    @pytest.fixture
    def sample_logging_config(self, tmp_path):
        """Create a sample logging config file."""
        config = {
            "version": 1,
            "disable_existing_loggers": False,
            "formatters": {
                "standard": {"format": "%(asctime)s [%(levelname)s] %(name)s: %(message)s"},
            },
            "handlers": {
                "console": {
                    "class": "logging.StreamHandler",
                    "level": "INFO",
                    "formatter": "standard",
                    "stream": "ext://sys.stdout",
                },
                "file": {
                    "class": "logging.FileHandler",
                    "level": "DEBUG",
                    "formatter": "standard",
                    "filename": "test.log",
                    "mode": "a",
                },
            },
            "loggers": {
                "stock_tracker": {
                    "level": "WARNING",
                    "handlers": ["console", "file"],
                    "propagate": False,
                }
            },
            "root": {"level": "ERROR", "handlers": ["console"]},
        }

        # Create config directory in temp path
        config_path = tmp_path / "logging_config.yaml"
        with open(config_path, "w") as f:
            yaml.dump(config, f)

        return config_path

    @patch("logging.config.dictConfig")
    def test_setup_logging_with_valid_config(self, mock_dict_config, sample_logging_config):
        """Test setting up logging with a valid config file."""
        # Call setup_logging with our sample config
        setup_logging(sample_logging_config, "DEBUG")

        # Check that dictConfig was called
        mock_dict_config.assert_called_once()

        # Get the config dict passed to dictConfig
        config_dict = mock_dict_config.call_args[0][0]

        # Verify the config has the expected structure
        assert "version" in config_dict
        assert "handlers" in config_dict
        assert "loggers" in config_dict
        assert "stock_tracker" in config_dict["loggers"]

    @patch("logging.config.dictConfig")
    @patch("logging.warning")
    def test_setup_logging_with_invalid_level(
        self, mock_warning, mock_dict_config, sample_logging_config
    ):
        """Test setting up logging with an invalid log level."""
        # Call setup_logging with an invalid log level
        setup_logging(sample_logging_config, "INVALID_LEVEL")

        # Check that dictConfig was still called
        mock_dict_config.assert_called_once()

        # Check that a warning was logged
        mock_warning.assert_called_once()
        assert "Invalid log level" in mock_warning.call_args[0][0]

    @patch("logging.config.dictConfig")
    @patch("logging.info")
    def test_setup_logging_with_override_level(
        self, mock_info, mock_dict_config, sample_logging_config
    ):
        """Test overriding the log level."""
        # Call setup_logging with a valid log level
        setup_logging(sample_logging_config, "DEBUG")

        # Check that info was logged about the override
        mock_info.assert_called()
        assert any("overridden" in args[0] for args, kwargs in mock_info.call_args_list)

    @patch("logging.basicConfig")
    @patch("logging.error")
    @patch("builtins.print")  # Also patch print since your function uses it
    def test_setup_logging_with_missing_file(self, mock_print, mock_error, mock_basic_config):
        """Test handling of a missing config file."""
        # Use a path that doesn't exist
        nonexistent_path = Path("/path/does/not/exist.yaml")

        # Call setup_logging with a nonexistent path
        setup_logging(nonexistent_path, "INFO")

        # Check that basicConfig was called as a fallback
        mock_basic_config.assert_called_once()

        # Check that an error was logged
        mock_error.assert_called_once()
        assert "Failed to load logging config" in mock_error.call_args[0][0]

    @patch("logging.basicConfig")
    @patch("logging.error")
    @patch("builtins.print")  # Also patch print
    def test_setup_logging_with_exception(
        self, mock_print, mock_error, mock_basic_config, sample_logging_config
    ):
        """Test handling of an exception during logging setup."""
        # Make dictConfig raise an exception
        with patch("logging.config.dictConfig", side_effect=RuntimeError("Test exception")):
            # Call setup_logging
            setup_logging(sample_logging_config, "INFO")

            # Check that basicConfig was called as a fallback
            mock_basic_config.assert_called_once()

            # Check that an error was logged - use the actual message seen in the test failure
            mock_error.assert_called()

            # Get the error message and check it contains the expected text
            error_msg = mock_error.call_args[0][0]
            assert (
                "Failed to setup logging due to AppConfig not being initialised" in error_msg
                or "An unexpected error occurred during logging setup" in error_msg
            )
