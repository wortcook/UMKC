# OpenGenome2 Refactoring Project

Scalable, production-ready genomic sequence analysis using Apache Spark.

## Overview

OpenGenome2 is a distributed genomic analysis platform that processes large FASTA files using Apache Spark. This refactored implementation replaces Jupyter notebooks with a CLI-based architecture for better version control, testing, and production deployment.

### Key Features

- **Distributed Processing**: Apache Spark cluster (1 master + 2 workers)
- **Scalable**: Handles multi-GB genomic datasets
- **Modular**: Clean Python package structure
- **Tested**: Automated validation and test suite
- **Container-based**: Docker Compose orchestration
- **Production-ready**: Resource limits, health checks, logging configuration

## Quick Start

### Prerequisites

- Docker Desktop (v20.10+)
- Docker Compose V2
- 8GB+ available RAM
- 20GB+ free disk space

### Installation

```bash
# Clone repository
git clone <repository-url>
cd CS5570

# Copy environment configuration
cp .env.example .env

# Build and start services
make build
make up

# Validate cluster
make validate
```

### Access Interfaces

- **Web UI**: http://localhost:5000 - User-friendly interface for all operations
- **Spark UI**: http://localhost:8081 - Spark Master dashboard

## Architecture

```
┌──────────────┐
│   Web UI     │ (5000)
│  Flask App   │
└──────┬───────┘
       │
┌──────▼──────────────┐
│   Spark Master      │ (8081:8080, 7077)
│  + CLI Driver App   │
└──────┬──────────────┘
       │
       ├─────────────┬─────────────┐
       ▼             ▼             ▼
┌──────────┐  ┌──────────┐  ┌──────────┐
│ Worker 1 │  │ Worker 2 │  │   Data   │
│ 6GB/4CPU │  │ 6GB/4CPU │  │  Volumes │
└──────────┘  └──────────┘  └──────────┘
```

### Components

- **Web UI**: Browser-based interface for ingestion and analysis
### Common Commands

```bash
# Start cluster
make up

# Open Web UI
make web-ui

# Open Spark UI
make spark-ui

# View logs
make logs
make logs-follow
make logs-web

# Interactive shell
make shell

# Run tests
make test

# Stop cluster
make down

# Clean up
make clean
```

### Running Analysis

**Option 1: Web UI (Recommended)**

```bash
make web-ui  # Opens http://localhost:5000
```

Navigate through the intuitive interface:
1. **Ingest** - Upload FASTA files or download from HuggingFace
2. **Analyze** - Run k-mer or codon analysis
3. **Results** - Browse and download results

**Option 2: CLI**

```bash
# Use the CLI wrapper script:
./opengenome version

### Running Analysis

```bash
# Use the CLI wrapper script:
./opengenome version
./opengenome config
./opengenome info --spark-ui

# Or use make:
make cli ARGS="version"
make cli ARGS="config"

# Data ingestion (Phase 3):
./opengenome ingest organelle --max-sequences 10000
./opengenome ingest organelle --chunk-size 25000 --compression zstd

# Future commands (Phase 4+):
./opengenome analyze kmer --k 6
./opengenome visualize --output /results/figures/
```

## Project Structure

```
.
├── docker/                 # Container definitions
│   ├── spark-master/      # Master + driver application
│   └── spark-worker/      # Worker nodes
├── src/opengenome/        # Python package
│   ├── cli/               # Command-line interface
│   ├── ingestion/         # Data loading
│   ├── analysis/          # K-mer, codon analysis
│   ├── spark/             # Spark session management
│   ├── visualization/     # Plotting utilities
│   ├── ml/                # Machine learning models
│   └── utils/             # Helpers
├── tests/                 # Test suite
│   ├── unit/              # Unit tests
│   └── integration/       # Integration tests
├── data/                  # Data directories
│   ├── raw/               # Original FASTA files
│   ├── parquet/           # Processed parquet files
│   └── samples/           # Test datasets
├── results/               # Analysis outputs
├── cache/                 # HuggingFace models, checkpoints
├── logs/                  # Application logs
├── scripts/               # Utility scripts
├── docs/                  # Documentation
├── docker-compose.yml     # Container orchestration
├── Makefile               # Development commands
└── .env.example           # Configuration template
```

## Configuration

### Environment Variables

See `.env.example` for all configuration options:

- **Spark Settings**: Memory, cores, executor config
- **Data Paths**: Input/output directories
- **Processing**: Shard size, k-mer defaults
- **HuggingFace**: Model repository, cache
- **Performance**: Adaptive execution, timeouts
- **Logging**: Level, format, retention

### Resource Allocation

Default configuration (per worker):
- **Memory**: 6GB
- **CPU Cores**: 4
- **Container Limit**: 7GB (includes overhead)

Adjust in `docker-compose.yml` based on your hardware.

## Development

### Running Tests

```bash
# All tests
make test

# With coverage
make test-coverage

