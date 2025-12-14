#!/usr/bin/env python3
"""
Unit tests for the config module.
"""

import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

# Add tools directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from config import (
    WorkspaceConfig,
    ConfigValidationError,
    load_config,
    get_config,
    get_config_value,
    create_default_config,
    show_config,
    clear_config_cache,
    get_config_path,
    CONFIG_FILENAME,
    DEFAULT_TEST_TIMEOUT,
    DEFAULT_MODEL,
    DEFAULT_HEALTH_CHECK_TIMEOUT,
    DEFAULT_LOCK_TIMEOUT,
)


class TestWorkspaceConfig(unittest.TestCase):
    """Tests for WorkspaceConfig dataclass."""

    def test_default_values(self):
        """Test that default values are set correctly."""
        config = WorkspaceConfig()

        self.assertIsNone(config.test_command)
        self.assertEqual(config.test_timeout, DEFAULT_TEST_TIMEOUT)
        self.assertEqual(config.default_model, DEFAULT_MODEL)
        self.assertEqual(config.health_check_timeout, DEFAULT_HEALTH_CHECK_TIMEOUT)
        self.assertEqual(config.lock_timeout, DEFAULT_LOCK_TIMEOUT)
        self.assertTrue(config.auto_sync_after_accept)
        self.assertTrue(config.push_after_accept)
        self.assertTrue(config.delete_remote_branch)
        self.assertEqual(config.main_branch, "main")
        self.assertIsNone(config.ticket_prefix)

    def test_to_dict(self):
        """Test conversion to dictionary."""
        config = WorkspaceConfig()
        config_dict = config.to_dict()

        self.assertIsInstance(config_dict, dict)
        self.assertIn("test_command", config_dict)
        self.assertIn("test_timeout", config_dict)
        self.assertIn("default_model", config_dict)

    def test_from_dict_valid(self):
        """Test creating from valid dictionary."""
        data = {
            "test_command": "npm test",
            "test_timeout": 600,
            "default_model": "sonnet",
        }
        config = WorkspaceConfig.from_dict(data)

        self.assertEqual(config.test_command, "npm test")
        self.assertEqual(config.test_timeout, 600)
        self.assertEqual(config.default_model, "sonnet")
        # Defaults should be used for unspecified fields
        self.assertEqual(config.lock_timeout, DEFAULT_LOCK_TIMEOUT)

    def test_from_dict_empty(self):
        """Test creating from empty dictionary uses defaults."""
        config = WorkspaceConfig.from_dict({})

        self.assertIsNone(config.test_command)
        self.assertEqual(config.test_timeout, DEFAULT_TEST_TIMEOUT)

    def test_from_dict_invalid_test_timeout(self):
        """Test validation error for invalid test_timeout."""
        data = {"test_timeout": "not an integer"}

        with self.assertRaises(ConfigValidationError) as context:
            WorkspaceConfig.from_dict(data)

        self.assertIn("test_timeout", str(context.exception))

    def test_from_dict_negative_timeout(self):
        """Test validation error for negative timeout."""
        data = {"test_timeout": -100}

        with self.assertRaises(ConfigValidationError) as context:
            WorkspaceConfig.from_dict(data)

        self.assertIn("positive", str(context.exception))

    def test_from_dict_invalid_model(self):
        """Test validation error for invalid model."""
        data = {"default_model": "invalid-model"}

        with self.assertRaises(ConfigValidationError) as context:
            WorkspaceConfig.from_dict(data)

        self.assertIn("default_model", str(context.exception))

    def test_from_dict_model_case_insensitive(self):
        """Test that model names are case insensitive."""
        data = {"default_model": "OPUS"}
        config = WorkspaceConfig.from_dict(data)
        self.assertEqual(config.default_model, "opus")

        data = {"default_model": "Sonnet"}
        config = WorkspaceConfig.from_dict(data)
        self.assertEqual(config.default_model, "sonnet")

    def test_from_dict_invalid_boolean(self):
        """Test validation error for invalid boolean."""
        data = {"push_after_accept": "yes"}  # Should be True/False

        with self.assertRaises(ConfigValidationError) as context:
            WorkspaceConfig.from_dict(data)

        self.assertIn("boolean", str(context.exception))

    def test_from_dict_empty_main_branch(self):
        """Test validation error for empty main_branch."""
        data = {"main_branch": "   "}

        with self.assertRaises(ConfigValidationError) as context:
            WorkspaceConfig.from_dict(data)

        self.assertIn("non-empty", str(context.exception))


