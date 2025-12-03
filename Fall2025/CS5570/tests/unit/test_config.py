"""
Unit tests for configuration validation utilities.
"""

import pytest
from opengenome.utils.config import (
    validate_memory_string,
    validate_positive_int,
    validate_boolean,
    parse_memory_to_bytes,
    validate_spark_config,
)


class TestMemoryValidation:
    """Test memory string validation."""
    
    def test_valid_memory_strings(self):
        """Test valid memory format strings."""
        assert validate_memory_string("3g") is True
        assert validate_memory_string("512m") is True
        assert validate_memory_string("1024k") is True
        assert validate_memory_string("1t") is True
        assert validate_memory_string("100M") is True  # Case insensitive
    
    def test_invalid_memory_strings(self):
        """Test invalid memory format strings."""
        assert validate_memory_string("invalid") is False
        assert validate_memory_string("3") is False
        assert validate_memory_string("g3") is False
        assert validate_memory_string("3gb") is False
        assert validate_memory_string("") is False
    
    def test_parse_memory_to_bytes(self):
        """Test conversion of memory strings to bytes."""
        assert parse_memory_to_bytes("1k") == 1024
        assert parse_memory_to_bytes("1m") == 1048576
        assert parse_memory_to_bytes("1g") == 1073741824
        assert parse_memory_to_bytes("1t") == 1099511627776
        assert parse_memory_to_bytes("invalid") is None


class TestPositiveIntValidation:
    """Test positive integer validation."""
    
    def test_valid_positive_ints(self):
        """Test valid positive integers."""
        assert validate_positive_int(1) is True
        assert validate_positive_int(100) is True
        assert validate_positive_int("5") is True
    
    def test_invalid_positive_ints(self):
        """Test invalid values."""
        assert validate_positive_int(0) is False
        assert validate_positive_int(-1) is False
        assert validate_positive_int("invalid") is False
        assert validate_positive_int(None) is False


class TestBooleanValidation:
    """Test boolean validation."""
    
    def test_valid_booleans(self):
        """Test valid boolean values."""
        assert validate_boolean(True) is True
        assert validate_boolean(False) is True
        assert validate_boolean("true") is True
        assert validate_boolean("false") is True
        assert validate_boolean("yes") is True
        assert validate_boolean("no") is True
        assert validate_boolean("1") is True
        assert validate_boolean("0") is True
    
    def test_invalid_booleans(self):
        """Test invalid boolean values."""
        assert validate_boolean("invalid") is False
        assert validate_boolean(123) is False


class TestSparkConfigValidation:
    """Test Spark configuration validation."""
    
    def test_valid_config(self):
        """Test valid Spark configuration."""
        config = {
            "spark.driver.memory": "3g",
            "spark.executor.memory": "5g",
            "spark.executor.cores": "4",
        }
        is_valid, errors = validate_spark_config(config)
        assert is_valid is True
        assert len(errors) == 0
    
    def test_invalid_memory_config(self):
        """Test configuration with invalid memory."""
        config = {
            "spark.driver.memory": "invalid",
        }
        is_valid, errors = validate_spark_config(config)
        assert is_valid is False
        assert len(errors) == 1
        assert "Invalid memory format" in errors[0]
    
    def test_invalid_numeric_config(self):
        """Test configuration with invalid numeric."""
        config = {
            "spark.executor.cores": "invalid",
        }
        is_valid, errors = validate_spark_config(config)
        assert is_valid is False
        assert len(errors) == 1
        assert "Invalid positive integer" in errors[0]
    
    def test_multiple_errors(self):
        """Test configuration with multiple errors."""
        config = {
            "spark.driver.memory": "bad",
            "spark.executor.cores": "-1",
        }
        is_valid, errors = validate_spark_config(config)
        assert is_valid is False
        assert len(errors) == 2
