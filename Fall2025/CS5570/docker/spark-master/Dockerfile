# Spark Master Container with CLI Driver Application
# Base: Apache Spark 3.5.0 with Python 3.8
FROM apache/spark:3.5.0-python3

USER root

# Install system dependencies
# Rationale: git for version control integration, curl for health checks,
# wget for downloads, vim for debugging
RUN apt-get update && apt-get install -y \
    git \
    curl \
    wget \
    vim \
    && rm -rf /var/lib/apt/lists/* \
    # Upgrade pip and build tools in same layer for efficiency
    && pip3 install --no-cache-dir --upgrade pip==23.3.1 setuptools==69.0.2 wheel==0.42.0

# Install Python scientific and development dependencies
# Version constraints: pandas 2.0.3 (Python 3.8 compatible)
# Combining into single RUN reduces image layers
RUN pip3 install --no-cache-dir \
    # PySpark integration (required for CLI)
    py4j==0.10.9.7 \
    # Genomics
    biopython==1.81 \
    # Data processing
    pyarrow==14.0.1 \
    pandas==2.0.3 \
    numpy==1.24.3 \
    # Visualization
    matplotlib==3.7.3 \
    seaborn==0.13.0 \
    # CLI and utilities
    click==8.1.7 \
    python-dotenv==1.0.0 \
    pyyaml==6.0.1 \
    # Testing
    pytest==7.4.3 \
    pytest-cov==4.1.0 \
    # HuggingFace model hub
    huggingface-hub==0.19.4 \
    # Verify py4j installation - build will fail if not installed
    && python3 -c "import py4j; print(f'✓ py4j {py4j.__version__} installed')"

# Create application directory
RUN mkdir -p /opt/opengenome
WORKDIR /opt/opengenome

# Configure Spark environment
# Note: Py4J jar is auto-detected at runtime via glob pattern
ENV SPARK_HOME=/opt/spark \
    PYTHONPATH=/opt/spark/python:/opt/spark/python/lib/py4j-*-src.zip:/opt/opengenome/src:$PYTHONPATH \
    PYSPARK_PYTHON=python3 \
    PYSPARK_DRIVER_PYTHON=python3

# TODO: For production, create non-root user:
# RUN useradd -m -u 1000 spark && chown -R spark:spark /opt/opengenome
# USER spark

# Default command runs Spark master
CMD ["/opt/bitnami/scripts/spark/run.sh"]