class TestLoadConfig(unittest.TestCase):
    """Tests for load_config function."""

    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        clear_config_cache()

    def tearDown(self):
        """Clean up test fixtures."""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
        clear_config_cache()

    def test_load_missing_config(self):
        """Test loading when no config file exists."""
        result = load_config(self.temp_dir)

        self.assertTrue(result["success"])
        self.assertFalse(result.get("exists", True))
        self.assertIsInstance(result["config"], WorkspaceConfig)

    def test_load_valid_config(self):
        """Test loading a valid config file."""
        config_data = {
            "test_command": "pytest",
            "test_timeout": 180,
        }
        config_path = Path(self.temp_dir) / CONFIG_FILENAME
        with open(config_path, 'w') as f:
            json.dump(config_data, f)

        result = load_config(self.temp_dir)

        self.assertTrue(result["success"])
        self.assertTrue(result.get("exists"))
        self.assertEqual(result["config"].test_command, "pytest")
        self.assertEqual(result["config"].test_timeout, 180)

    def test_load_invalid_json(self):
        """Test error handling for invalid JSON."""
        config_path = Path(self.temp_dir) / CONFIG_FILENAME
        with open(config_path, 'w') as f:
            f.write("{ invalid json }")

        result = load_config(self.temp_dir)

        self.assertFalse(result["success"])
        self.assertIn("Invalid JSON", result["error"])

    def test_load_validation_error(self):
        """Test error handling for validation errors."""
        config_data = {"test_timeout": "invalid"}
        config_path = Path(self.temp_dir) / CONFIG_FILENAME
        with open(config_path, 'w') as f:
            json.dump(config_data, f)

        result = load_config(self.temp_dir)

        self.assertFalse(result["success"])
        self.assertTrue(result.get("config_error"))

    def test_load_caching(self):
        """Test that configs are cached."""
        config_data = {"test_command": "npm test"}
        config_path = Path(self.temp_dir) / CONFIG_FILENAME
        with open(config_path, 'w') as f:
            json.dump(config_data, f)

        # Load once
        result1 = load_config(self.temp_dir)
        self.assertTrue(result1["success"])
        self.assertFalse(result1.get("cached", False))

        # Load again - should be cached
        result2 = load_config(self.temp_dir)
        self.assertTrue(result2["success"])
        self.assertTrue(result2.get("cached", False))

    def test_load_force_reload(self):
        """Test force reload bypasses cache."""
        config_data = {"test_command": "npm test"}
        config_path = Path(self.temp_dir) / CONFIG_FILENAME
        with open(config_path, 'w') as f:
            json.dump(config_data, f)

        # Load once
        load_config(self.temp_dir)

        # Force reload
        result = load_config(self.temp_dir, force_reload=True)
        self.assertTrue(result["success"])
        self.assertFalse(result.get("cached", False))


class TestGetConfig(unittest.TestCase):
    """Tests for get_config function."""

    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        clear_config_cache()

    def tearDown(self):
        """Clean up test fixtures."""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
        clear_config_cache()

    def test_get_config_returns_config(self):
        """Test get_config always returns WorkspaceConfig."""
        config = get_config(self.temp_dir)
        self.assertIsInstance(config, WorkspaceConfig)

    def test_get_config_with_valid_file(self):
        """Test get_config with valid config file."""
        config_data = {"test_command": "make test"}
        config_path = Path(self.temp_dir) / CONFIG_FILENAME
        with open(config_path, 'w') as f:
            json.dump(config_data, f)

        config = get_config(self.temp_dir)
        self.assertEqual(config.test_command, "make test")


class TestGetConfigValue(unittest.TestCase):
    """Tests for get_config_value function."""

    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        clear_config_cache()

    def tearDown(self):
        """Clean up test fixtures."""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
        clear_config_cache()

    def test_get_existing_value(self):
        """Test getting an existing config value."""
        config_data = {"test_timeout": 500}
        config_path = Path(self.temp_dir) / CONFIG_FILENAME
        with open(config_path, 'w') as f:
            json.dump(config_data, f)

        value = get_config_value(self.temp_dir, "test_timeout")
        self.assertEqual(value, 500)

    def test_get_missing_value_with_default(self):
        """Test getting a missing value returns default."""
        value = get_config_value(self.temp_dir, "nonexistent_key", "default_value")
        self.assertEqual(value, "default_value")

    def test_get_none_value_returns_default(self):
        """Test that None values fall back to default."""
        config_data = {"test_command": None}
        config_path = Path(self.temp_dir) / CONFIG_FILENAME
        with open(config_path, 'w') as f:
            json.dump(config_data, f)

        value = get_config_value(self.temp_dir, "test_command", "pytest")
        self.assertEqual(value, "pytest")


