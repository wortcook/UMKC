FROM python:3.8-slim

LABEL maintainer="OpenGenome2 Team"
LABEL description="OpenGenome2 Web UI"

# Set working directory
WORKDIR /opt/opengenome

# Install system dependencies including Java for PySpark and gcc for biopython
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    default-jre-headless \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Set JAVA_HOME for PySpark (auto-detect)
ENV JAVA_HOME=/usr/lib/jvm/default-java

# Copy requirements from docker/web directory
COPY docker/web/requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Note: Application source is mounted as volume at runtime
# This allows live code updates during development

# Set Python path
ENV PYTHONPATH=/opt/opengenome/src

# Create necessary directories
RUN mkdir -p /data/uploads /data/parquet /results /cache /logs

# Expose Flask port
EXPOSE 5000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --retries=3 --start-period=10s \
    CMD curl -f http://localhost:5000/api/health || exit 1

# Run Flask app
CMD ["python", "-m", "flask", "--app", "opengenome.web.app", "run", "--host=0.0.0.0", "--port=5000"]
