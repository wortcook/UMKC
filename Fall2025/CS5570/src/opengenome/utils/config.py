"""
Configuration validation utilities.
"""

import re
from typing import Any, Optional, Tuple, List


def validate_memory_string(value: str) -> bool:
    """
    Validate Spark memory configuration string.
    
    Args:
        value: Memory string (e.g., "3g", "512m", "1024k")
    
    Returns:
        bool: True if valid format
    
    Examples:
        >>> validate_memory_string("3g")
        True
        >>> validate_memory_string("invalid")
        False
    """
    pattern = r'^\d+[kmgt]$'
    return bool(re.match(pattern, value.lower()))


def validate_positive_int(value: Any) -> bool:
    """
    Validate positive integer value.
    
    Args:
        value: Value to validate
    
    Returns:
        bool: True if positive integer
    """
    try:
        return int(value) > 0
    except (ValueError, TypeError):
        return False


def validate_boolean(value: Any) -> bool:
    """
    Validate boolean value from string.
    
    Args:
        value: Value to check
    
    Returns:
        bool: True if valid boolean representation
    """
    if isinstance(value, bool):
        return True
    if isinstance(value, str):
        return value.lower() in ('true', 'false', '1', '0', 'yes', 'no')
    return False


def parse_memory_to_bytes(value: str) -> Optional[int]:
    """
    Convert memory string to bytes.
    
    Args:
        value: Memory string (e.g., "3g", "512m")
    
    Returns:
        int: Number of bytes, or None if invalid
    
    Examples:
        >>> parse_memory_to_bytes("1g")
        1073741824
        >>> parse_memory_to_bytes("512m")
        536870912
    """
    if not validate_memory_string(value):
        return None
    
    multipliers = {
        'k': 1024,
        'm': 1024 ** 2,
        'g': 1024 ** 3,
        't': 1024 ** 4,
    }
    
    unit = value[-1].lower()
    try:
        number = int(value[:-1])
        return number * multipliers[unit]
    except (ValueError, KeyError):
        return None


def validate_spark_config(config: dict) -> Tuple[bool, List[str]]:
    """
    Validate Spark configuration dictionary.
    
    Args:
        config: Configuration key-value pairs
    
    Returns:
        tuple: (is_valid, list of error messages)
    
    Example:
        >>> validate_spark_config({"spark.driver.memory": "3g"})
        (True, [])
        >>> validate_spark_config({"spark.driver.memory": "invalid"})
        (False, ['Invalid memory format: invalid'])
    """
    errors = []
    
    # Validate memory configurations
    memory_keys = [
        "spark.driver.memory",
        "spark.executor.memory",
        "spark.driver.maxResultSize",
    ]
    
    for key in memory_keys:
        if key in config:
            value = config[key]
            if not validate_memory_string(str(value)):
                errors.append(f"Invalid memory format for {key}: {value}")
    
    # Validate numeric configurations
    numeric_keys = [
        "spark.executor.cores",
        "spark.sql.shuffle.partitions",
    ]
    
    for key in numeric_keys:
        if key in config:
            value = config[key]
            if not validate_positive_int(value):
                errors.append(f"Invalid positive integer for {key}: {value}")
    
    return len(errors) == 0, errors