class TestCreateDefaultConfig(unittest.TestCase):
    """Tests for create_default_config function."""

    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        clear_config_cache()

    def tearDown(self):
        """Clean up test fixtures."""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
        clear_config_cache()

    def test_create_default_config(self):
        """Test creating a default config file."""
        result = create_default_config(self.temp_dir)

        self.assertTrue(result["success"])
        self.assertTrue(Path(result["path"]).exists())

        # Verify file content
        with open(result["path"], 'r') as f:
            data = json.load(f)
        self.assertIn("test_timeout", data)

    def test_create_config_nonexistent_workspace(self):
        """Test error when workspace doesn't exist."""
        result = create_default_config("/nonexistent/path")

        self.assertFalse(result["success"])
        self.assertIn("does not exist", result["error"])

    def test_create_config_no_overwrite(self):
        """Test that existing config is not overwritten by default."""
        # Create initial config
        create_default_config(self.temp_dir)

        # Try to create again without overwrite
        result = create_default_config(self.temp_dir)

        self.assertFalse(result["success"])
        self.assertIn("already exists", result["error"])

    def test_create_config_with_overwrite(self):
        """Test overwriting existing config."""
        # Create initial config
        create_default_config(self.temp_dir)

        # Overwrite
        result = create_default_config(self.temp_dir, overwrite=True)

        self.assertTrue(result["success"])


class TestShowConfig(unittest.TestCase):
    """Tests for show_config function."""

    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        clear_config_cache()

    def tearDown(self):
        """Clean up test fixtures."""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
        clear_config_cache()

    def test_show_missing_config(self):
        """Test showing config when file doesn't exist."""
        result = show_config(self.temp_dir)

        self.assertTrue(result["success"])
        self.assertFalse(result.get("exists"))
        self.assertIn("config", result)

    def test_show_existing_config(self):
        """Test showing existing config."""
        config_data = {"test_command": "pytest"}
        config_path = Path(self.temp_dir) / CONFIG_FILENAME
        with open(config_path, 'w') as f:
            json.dump(config_data, f)

        result = show_config(self.temp_dir)

        self.assertTrue(result["success"])
        self.assertTrue(result.get("exists"))
        self.assertEqual(result["config"]["test_command"], "pytest")


class TestConfigValidationError(unittest.TestCase):
    """Tests for ConfigValidationError exception."""

    def test_to_dict(self):
        """Test converting error to dictionary."""
        error = ConfigValidationError(
            message="Invalid value",
            field="test_timeout",
            value=-100,
            hint="Use a positive integer"
        )
        result = error.to_dict()

        self.assertFalse(result["success"])
        self.assertEqual(result["error"], "Invalid value")
        self.assertEqual(result["field"], "test_timeout")
        self.assertEqual(result["invalid_value"], -100)
        self.assertEqual(result["hint"], "Use a positive integer")
        self.assertTrue(result["config_error"])


class TestClearConfigCache(unittest.TestCase):
    """Tests for clear_config_cache function."""

    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        clear_config_cache()

    def tearDown(self):
        """Clean up test fixtures."""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
        clear_config_cache()

    def test_clear_specific_workspace(self):
        """Test clearing cache for specific workspace."""
        config_data = {"test_command": "npm test"}
        config_path = Path(self.temp_dir) / CONFIG_FILENAME
        with open(config_path, 'w') as f:
            json.dump(config_data, f)

        # Load to populate cache
        load_config(self.temp_dir)

        # Clear cache for this workspace
        clear_config_cache(self.temp_dir)

        # Load again - should not be cached
        result = load_config(self.temp_dir)
        self.assertFalse(result.get("cached", False))

    def test_clear_all_cache(self):
        """Test clearing entire cache."""
        # Create and load config
        config_data = {"test_command": "npm test"}
        config_path = Path(self.temp_dir) / CONFIG_FILENAME
        with open(config_path, 'w') as f:
            json.dump(config_data, f)

        load_config(self.temp_dir)

        # Clear all cache
        clear_config_cache()

        # Load again - should not be cached
        result = load_config(self.temp_dir)
        self.assertFalse(result.get("cached", False))


if __name__ == "__main__":
    unittest.main()
