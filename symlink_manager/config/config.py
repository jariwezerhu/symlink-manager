"""
Configuration module for symlink manager.

This module provides a central configuration system for the application,
loading settings from a YAML file and providing default values where needed.
"""

import logging
import os
from typing import Dict, List, Optional, Tuple


import yaml


class Config:
    """Configuration manager for symlink manager.

    Loads configuration from a YAML file and provides access to configuration values
    with sensible defaults for missing values.
    """

    # Default configuration values
    DEFAULTS = {
        "paths": {
            "torrents": "/mnt/remote/realdebrid/torrents/",
            "library": "/mnt/plex",
            "database": "./media_library.db",
        },
        "directories": {
            "separate_anime": True,
            "movies": "movies",
            "shows": "shows",
            "anime_movies": "anime_movies",
            "anime_shows": "anime_shows",
        },
        "logging": {
            "level": "INFO",
        },
    }

    # Valid logging levels
    VALID_LOG_LEVELS = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]

    def __init__(self, config_path: Optional[str] = None):
        """Initialize the configuration manager.

        Args:
            config_path: Path to the YAML configuration file. If None,
                         the default location will be used.
        """
        self.logger = logging.getLogger(__name__)
        self._config = self.DEFAULTS.copy()

        # Find and load configuration file
        if config_path:
            self.config_path = config_path
        else:
            self.config_path = self._find_config_file()

        if self.config_path and os.path.exists(self.config_path):
            self._load_config()
        else:
            self.logger.warning(f"No configuration file found, using defaults")

        # Validate the loaded configuration
        self._validate_config()

    def _find_config_file(self) -> Optional[str]:
        """Find the configuration file in standard locations.

        Returns:
            Path to the configuration file, or None if not found.
        """
        # Check standard locations
        locations = [
            "config.yaml",  # Current directory
            "config.yml",
            os.path.expanduser("~/.config/symlink_manager/config.yaml"),
            "/etc/symlink_manager/config.yaml",
        ]

        for loc in locations:
            if os.path.exists(loc):
                return loc

        return None

    def _load_config(self) -> None:
        """Load configuration from the YAML file."""
        try:
            with open(self.config_path, "r") as f:
                config_data = yaml.safe_load(f)

            if not config_data:
                self.logger.warning("Empty configuration file")
                return

            # Update configuration with loaded values
            self._update_config_recursive(self._config, config_data)

        except Exception as e:
            self.logger.error(f"Error loading configuration: {e}")

    def _update_config_recursive(self, target: Dict, source: Dict) -> None:
        """Recursively update a dictionary with values from another dictionary.

        Args:
            target: The dictionary to update
            source: The dictionary with new values
        """
        for key, value in source.items():
            if (
                key in target
                and isinstance(target[key], dict)
                and isinstance(value, dict)
            ):
                # Recursively update nested dictionaries
                self._update_config_recursive(target[key], value)
            elif key in target:
                # Update existing keys
                target[key] = value
            else:
                # Warn about unknown keys
                self.logger.warning(f"Unknown configuration key: {key}")

    def _validate_config(self) -> List[str]:
        """Validate the configuration values.

        Checks:
        - If paths exist
        - If logging level is valid

        Returns:
            List of validation issues
        """
        issues = []

        # Validate paths
        torrents_path = self.get_torrents_path()
        if not os.path.exists(torrents_path):
            issues.append(f"Torrents path does not exist: {torrents_path}")
            self.logger.warning(f"Torrents path does not exist: {torrents_path}")

        library_path = self.get_library_path()
        if not os.path.exists(library_path):
            issues.append(f"Library path does not exist: {library_path}")
            self.logger.warning(f"Library path does not exist: {library_path}")

        # For database path, check if the directory exists (not the file itself)
        db_path = self.get_database_path()
        db_dir = os.path.dirname(os.path.abspath(db_path))
        if db_dir and not os.path.exists(db_dir):
            issues.append(f"Database directory does not exist: {db_dir}")
            self.logger.warning(f"Database directory does not exist: {db_dir}")

        # Validate logging level
        log_level = self.get_logging_level()
        if log_level not in self.VALID_LOG_LEVELS:
            issues.append(f"Invalid logging level: {log_level}")
            self.logger.warning(
                f"Invalid logging level: {log_level}, will use 'INFO' instead"
            )
            # Reset to default
            self._config["logging"]["level"] = "INFO"

        # Validate directory names (ensure they're not empty or contain invalid characters)
        for dir_type, dir_name in self.get_directory_names().items():
            if not dir_name or not isinstance(dir_name, str):
                issues.append(f"Invalid directory name for {dir_type}: {dir_name}")
                self.logger.warning(
                    f"Invalid directory name for {dir_type}: {dir_name}"
                )
            elif os.path.sep in dir_name:
                issues.append(f"Directory name '{dir_name}' contains path separator")
                self.logger.warning(
                    f"Directory name '{dir_name}' contains path separator"
                )

        return issues

    def validate_paths(self, create_missing: bool = False) -> Tuple[bool, List[str]]:
        """Validate paths and optionally create missing directories.

        Args:
            create_missing: If True, try to create missing directories

        Returns:
            Tuple of (success, list of issues)
        """
        issues = []
        success = True

        # Check torrents path
        torrents_path = self.get_torrents_path()
        if not os.path.exists(torrents_path):
            if create_missing:
                try:
                    os.makedirs(torrents_path, exist_ok=True)
                    self.logger.info(f"Created torrents directory: {torrents_path}")
                except Exception as e:
                    issues.append(f"Failed to create torrents path: {e}")
                    self.logger.error(f"Failed to create torrents path: {e}")
                    success = False
            else:
                issues.append(f"Torrents path does not exist: {torrents_path}")
                self.logger.warning(f"Torrents path does not exist: {torrents_path}")
                success = False

        # Check library path
        library_path = self.get_library_path()
        if not os.path.exists(library_path):
            if create_missing:
                try:
                    os.makedirs(library_path, exist_ok=True)
                    self.logger.info(f"Created library directory: {library_path}")
                except Exception as e:
                    issues.append(f"Failed to create library path: {e}")
                    self.logger.error(f"Failed to create library path: {e}")
                    success = False
            else:
                issues.append(f"Library path does not exist: {library_path}")
                self.logger.warning(f"Library path does not exist: {library_path}")
                success = False

        # Check database directory (not the file itself)
        db_path = self.get_database_path()
        db_dir = os.path.dirname(os.path.abspath(db_path))
        if db_dir and not os.path.exists(db_dir):
            if create_missing:
                try:
                    os.makedirs(db_dir, exist_ok=True)
                    self.logger.info(f"Created database directory: {db_dir}")
                except Exception as e:
                    issues.append(f"Failed to create database directory: {e}")
                    self.logger.error(f"Failed to create database directory: {e}")
                    success = False
            else:
                issues.append(f"Database directory does not exist: {db_dir}")
                self.logger.warning(f"Database directory does not exist: {db_dir}")
                success = False

        return success, issues

    def get_database_url(self) -> str:
        """Get the database connection URL for SQLAlchemy.

        Returns:
            Database connection URL
        """
        db_path = self.get_database_path()

        # If already a connection URL, return as is
        if db_path.startswith("sqlite:///") or "://" in db_path:
            return db_path

        # Convert path to SQLite URL
        abs_path = os.path.abspath(db_path)
        return f"sqlite:///{abs_path}"

    def get_database_path(self) -> str:
        """Get the raw database file path (not the SQLAlchemy URL).

        Returns:
            Path to the database file
        """
        return self._config["paths"]["database"]

    def get_torrents_path(self) -> str:
        """Get the torrents base path.

        Returns:
            Path to the torrents directory
        """
        return self._config["paths"]["torrents"]

    def get_library_path(self) -> str:
        """Get the library base path.

        Returns:
            Path to the library directory
        """
        return self._config["paths"]["library"]

    def get_logging_level(self) -> str:
        """Get the logging level.

        Returns:
            Logging level as a string
        """
        return self._config["logging"]["level"]

    def get_separate_anime(self) -> bool:
        """Get whether to separate anime into different directories.

        Returns:
            True if anime should be stored in separate directories
        """
        return self._config["directories"]["separate_anime"]

    def get_directory_names(self) -> Dict[str, str]:
        """Get the directory names for different media types.

        Returns:
            Dictionary with directory names
        """
        dirs = self._config["directories"]
        return {
            "movies": dirs["movies"],
            "shows": dirs["shows"],
            "anime_movies": dirs["anime_movies"],
            "anime_shows": dirs["anime_shows"],
        }

    def __str__(self) -> str:
        """Get a string representation of the configuration.

        Returns:
            String representation
        """
        return (
            f"Config(torrents={self.get_torrents_path()}, "
            f"library={self.get_library_path()}, "
            f"database={self.get_database_path()}, "
            f"logging={self.get_logging_level()})"
        )
