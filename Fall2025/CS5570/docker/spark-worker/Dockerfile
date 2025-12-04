# Spark Worker Container
# Base: Apache Spark 3.5.0 with Python 3.8
# IMPORTANT: Package versions must exactly match master for execution consistency
FROM apache/spark:3.5.0-python3

USER root

# Install Python dependencies matching master
# Rationale: Workers must have identical Python environment as master
# to avoid serialization errors and library mismatches
RUN pip3 install --no-cache-dir --upgrade pip==23.3.1 setuptools==69.0.2 wheel==0.42.0 \
    && pip3 install --no-cache-dir --prefer-binary \
    py4j==0.10.9.7 \
    biopython==1.81 \
    pyarrow==14.0.1 \
    pandas==2.0.3 \
    numpy==1.24.3 \
    # Verify py4j installation - build will fail if not installed
    && python3 -c "import py4j; print(f'✓ py4j {py4j.__version__} installed')"

# Configure Spark environment
ENV PYSPARK_PYTHON=python3 \
    SPARK_HOME=/opt/spark

# TODO: For production, create non-root user:
# RUN useradd -m -u 1000 spark
# USER spark

# Default command runs Spark worker
CMD ["/opt/bitnami/scripts/spark/run.sh"]
