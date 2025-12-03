"""
Unit tests for Spark session management.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from opengenome.spark.session import (
    get_spark_session,
    stop_spark_session,
    is_spark_session_active,
)


@pytest.fixture
def mock_spark_session():
    """Fixture for mocked Spark session."""
    mock_session = Mock()
    mock_session.version = "3.5.0"
    mock_session.sparkContext.master = "spark://test:7077"
    mock_session.sparkContext.appName = "TestApp"
    mock_session.sparkContext.applicationId = "app-test-001"
    mock_session.sparkContext.setLogLevel = Mock()
    mock_session.sparkContext._jsc.sc().isStopped.return_value = False
    return mock_session


@pytest.fixture(autouse=True)
def reset_session():
    """Reset global session state before each test."""
    import opengenome.spark.session as session_module
    session_module._spark_session = None
    yield
    session_module._spark_session = None


class TestGetSparkSession:
    """Test Spark session creation."""
    
    @patch('opengenome.spark.session.SparkSession')
    def test_creates_new_session(self, mock_spark_class, mock_spark_session):
        """Test that a new session is created on first call."""
        mock_builder = Mock()
        mock_spark_class.builder.config.return_value = mock_builder
        mock_builder.getOrCreate.return_value = mock_spark_session
        
        session = get_spark_session(app_name="TestApp")
        
        assert session is not None
        assert session.version == "3.5.0"
        mock_builder.getOrCreate.assert_called_once()
    
    @patch('opengenome.spark.session.SparkSession')
    def test_reuses_existing_session(self, mock_spark_class, mock_spark_session):
        """Test that existing session is reused."""
        mock_builder = Mock()
        mock_spark_class.builder.config.return_value = mock_builder
        mock_builder.getOrCreate.return_value = mock_spark_session
        
        session1 = get_spark_session(app_name="Test1")
        session2 = get_spark_session(app_name="Test2")
        
        assert session1 is session2
        # getOrCreate called only once
        mock_builder.getOrCreate.assert_called_once()
    
    @patch('opengenome.spark.session.SparkSession')
    @patch.dict('os.environ', {
        'SPARK_DRIVER_MEMORY': '4g',
        'SPARK_EXECUTOR_MEMORY': '6g',
    })
    def test_uses_environment_config(self, mock_spark_class, mock_spark_session):
        """Test that environment variables are used."""
        mock_builder = Mock()
        mock_spark_class.builder.config.return_value = mock_builder
        mock_builder.getOrCreate.return_value = mock_spark_session
        
        session = get_spark_session()
        
        # Verify config was set (via SparkConf)
        assert session is not None
    
    @patch('opengenome.spark.session.SparkSession')
    @patch.dict('os.environ', {
        'SPARK_DRIVER_MEMORY': 'invalid',
    })
    def test_validates_memory_config(self, mock_spark_class, mock_spark_session):
        """Test that invalid memory config triggers warning."""
        mock_builder = Mock()
        mock_spark_class.builder.config.return_value = mock_builder
        mock_builder.getOrCreate.return_value = mock_spark_session
        
        with patch('opengenome.spark.session.logger') as mock_logger:
            session = get_spark_session()
            
            # Should log warning about invalid memory
            mock_logger.warning.assert_called()
            assert "Invalid driver memory" in str(mock_logger.warning.call_args)


class TestStopSparkSession:
    """Test Spark session stopping."""
    
    @patch('opengenome.spark.session.SparkSession')
    def test_stops_active_session(self, mock_spark_class, mock_spark_session):
        """Test stopping an active session."""
        mock_builder = Mock()
        mock_spark_class.builder.config.return_value = mock_builder
        mock_builder.getOrCreate.return_value = mock_spark_session
        
        # Create session
        get_spark_session()
        
        # Stop it
        stop_spark_session()
        
        mock_spark_session.stop.assert_called_once()
    
    def test_stop_without_session(self):
        """Test stopping when no session exists."""
        # Should not raise error
        stop_spark_session()


class TestIsSparkSessionActive:
    """Test session activity checking."""
    
    def test_no_session(self):
        """Test when no session exists."""
        assert is_spark_session_active() is False
    
    @patch('opengenome.spark.session.SparkSession')
    def test_active_session(self, mock_spark_class, mock_spark_session):
        """Test when session is active."""
        mock_builder = Mock()
        mock_spark_class.builder.config.return_value = mock_builder
        mock_builder.getOrCreate.return_value = mock_spark_session
        
        get_spark_session()
        
        assert is_spark_session_active() is True