# Inside container
make shell
pytest tests/unit/ -v
pytest tests/integration/ -v
```

### Code Style

```bash
# Format code (when added)
black src/ tests/

# Lint
pylint src/

# Type checking
mypy src/
```

## Troubleshooting

### Common Issues

#### 1. Port Already in Use

**Symptom**: `Bind for 0.0.0.0:8081 failed: port is already allocated`

**Solution**:
```bash
# Find process using port
lsof -i :8081

# Change port in docker-compose.yml
# ports:
#   - "8082:8080"  # Use different external port
```

#### 2. Containers Not Starting

**Symptom**: `docker ps` shows no running containers

**Solution**:
```bash
# Check logs
make logs

# Common causes:
# - Insufficient memory (need 8GB+ free)
# - Docker daemon not running
# - Image build failed

# Rebuild from scratch
make clean
make rebuild
make up
```

#### 3. Workers Not Connecting

**Symptom**: Spark UI shows 0 workers

**Solution**:
```bash
# Wait longer (can take 30s)
sleep 30 && curl -s http://localhost:8081/json/ | python3 -m json.tool

# Check worker logs
docker logs opengenome-spark-worker-1

# Restart services
make restart
```

#### 4. Out of Memory

**Symptom**: `Container killed (exit code 137)`

**Solution**:
```bash
# Reduce memory in docker-compose.yml
# command: ... --memory 4g ...  # Instead of 6g

# Or increase Docker Desktop memory limit
# Docker Desktop → Settings → Resources → Memory
```

#### 5. Permission Denied on Volumes

**Symptom**: `Permission denied` errors in logs

**Solution**:
```bash
# Fix permissions
chmod -R 777 data/ results/ cache/ logs/

# Or run containers as your user (docker-compose.yml):
# user: "${UID}:${GID}"
```

#### 6. Slow Performance

**Symptom**: Jobs taking too long

**Solution**:
```bash
# Check resource allocation
docker stats

# Increase parallelism in .env:
# SPARK_SQL_SHUFFLE_PARTITIONS=400

# Add more workers:
# docker-compose up -d --scale spark-worker=4
```

### Health Checks

```bash
# Check all services
docker ps

# Validate cluster
make validate

# Check worker registration
curl -s http://localhost:8081/json/ | python3 -c "import sys, json; data=json.load(sys.stdin); print(f\"Workers: {len(data['workers'])}\")"

# Test Spark connectivity
docker cp scripts/validate_cluster.py opengenome-spark-master:/tmp/
docker exec opengenome-spark-master python3 /tmp/validate_cluster.py
```

### Debug Mode

```bash
# Enable debug logging
# In .env:
DEBUG=true
LOG_LEVEL=DEBUG

# Restart services
make restart

# Follow logs
make logs-follow
```

## Production Deployment

### Security Checklist

- [ ] Change to non-root user in Dockerfiles
- [ ] Don't expose port 7077 externally
- [ ] Enable Spark authentication
- [ ] Enable SSL/TLS encryption
- [ ] Use Docker secrets for credentials
- [ ] Implement network policies
- [ ] Regular security updates
- [ ] Scan images for vulnerabilities

### Production Configuration

```bash
# Use production environment
cp .env.production .env

# Edit with production values
vim .env

# Set secure permissions
chmod 600 .env

# Deploy with restart policy (already configured)
make up
```

### Monitoring

Consider adding:
- **Prometheus**: Metrics collection
- **Grafana**: Visualization dashboards
- **ELK Stack**: Centralized logging
- **Health check endpoints**: Application monitoring

## Performance Tuning

### Memory Settings

```bash
# .env adjustments based on data size:

# Small datasets (<1GB):
SPARK_EXECUTOR_MEMORY=2g
SPARK_WORKER_MEMORY=3g

# Medium datasets (1-10GB):
SPARK_EXECUTOR_MEMORY=5g
SPARK_WORKER_MEMORY=6g

# Large datasets (10GB+):
SPARK_EXECUTOR_MEMORY=10g
SPARK_WORKER_MEMORY=12g
```

### Parallelism

```bash
# Increase for larger datasets:
SPARK_SQL_SHUFFLE_PARTITIONS=400  # Default: 200
SHARD_SIZE=200000  # Larger shards for better performance
```

## Documentation

- [DESIGN.md](docs/DESIGN.md) - Architecture and design decisions
- [PHASE1_SUMMARY.md](docs/PHASE1_SUMMARY.md) - Implementation details
- [PHASE1_REVIEW.md](docs/PHASE1_REVIEW.md) - Critical analysis

## Contributing

1. Fork repository
2. Create feature branch
3. Make changes
4. Run tests: `make test`
5. Submit pull request

## License

[License information]

## Contact

[Contact information]

## Acknowledgments

- Apache Spark community
- BioPython developers
- Arc Institute OpenGenome2 dataset

---

**Status**: Phase 1 (Core Infrastructure) Complete ✓

**Next**: Phase 2 (CLI Foundation) - In Progress
