# OpenGenome2 Docker Refactoring - Design Document

**Date**: December 2, 2025  
**Version**: 2.0  
**Status**: Design Phase - Simplified Architecture

## Executive Summary

This document outlines the design for refactoring the OpenGenome2 genomic analysis project from a Google Colab-dependent architecture to a production-grade, Docker-based distributed computing system. The redesigned architecture eliminates Jupyter notebook complexity in favor of a clean Python CLI application with proper ML workflow patterns, optimized Spark cluster configuration, and industry-standard big data processing techniques.

**Key Design Philosophy**: Build a robust, scalable big data processing pipeline using battle-tested patterns from production ML systems, emphasizing reproducibility, testability, and operational simplicity.

---

## Table of Contents

1. [Current State Analysis](#current-state-analysis)
2. [Design Goals & Principles](#design-goals--principles)
3. [System Architecture](#system-architecture)
4. [Component Specifications](#component-specifications)
5. [Data Flow & Processing Pipeline](#data-flow--processing-pipeline)
6. [File Structure & Organization](#file-structure--organization)
7. [Configuration Management](#configuration-management)
8. [Development Workflow](#development-workflow)
9. [Testing Strategy](#testing-strategy)
10. [Deployment Scenarios](#deployment-scenarios)
11. [Migration Path](#migration-path)
12. [Risk Assessment](#risk-assessment)

---

## Current State Analysis

### Existing Implementation
- **Environment**: Google Colab notebook (single file: `CS5540_OpenGenome2Project.ipynb`)
- **Storage**: Google Drive mounted at `/content/drive/MyDrive/`
- **Compute**: Colab's shared resources with manual Spark configuration
- **Dependencies**: Mix of system packages and Python libraries installed via `apt-get` and `pip`

### Identified Issues
1. **Non-Portable**: Tightly coupled to Colab environment
2. **Manual Setup**: Repeated installations in each session
3. **Resource Limits**: Colab memory constraints (12GB driver memory workarounds)
4. **Storage Constraints**: Google Drive API limits and sync issues
5. **No Version Control**: Configuration scattered throughout notebook cells
6. **Testing Challenges**: Difficult to automate or test systematically
7. **Scaling Limitations**: Cannot easily add more compute resources
8. **Notebook Limitations**: Hard to version control, debug, test, and productionize
9. **No Pipeline Orchestration**: Manual execution order, no dependency management
10. **Poor Reproducibility**: Environment inconsistencies, no artifact tracking

### Core Functionality to Preserve
1. Data ingestion from HuggingFace (FASTA → Parquet)
2. K-mer frequency analysis (MapReduce pattern)
3. Codon usage bias analysis
4. Per-sequence k-mer vector generation
5. TF-IDF based sequence similarity search
6. Visualization (GC%, k-mer plots, codon heatmaps)

---

## Design Goals & Principles

### Primary Goals
1. **Production-Ready**: Built for reliability and operational excellence
2. **Reproducibility**: Identical behavior across environments, full artifact lineage
3. **Scalability**: Horizontal scaling with proper resource management
4. **Maintainability**: Clean code architecture, comprehensive testing
5. **Performance**: Optimized for distributed genomic data processing at scale
6. **Developer Experience**: Simple CLI, clear workflows, fast iteration

### Design Principles
1. **Working Simplicity Over Clever Design**: Prioritize clarity and maintainability
2. **Big Data Best Practices**: Proper partitioning, caching, and data skew handling
3. **ML Workflow Patterns**: Version control, experiment tracking, pipeline orchestration
4. **Configuration Over Code**: Externalize all settings, support multiple environments
5. **Fail Fast with Context**: Early validation with actionable error messages
6. **Data Locality First**: Co-locate computation and storage, minimize shuffles
7. **Immutable Infrastructure**: Containers as disposable, data as persistent
8. **Observable Systems**: Comprehensive logging, metrics, and monitoring hooks

---

## System Architecture

### High-Level Architecture

```
┌──────────────────────────────────────────────────────────────┐
│                   Docker Compose Stack                        │
└──────────────────────────────────────────────────────────────┘
                              │
                              │
        ┌─────────────────────┴─────────────────────┐
        │                                            │
┌───────▼─────────┐                      ┌──────────▼──────────┐
│  Spark Master   │                      │   Python CLI App    │
│  (Coordinator)  │◄─────────────────────┤   (Driver Process)  │
│  Port: 7077     │  Job Submission      │   Runs in Master    │
│  UI: 8080       │                      │   Container         │
└────────┬────────┘                      └─────────────────────┘
         │                                         │
         │ Schedule Tasks                          │ Read Config
         │                                         │ Submit Jobs
         ├──────────┬──────────┬──────────┐       │
         │          │          │          │       │
    ┌────▼───┐ ┌───▼────┐ ┌───▼────┐ ┌──▼─────┐ │
    │Worker 1│ │Worker 2│ │Worker 3│ │Worker N│ │
    │ 6GB RAM│ │ 6GB RAM│ │ 6GB RAM│ │ 6GB RAM│ │
    │ 4 cores│ │ 4 cores│ │ 4 cores│ │ 4 cores│ │
    └────┬───┘ └───┬────┘ └───┬────┘ └───┬────┘ │
         │         │          │          │       │
         └─────────┴──────────┴──────────┴───────┘
                              │
                    ┌─────────▼──────────┐
                    │  Shared Volumes    │
                    │  - /data/          │
                    │  - /results/       │
                    │  - /cache/         │
                    │  - /logs/          │
                    └────────────────────┘
```

### Simplified 3-Container Architecture

| Container | Purpose | Resources | Ports |
|-----------|---------|-----------|-------|
| `spark-master` | Spark cluster coordinator + Python CLI application driver | 4GB RAM, 2 CPU | 8080 (UI), 7077 (internal) |
| `spark-worker` (×N) | Distributed computation executors | 6GB RAM, 4 CPU each | None (internal only) |
| `postgres` (optional) | Metadata store for experiment tracking | 512MB RAM, 1 CPU | 5432 (internal) |

**Key Simplifications from v1.0:**
- ❌ **Removed Jupyter**: Eliminated web UI complexity, container overhead, and notebook versioning issues
- ❌ **Removed MinIO**: Direct file system access is simpler for development; add S3 when needed for production
- ✅ **Consolidated Driver**: Python CLI runs in spark-master container, reducing network hops
- ✅ **Increased Worker Resources**: Better resource allocation (6GB vs 4GB per worker)
- ✅ **Optional Metadata Store**: PostgreSQL for tracking runs (can use SQLite locally)

### Network Architecture

```
spark-network (Bridge Network)
├── spark-master.spark-network (driver + coordinator)
├── spark-worker-1.spark-network
├── spark-worker-2.spark-network
├── spark-worker-N.spark-network
└── postgres.spark-network (optional)
```

**Network Benefits**:
- Simplified topology: 3 container types vs 5
- Reduced inter-container communication overhead
- All Spark traffic stays within bridge network
- Single entry point for job submission (spark-master)
- No external ports exposed except monitoring UI

---

## Component Specifications

### 1. Spark Master Container (+ Python CLI Driver)

**Base Image**: `bitnami/spark:3.5.0`

**Rationale**: 
- Production-grade Spark distribution with proven stability
- Includes JVM optimization and proper signal handling
- Well-documented configuration surface
- Regular security updates

**Dual Role**:
1. **Spark Master**: Cluster coordinator, job scheduler, resource manager
2. **Application Driver**: Runs Python CLI application that submits jobs

**Custom Additions**:
```dockerfile
# Python 3.11 with scientific computing stack
FROM bitnami/spark:3.5.0

USER root

# Install Python 3.11 and system dependencies
RUN apt-get update && apt-get install -y \
    python3.11 \
    python3.11-venv \
    python3-pip \
    git \
    htop \
    && rm -rf /var/lib/apt/lists/*

# Python packages (pinned versions for reproducibility)
RUN pip3 install --no-cache-dir \
    pyspark==3.5.0 \
    biopython==1.81 \
    huggingface-hub==0.19.4 \
    pyarrow==14.0.1 \
    pandas==2.1.3 \
    numpy==1.24.3 \
    matplotlib==3.8.2 \
    seaborn==0.13.0 \
    click==8.1.7 \
    python-dotenv==1.0.0 \
    pyyaml==6.0.1 \
    pytest==7.4.3 \
    pytest-cov==4.1.0 \
    mlflow==2.9.2 \
    dvc==3.36.0

# Create application directory
RUN mkdir -p /opt/opengenome
WORKDIR /opt/opengenome

# Copy application code (done in docker-compose volume mount)
USER 1001
```

**Environment Configuration**:
```yaml
Environment:
  SPARK_MODE: master
  SPARK_MASTER_HOST: spark-master
  SPARK_MASTER_PORT: 7077
  
  # Resource Management
  SPARK_DRIVER_MEMORY: 3g
  SPARK_DRIVER_CORES: 2
  
  # Optimizations
  SPARK_RPC_MESSAGE_MAX_SIZE: 256
  SPARK_NETWORK_TIMEOUT: 800s
  SPARK_EXECUTOR_HEARTBEAT_INTERVAL: 60s
  
  # Locality
  SPARK_LOCALITY_WAIT: 3s
  
  # Python Environment
  PYSPARK_PYTHON: /usr/bin/python3.11
  PYSPARK_DRIVER_PYTHON: /usr/bin/python3.11
```

**Volume Mounts**:
```yaml
volumes:
  - ./src:/opt/opengenome/src:ro          # Application code (read-only)
  - ./data:/data                          # Datasets
  - ./results:/results                    # Outputs
  - ./cache:/cache                        # HuggingFace cache
  - ./logs:/opt/bitnami/spark/logs        # Spark logs
  - ./mlruns:/mlruns                      # MLflow tracking
```

**Exposed Ports**:
- `8080`: Spark Master Web UI (monitoring)
- `7077`: Spark Master RPC (internal)

### 2. Spark Worker Containers

**Base Image**: `bitnami/spark:3.5.0`

**Rationale**: Identical base ensures Python environment consistency

**Custom Additions**:
```dockerfile
FROM bitnami/spark:3.5.0

USER root

# Install Python 3.11
RUN apt-get update && apt-get install -y \
    python3.11 \
    python3-pip \
    && rm -rf /var/lib/apt/lists/*

# Install EXACT same Python packages as master
RUN pip3 install --no-cache-dir \
    pyspark==3.5.0 \
    biopython==1.81 \
    pyarrow==14.0.1 \
    pandas==2.1.3 \
    numpy==1.24.3

USER 1001
```

**Environment Configuration**:
```yaml
Environment:
  SPARK_MODE: worker
  SPARK_MASTER_URL: spark://spark-master:7077
  
  # Resource Allocation (per worker)
  SPARK_WORKER_MEMORY: 6g
  SPARK_WORKER_CORES: 4
  
  # Executor Configuration
  SPARK_EXECUTOR_MEMORY: 5g
  SPARK_EXECUTOR_CORES: 4
  
  # Memory Overhead (1GB for off-heap)
  SPARK_EXECUTOR_MEMORY_OVERHEAD: 1g
  
  # Python Environment
  PYSPARK_PYTHON: /usr/bin/python3.11
```

**Volume Mounts**:
```yaml
volumes:
  - ./data:/data:ro        # Read-only data access
  - ./cache:/cache         # Shared temporary storage
  - ./results:/results     # Write results
```

**Scaling Strategy**:
```bash
# Development: 2 workers (12GB total)
docker-compose up -d --scale spark-worker=2

# Production: Scale based on data volume
# Rule of thumb: 1 worker per 100GB of input data
docker-compose up -d --scale spark-worker=8
```

**Resource Calculation**:
- Each worker: 6GB RAM, 4 cores
- Executor gets: 5GB (6GB - 1GB overhead)
- Total cluster memory: N_workers × 5GB
- Total cluster cores: N_workers × 4

### 3. PostgreSQL Container (Optional - for Experiment Tracking)

**Base Image**: `postgres:16-alpine`

**Rationale**: 
- Lightweight metadata store for MLflow tracking
- Can be replaced with SQLite for local development
- Enables multi-user experiment tracking

**Configuration**:
```yaml
Environment:
  POSTGRES_DB: mlflow
  POSTGRES_USER: mlflow
  POSTGRES_PASSWORD: mlflow123
  PGDATA: /var/lib/postgresql/data/pgdata

Volume:
  - postgres-data:/var/lib/postgresql/data
```

**Usage**: MLflow backend store for tracking experiments, parameters, metrics, and artifacts

**When to Skip**: Use SQLite (`sqlite:///mlruns.db`) for single-user development

---

## Data Flow & Processing Pipeline

### Overview: Optimized Big Data Pipeline

The pipeline follows proven big data patterns:
1. **Ingest Once, Process Many**: Convert FASTA → Parquet once, reuse for all analyses
2. **Partition by Size**: Automatic partitioning based on data volume and cluster capacity
3. **Cache Strategically**: Cache hot datasets in memory with disk spillover
4. **Minimize Shuffles**: Use broadcast joins and map-side operations where possible
5. **Lazy Evaluation**: Build computation DAG, optimize before execution

### Stage 1: Data Ingestion (ETL)

```
HuggingFace → Download → Stream Parse → Batch → Write Parquet → Validate
    │            │           │            │          │             │
    │            │           │            │          │             └─→ Schema check
    │            │           │            │          └─→ Snappy compression
    │            │           │            └─→ 100K records/shard
    │            │           └─→ BioPython (streaming)
    │            └─→ Resume capability
    └─→ arcinstitute/opengenome2
```

**CLI Command**:
```bash
python -m opengenome ingest \
    --source huggingface \
    --repo arcinstitute/opengenome2 \
    --output /data/parquet/organelle \
    --shard-size 100000 \
    --compression snappy \
    --validate
```

**Implementation Details**:
```python
# Streaming parse (constant memory)
def ingest_fasta_to_parquet(
    fasta_path: Path,
    output_dir: Path,
    shard_size: int = 100_000,
    compression: str = "snappy"
) -> List[Path]:
    """
    Convert FASTA to Parquet shards with proper partitioning.
    
    Big Data Rationale:
    - Shard size 100K balances file count vs parallelism
    - Snappy compression: good speed/compression trade-off
    - Streaming prevents memory overflow on large FASTA files
    """
    writer = ParquetWriter(output_dir, compression=compression)
    buffer = []
    
    for record in SeqIO.parse(gzip.open(fasta_path, 'rt'), 'fasta'):
        buffer.append({
            'seq_id': record.id,
            'description': record.description,
            'length': len(record.seq),
            'sequence': str(record.seq).upper(),
            'source': 'organelle',
            'gc_content': calculate_gc(record.seq)  # Pre-compute for later
        })
        
        if len(buffer) >= shard_size:
            writer.write_shard(buffer)
            buffer.clear()
    
    if buffer:
        writer.write_shard(buffer)
    
    return writer.finalize()
```

**Parquet Schema** (optimized for queries):
```python
schema = pa.schema([
    ('seq_id', pa.string()),           # Indexed for lookups
    ('description', pa.string()),
    ('length', pa.int32()),            # Statistics column
    ('sequence', pa.string()),         # Large column - consider compression
    ('source', pa.string()),           # Partition key candidate
    ('gc_content', pa.float32()),      # Pre-computed metric
    ('_partition', pa.int32())         # Explicit partition ID
])
```

**Output Structure**:
```
/data/parquet/organelle/
├── _SUCCESS                           # Marker file
├── _metadata                          # Parquet metadata
├── part-00000.snappy.parquet         # 100K records
├── part-00001.snappy.parquet
├── ...
└── part-000NN.snappy.parquet
```

### Stage 2: Spark Data Loading (with Optimization)

```
Parquet → Spark Read → Predicate Pushdown → Repartition → Cache → Checkpoint
   │         │              │                    │           │         │
   │         │              │                    │           │         └─→ Fault tolerance
   │         │              │                    │           └─→ MEMORY_AND_DISK_SER
   │         │              │                    └─→ N_cores × 2-4
   │         │              └─→ Filter at storage layer
   │         └─→ Parallel read (one task per file)
   └─→ Columnar format
```

**CLI Command**:
```bash
python -m opengenome load \
    --input /data/parquet/organelle \
    --cache \
    --repartition auto \
    --checkpoint /cache/checkpoints/organelle
```

**Implementation** (with big data optimizations):
```python
def load_dataset(
    spark: SparkSession,
    path: str,
    repartition: Optional[int] = None,
    cache: bool = True
) -> DataFrame:
    """
    Load Parquet with optimizations.
    
    Big Data Optimizations:
    1. Predicate pushdown: filter before loading
    2. Partition pruning: only read needed files
    3. Adaptive partitioning: based on cluster size
    4. Serialized caching: reduce memory pressure
    """
    # Calculate optimal partitions
    if repartition == "auto":
        num_workers = len(spark.sparkContext.statusTracker().getExecutorInfos()) - 1
        cores_per_worker = int(spark.conf.get("spark.executor.cores", "4"))
        repartition = num_workers * cores_per_worker * 3  # 3× for better distribution
    
    df = (
        spark.read
        .parquet(path)
        .filter(F.col("length") >= 100)  # Predicate pushdown
        .repartition(repartition) if repartition else spark.read.parquet(path)
    )
    
    if cache:
        # Serialized caching saves memory
        df = df.persist(StorageLevel.MEMORY_AND_DISK_SER)
        df.count()  # Force caching
    
    return df
```

**Partitioning Strategy**:
```python
# Rule of thumb for genomic data
num_partitions = min(
    num_cores * 4,                    # Maximize parallelism
    total_sequences // 10_000,        # ~10K sequences per partition
    1000                              # Cap at 1000 partitions
)
```

### Stage 3: K-mer Analysis (Optimized MapReduce)

```
DataFrame → mapInPandas → Local Aggregation → Shuffle → Global Aggregation → Top-K
    │            │              │                 │            │               │
    │            └─→ Batch      └─→ Dict          └─→ Hash    └─→ Sum        └─→ Broadcast
    │                process        (in-memory)       partition    (combiner)     (small result)
    └─→ Cached
```

**CLI Command**:
```bash
python -m opengenome kmer \
    --input /data/parquet/organelle \
    --k 6 \
    --output /results/kmer_freq_k6.parquet \
    --top-n 1000
```

**Implementation** (optimized for genomics):
```python
def compute_kmer_frequencies(
    df: DataFrame,
    k: int = 6,
    top_n: int = 1000
) -> DataFrame:
    """
    Compute global k-mer frequencies with optimizations.
    
    Big Data Optimizations:
    1. Map-side aggregation: Reduce shuffle size by 100×
    2. Custom partitioner: Handle skewed k-mer distribution
    3. Combiner: Pre-aggregate before shuffle
    4. No explode: Process all k-mers in single pass
    """
    
    # Schema for map output
    schema = StructType([
        StructField("kmer", StringType(), False),
        StructField("count", LongType(), False)
    ])
    
    # Map function with local aggregation
    def extract_and_count_kmers(iterator: Iterator[pd.DataFrame]) -> Iterator[pd.DataFrame]:
        """
        Process partition, emit k-mer counts (map-side combine).
        
        Memory-efficient: Uses dict for O(1) lookup, 
        processes batch-by-batch to stay within memory limits.
        """
        partition_counts = {}  # Aggregate entire partition
        
        for batch in iterator:
            for sequence in batch['sequence']:
                seq = sequence.upper()
                seq_len = len(seq)
                
                # Vectorized k-mer extraction
                for i in range(seq_len - k + 1):
                    kmer = seq[i:i+k]
                    
                    # Filter invalid k-mers
                    if 'N' not in kmer:
                        partition_counts[kmer] = partition_counts.get(kmer, 0) + 1
        
        # Emit partition aggregates (much smaller than per-sequence)
        if partition_counts:
            yield pd.DataFrame({
                'kmer': list(partition_counts.keys()),
                'count': list(partition_counts.values())
            })
    
    # Execute MapReduce
    kmer_df = (
        df.mapInPandas(extract_and_count_kmers, schema)
        .groupBy('kmer')
        .agg(F.sum('count').alias('count'))  # Shuffle + reduce
        .orderBy(F.desc('count'))
        .limit(top_n)
    )
    
    # Broadcast small result for future joins
    kmer_df.cache()
    kmer_df.count()  # Materialize
    
    return kmer_df

# Performance: ~10M sequences → 4^6 = 4096 possible 6-mers
# Map output: ~4000 rows per partition (vs 10M without aggregation)
# Shuffle reduction: 2500× smaller
```

**Advanced: Per-Sequence K-mer Vectors** (for similarity search):
```python
def compute_sequence_kmer_vectors(
    df: DataFrame,
    k: int = 6,
    use_tfidf: bool = True
) -> DataFrame:
    """
    Compute k-mer TF or TF-IDF vectors per sequence.
    
    Big Data Challenge: Potentially huge output (N_seq × N_kmer)
    Solution: Sparse representation, only non-zero k-mers
    """
    
    schema = StructType([
        StructField("seq_id", StringType(), False),
        StructField("kmer", StringType(), False),
        StructField("tf", DoubleType(), False)
    ])
    
    def compute_tf_vector(iterator: Iterator[pd.DataFrame]) -> Iterator[pd.DataFrame]:
        """Emit sparse TF vectors (seq_id, kmer, tf)"""
        for batch in iterator:
            results = []
            
            for _, row in batch.iterrows():
                seq_id = row['seq_id']
                sequence = row['sequence'].upper()
                seq_len = len(sequence)
                
                kmer_counts = {}
                for i in range(seq_len - k + 1):
                    kmer = sequence[i:i+k]
                    if 'N' not in kmer:
                        kmer_counts[kmer] = kmer_counts.get(kmer, 0) + 1
                
                # Normalize to TF
                total = sum(kmer_counts.values())
                for kmer, count in kmer_counts.items():
                    results.append({
                        'seq_id': seq_id,
                        'kmer': kmer,
                        'tf': count / total
                    })
            
            if results:
                yield pd.DataFrame(results)
    
    tf_df = df.mapInPandas(compute_tf_vector, schema)
    
    if use_tfidf:
        # Compute IDF
        num_docs = df.count()
        idf_df = (
            tf_df.groupBy('kmer')
            .agg(F.countDistinct('seq_id').alias('df'))
            .withColumn('idf', F.log((F.lit(num_docs) + 1) / (F.col('df') + 1)) + 1)
            .select('kmer', 'idf')
        )
        
        # Join and compute TF-IDF (broadcast IDF - small table)
        tfidf_df = (
            tf_df.join(F.broadcast(idf_df), on='kmer', how='inner')
            .withColumn('tfidf', F.col('tf') * F.col('idf'))
            .select('seq_id', 'kmer', 'tfidf')
        )
        
        return tfidf_df
    
    return tf_df
```

### Stage 4: Codon Usage Analysis

```
Sequences → Extract Codons → Count by Codon → Frequency Calculation → RSCU
    │            │                 │                  │                  │
    └─→ Frame 0  └─→ Triplets     └─→ Global sum    └─→ freq = c/Σc   └─→ Relative
        only         (no explode)                                           usage
```

**Processing**:
1. Filter sequences with length ≥ 3
2. Extract codons: `sequence[0::3]`, `sequence[1::3]`, `sequence[2::3]`
3. For frame 0: use SQL `substring(sequence, i+1, 3)` with `sequence(0, length-3, 3)`
4. Filter out codons containing 'N'
5. Aggregate counts globally
6. Calculate frequencies and RSCU metrics

### Stage 5: Sequence Similarity Search

```
Query Seq → K-mer Vector → TF-IDF Weights → Cosine Similarity → Top-N Results
    │           │               │                  │                  │
    └─→ Parse   └─→ {kmer: tf}  └─→ tf * idf      └─→ dot(q,d)/     └─→ Ranked
                                                        (||q||·||d||)     sequences
```

**Components**:
1. **TF Matrix**: Per-sequence k-mer counts
2. **IDF Vector**: `idf(kmer) = log((N+1)/(df+1)) + 1`
3. **Query Processing**: Convert query to k-mer vector
4. **Similarity Computation**: Spark join on k-mer, compute dot products
5. **Ranking**: Order by cosine similarity descending

### Stage 6: Visualization & Reporting

```
Analysis Results → Aggregate → Plot → Save PNG/HTML → /results/
       │              │          │         │              │
       └─→ Spark DF   └─→ Small  └─→ MPL  └─→ High-res  └─→ figures/
                          .toPandas()         images          reports/
```

**Outputs**:
- GC content histogram
- Top-K k-mer bar charts
- Codon frequency plots
- RSCU analysis
- Codon usage heatmap
- Summary statistics (JSON/CSV)

---

## File Structure & Organization

```
opengenome2-project/
│
├── docker/                              # Docker configurations
│   ├── spark-master/
│   │   ├── Dockerfile                   # Master + driver container
│   │   └── spark-defaults.conf          # Spark configuration
│   ├── spark-worker/
│   │   ├── Dockerfile                   # Worker container
│   │   └── requirements.txt             # Python dependencies
│   └── postgres/
│       └── init.sql                     # MLflow DB schema
│
├── src/                                 # Python application (CLI-based)
│   ├── opengenome/
│   │   ├── __init__.py
│   │   ├── __main__.py                  # CLI entry point
│   │   ├── config.py                    # Configuration management
│   │   ├── logging.py                   # Logging setup
│   │   │
│   │   ├── cli/                         # Command-line interface
│   │   │   ├── __init__.py
│   │   │   ├── main.py                  # Click CLI app
│   │   │   ├── ingest.py                # Ingest command
│   │   │   ├── analyze.py               # Analysis commands
│   │   │   ├── search.py                # Search command
│   │   │   └── pipeline.py              # Full pipeline command
│   │   │
│   │   ├── ingestion/
│   │   │   ├── __init__.py
│   │   │   ├── downloader.py            # HuggingFace download
│   │   │   ├── fasta_parser.py          # Streaming FASTA parser
│   │   │   └── parquet_writer.py        # Efficient Parquet writer
│   │   │
│   │   ├── analysis/
│   │   │   ├── __init__.py
│   │   │   ├── kmer.py                  # K-mer analysis
│   │   │   ├── codon.py                 # Codon usage analysis
│   │   │   ├── statistics.py            # GC%, length dist, etc.
│   │   │   └── search.py                # Similarity search
│   │   │
│   │   ├── spark/
│   │   │   ├── __init__.py
│   │   │   ├── session.py               # SparkSession factory
│   │   │   ├── optimize.py              # Performance tuning
│   │   │   └── monitoring.py            # Job monitoring
│   │   │
│   │   ├── visualization/
│   │   │   ├── __init__.py
│   │   │   ├── plots.py                 # Matplotlib plots
│   │   │   ├── dashboards.py            # Summary dashboards
│   │   │   └── styles.py                # Consistent styling
│   │   │
│   │   ├── ml/                          # ML workflow utilities
│   │   │   ├── __init__.py
│   │   │   ├── tracking.py              # MLflow integration
│   │   │   ├── versioning.py            # Data/model versioning
│   │   │   └── experiments.py           # Experiment management
│   │   │
│   │   └── utils/
│   │       ├── __init__.py
│   │       ├── validation.py            # Input validation
│   │       ├── io_utils.py              # File I/O helpers
│   │       └── bio_utils.py             # Biological computation
│   │
│   ├── setup.py                         # Package installation
│   ├── requirements.txt                 # Python dependencies
│   └── pyproject.toml                   # Modern Python packaging
│
├── tests/                               # Comprehensive test suite
│   ├── __init__.py
│   ├── conftest.py                      # Pytest fixtures
│   │
│   ├── unit/                            # Unit tests
│   │   ├── test_config.py
│   │   ├── test_ingestion.py
│   │   ├── test_kmer.py
│   │   ├── test_codon.py
│   │   └── test_search.py
│   │
│   ├── integration/                     # Integration tests
│   │   ├── test_pipeline.py
│   │   ├── test_spark_session.py
│   │   └── test_end_to_end.py
│   │
│   ├── data/                            # Test fixtures
│   │   ├── sample.fasta
│   │   └── expected_output.parquet
│   │
│   └── performance/                     # Performance benchmarks
│       └── test_scaling.py
│
├── experiments/                         # Experiment tracking
│   ├── configs/                         # Experiment configurations
│   │   ├── baseline.yaml
│   │   └── optimized.yaml
│   └── notebooks/                       # Optional: exploration notebooks
│       └── analysis.ipynb               # For adhoc exploration only
│
├── data/                                # Data directory (gitignored)
│   ├── raw/                            # Original FASTA files
│   ├── parquet/                        # Converted datasets
│   │   └── organelle/                  # Partitioned by source
│   ├── processed/                      # Analysis results
│   └── samples/                        # Small test datasets
│
├── results/                             # Output directory (gitignored)
│   ├── kmer_analysis/
│   ├── codon_analysis/
│   ├── search_results/
│   ├── figures/
│   └── reports/
│
├── cache/                               # Cache directory (gitignored)
│   ├── huggingface/                    # HF Hub cache
│   └── checkpoints/                    # Spark checkpoints
│
├── logs/                                # Log directory (gitignored)
│   ├── spark/                          # Spark application logs
│   └── application/                    # CLI application logs
│
├── mlruns/                              # MLflow tracking (gitignored)
│   └── experiments/
│
├── scripts/                             # Utility scripts
│   ├── setup.sh                        # Initial setup
│   ├── create_sample_data.py           # Generate test data
│   ├── validate_environment.sh         # Pre-flight checks
│   ├── benchmark.sh                    # Performance testing
│   └── export_results.py               # Export to various formats
│
├── docs/                                # Documentation
│   ├── architecture.md                 # System design
│   ├── api.md                          # CLI API reference
│   ├── development.md                  # Development guide
│   ├── deployment.md                   # Deployment guide
│   ├── performance_tuning.md           # Optimization guide
│   └── troubleshooting.md
│
├── .github/                             # CI/CD
│   └── workflows/
│       ├── test.yml
│       └── build.yml
│
├── .env.example                         # Environment template
├── .gitignore
├── docker-compose.yml                   # Production config
├── docker-compose.dev.yml               # Development overrides
├── Makefile                             # Common operations
├── README.md                            # Project overview
├── DESIGN.md                            # This document
├── CHANGELOG.md                         # Version history
└── LICENSE
```

### Directory Purpose & Guidelines

| Directory | Purpose | Gitignored | Volume Mount | Notes |
|-----------|---------|------------|--------------|-------|
| `docker/` | Container definitions | No | No | Build context |
| `src/opengenome/` | CLI application code | No | Yes (`/opt/opengenome/src`) | Mounted for live dev |
| `tests/` | Test suite | No | Yes | Run tests in container |
| `experiments/` | Experiment configs | No | Yes | YAML configs for runs |
| `data/` | Datasets | Yes | Yes (`/data`) | Large files (GB-TB) |
| `results/` | Analysis outputs | Yes | Yes (`/results`) | Gitignore, DVC track |
| `cache/` | Temporary cache | Yes | Yes (`/cache`) | Safe to delete |
| `logs/` | Application logs | Yes | Yes (`/logs`) | Rotate regularly |
| `mlruns/` | MLflow tracking | Yes | Yes (`/mlruns`) | Experiment artifacts |
| `scripts/` | Automation utilities | No | No | Bash/Python helpers |
| `docs/` | Documentation | No | No | Markdown files |

---

## CLI Application Design

### Command Structure

The application uses **Click** for a hierarchical CLI with clear, composable commands:

```bash
# Main command groups
opengenome ingest    # Data ingestion commands
opengenome analyze   # Analysis commands
opengenome search    # Sequence search
opengenome pipeline  # Full pipeline execution
opengenome validate  # Environment validation
opengenome info      # System information

# Example workflows
opengenome ingest fasta --input /data/raw/organelle.fasta.gz --output /data/parquet/organelle
opengenome analyze kmer --input /data/parquet/organelle --k 6 --output /results/kmer_k6
opengenome analyze codon --input /data/parquet/organelle --output /results/codon
opengenome search similar --query "ATGCGATCG..." --index /results/kmer_k6 --top-n 20
opengenome pipeline run --config experiments/configs/baseline.yaml
```

### Command Reference

#### 1. Data Ingestion

```bash
# Ingest FASTA to Parquet
opengenome ingest fasta \
    --input PATH            # Input FASTA file (gzipped or plain)
    --output PATH           # Output Parquet directory
    --shard-size INT        # Records per shard (default: 100000)
    --compression STR       # Compression: snappy, gzip, lz4 (default: snappy)
    --filter-n              # Filter sequences with 'N' bases
    --validate              # Validate output schema
    --workers INT           # Parallel write workers (default: 4)

# Download from HuggingFace
opengenome ingest download \
    --repo STR              # HuggingFace repo (default: arcinstitute/opengenome2)
    --output PATH           # Output directory
    --cache-dir PATH        # Cache directory (default: /cache/huggingface)
```

#### 2. Analysis Commands

```bash
# K-mer frequency analysis
opengenome analyze kmer \
    --input PATH            # Input Parquet directory
    --output PATH           # Output Parquet file
    --k INT                 # K-mer size (default: 6)
    --top-n INT             # Return top N k-mers (default: 1000)
    --per-sequence          # Compute per-sequence vectors (for search)
    --tfidf                 # Compute TF-IDF weights
    --plot                  # Generate frequency plot

# Codon usage analysis
opengenome analyze codon \
    --input PATH            # Input Parquet directory
    --output PATH           # Output Parquet file
    --frame INT             # Reading frame: 0, 1, 2 (default: 0)
    --rscu                  # Compute RSCU values
    --genetic-code INT      # Genetic code table (default: 1 - standard)
    --plot                  # Generate codon usage heatmap

# Statistics
opengenome analyze stats \
    --input PATH            # Input Parquet directory
    --output PATH           # Output JSON/CSV file
    --metrics STR           # Comma-separated: gc,length,ambiguous
    --plot                  # Generate distribution plots
```

#### 3. Search Commands

```bash
# Similarity search
opengenome search similar \
    --query STR or PATH     # Query sequence or FASTA file
    --index PATH            # K-mer TF-IDF index directory
    --top-n INT             # Return top N results (default: 20)
    --threshold FLOAT       # Minimum similarity (0.0-1.0)
    --output PATH           # Output results

# Exact k-mer match
opengenome search kmer \
    --kmer STR              # K-mer to search
    --index PATH            # K-mer index directory
    --min-count INT         # Minimum k-mer count
    --output PATH           # Output results
```

#### 4. Pipeline Command

```bash
# Run complete pipeline from config
opengenome pipeline run \
    --config PATH           # YAML configuration file
    --experiment STR        # Experiment name (for MLflow)
    --workers INT           # Spark worker count
    --dry-run               # Show plan without execution

# Generate pipeline config template
opengenome pipeline init \
    --output PATH           # Output YAML file
    --template STR          # Template: baseline, optimized, minimal
```

#### 5. Utility Commands

```bash
# Validate environment
opengenome validate \
    --check spark           # Check Spark connectivity
    --check storage         # Check volumes
    --check dependencies    # Check Python packages

# System information
opengenome info \
    --spark                 # Show Spark cluster info
    --storage               # Show storage usage
    --config                # Show current configuration
```

### Pipeline Configuration (YAML)

**Example**: `experiments/configs/baseline.yaml`

```yaml
name: baseline_organelle_analysis
description: Baseline k-mer and codon analysis on organelle sequences

# Input data
input:
  source: huggingface
  repo: arcinstitute/opengenome2
  cache: /cache/huggingface

# Ingestion stage
ingestion:
  output: /data/parquet/organelle
  shard_size: 100000
  compression: snappy
  validate: true

# Analysis stages
analysis:
  kmer:
    enabled: true
    k_values: [6, 7, 8]
    top_n: 1000
    per_sequence: true
    tfidf: true
    output: /results/kmer

  codon:
    enabled: true
    frame: 0
    rscu: true
    genetic_code: 1
    output: /results/codon

  statistics:
    enabled: true
    metrics: [gc, length, ambiguous]
    output: /results/stats

# Search index
search_index:
  enabled: true
  k: 6
  index_type: tfidf
  output: /results/search_index

# Visualization
visualization:
  enabled: true
  plots:
    - kmer_frequency
    - codon_usage_heatmap
    - gc_distribution
    - length_distribution
  output: /results/figures
  format: png
  dpi: 300

# Spark configuration
spark:
  executor_memory: 5g
  executor_cores: 4
  shuffle_partitions: auto  # Based on data size
  dynamic_allocation: true

# MLflow tracking
mlflow:
  enabled: true
  tracking_uri: sqlite:////mlruns/mlflow.db
  experiment_name: opengenome_baseline
  log_params: true
  log_metrics: true
  log_artifacts: true

# Performance
performance:
  cache_input: true
  checkpoint_interval: 100  # Iterations
  optimize_joins: true
```

---

## Configuration Management

### Environment Variables (.env)

```bash
# ===== Spark Configuration =====
SPARK_MASTER=spark://spark-master:7077
SPARK_DRIVER_MEMORY=3g
SPARK_EXECUTOR_MEMORY=5g
SPARK_EXECUTOR_CORES=4
SPARK_SQL_SHUFFLE_PARTITIONS=auto

# ===== Paths =====
DATA_DIR=/data
RESULTS_DIR=/results
CACHE_DIR=/cache
LOGS_DIR=/logs

# ===== Data Processing =====
SHARD_SIZE=100000
K_MER_DEFAULT=6
COMPRESSION=snappy

# ===== HuggingFace =====
HF_REPO=arcinstitute/opengenome2
HF_CACHE_DIR=/cache/huggingface
HF_TOKEN=  # Optional, for private repos

# ===== MLflow =====
MLFLOW_TRACKING_URI=sqlite:////mlruns/mlflow.db
MLFLOW_EXPERIMENT_NAME=opengenome
MLFLOW_ARTIFACT_ROOT=/mlruns/artifacts

# ===== Performance =====
ENABLE_ADAPTIVE_EXECUTION=true
ENABLE_DYNAMIC_ALLOCATION=true
CACHE_STRATEGY=memory_and_disk_ser

# ===== Logging =====
LOG_LEVEL=INFO
LOG_FORMAT=json  # json or text
SPARK_LOG_LEVEL=WARN

# ===== Development =====
DEBUG=false
SAMPLE_MODE=false
SAMPLE_SIZE=5000
```

### Python Config Class

**File**: `src/opengenome/config.py`

```python
"""
Configuration management with environment-specific overrides.
"""

import os
from pathlib import Path
from typing import List, Optional, Dict, Any
from dataclasses import dataclass, field
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

@dataclass
class SparkConfig:
    """Spark cluster configuration"""
    master: str = os.getenv("SPARK_MASTER", "local[*]")
    app_name: str = "OpenGenome"
    driver_memory: str = os.getenv("SPARK_DRIVER_MEMORY", "3g")
    executor_memory: str = os.getenv("SPARK_EXECUTOR_MEMORY", "5g")
    executor_cores: int = int(os.getenv("SPARK_EXECUTOR_CORES", "4"))
    sql_shuffle_partitions: str = os.getenv("SPARK_SQL_SHUFFLE_PARTITIONS", "auto")
    dynamic_allocation: bool = os.getenv("ENABLE_DYNAMIC_ALLOCATION", "true").lower() == "true"
    adaptive_execution: bool = os.getenv("ENABLE_ADAPTIVE_EXECUTION", "true").lower() == "true"
    
    def to_spark_conf(self) -> Dict[str, str]:
        """Convert to Spark configuration dict"""
        conf = {
            "spark.driver.memory": self.driver_memory,
            "spark.executor.memory": self.executor_memory,
            "spark.executor.cores": str(self.executor_cores),
            "spark.sql.adaptive.enabled": str(self.adaptive_execution).lower(),
            "spark.dynamicAllocation.enabled": str(self.dynamic_allocation).lower(),
        }
        
        if self.sql_shuffle_partitions != "auto":
            conf["spark.sql.shuffle.partitions"] = self.sql_shuffle_partitions
        
        return conf

@dataclass
class PathConfig:
    """File system paths"""
    data_dir: Path = Path(os.getenv("DATA_DIR", "/data"))
    results_dir: Path = Path(os.getenv("RESULTS_DIR", "/results"))
    cache_dir: Path = Path(os.getenv("CACHE_DIR", "/cache"))
    logs_dir: Path = Path(os.getenv("LOGS_DIR", "/logs"))
    
    @property
    def raw_data(self) -> Path:
        return self.data_dir / "raw"
    
    @property
    def parquet_data(self) -> Path:
        return self.data_dir / "parquet"
    
    @property
    def results_kmer(self) -> Path:
        return self.results_dir / "kmer_analysis"
    
    @property
    def results_codon(self) -> Path:
        return self.results_dir / "codon_analysis"
    
    @property
    def figures(self) -> Path:
        return self.results_dir / "figures"
    
    def create_all(self):
        """Create all necessary directories"""
        for path in [
            self.data_dir, self.results_dir, self.cache_dir, self.logs_dir,
            self.raw_data, self.parquet_data, self.results_kmer, 
            self.results_codon, self.figures
        ]:
            path.mkdir(parents=True, exist_ok=True)

@dataclass
class ProcessingConfig:
    """Data processing parameters"""
    shard_size: int = int(os.getenv("SHARD_SIZE", "100000"))
    k_mer_default: int = int(os.getenv("K_MER_DEFAULT", "6"))
    compression: str = os.getenv("COMPRESSION", "snappy")
    cache_strategy: str = os.getenv("CACHE_STRATEGY", "memory_and_disk_ser")
    
@dataclass
class MLflowConfig:
    """MLflow experiment tracking"""
    tracking_uri: str = os.getenv("MLFLOW_TRACKING_URI", "sqlite:////mlruns/mlflow.db")
    experiment_name: str = os.getenv("MLFLOW_EXPERIMENT_NAME", "opengenome")
    artifact_root: str = os.getenv("MLFLOW_ARTIFACT_ROOT", "/mlruns/artifacts")
    enabled: bool = True

@dataclass
class Config:
    """Main application configuration"""
    spark: SparkConfig = field(default_factory=SparkConfig)
    paths: PathConfig = field(default_factory=PathConfig)
    processing: ProcessingConfig = field(default_factory=ProcessingConfig)
    mlflow: MLflowConfig = field(default_factory=MLflowConfig)
    
    # Development flags
    debug: bool = os.getenv("DEBUG", "false").lower() == "true"
    sample_mode: bool = os.getenv("SAMPLE_MODE", "false").lower() == "true"
    sample_size: int = int(os.getenv("SAMPLE_SIZE", "5000"))
    
    # Logging
    log_level: str = os.getenv("LOG_LEVEL", "INFO")
    log_format: str = os.getenv("LOG_FORMAT", "json")
    
    def validate(self):
        """Validate configuration and create directories"""
        self.paths.create_all()
        
        if self.sample_mode:
            print(f"⚠️  Running in SAMPLE MODE ({self.sample_size} sequences)")
        
        return self
    
    @classmethod
    def from_yaml(cls, path: Path) -> 'Config':
        """Load configuration from YAML file"""
        import yaml
        with open(path) as f:
            data = yaml.safe_load(f)
        # TODO: Implement YAML override logic
        return cls()

# Global config instance
config = Config().validate()
```

---

## ML Workflow & Reproducibility

### Experiment Tracking with MLflow

**Integration**: MLflow tracks all pipeline runs with parameters, metrics, and artifacts

```python
# src/opengenome/ml/tracking.py
import mlflow
from opengenome.config import config

def start_run(experiment_name: str, run_name: str = None):
    """Start MLflow tracking run"""
    mlflow.set_tracking_uri(config.mlflow.tracking_uri)
    mlflow.set_experiment(experiment_name)
    return mlflow.start_run(run_name=run_name)

# Usage in pipeline
with start_run("kmer_analysis", "k6_baseline"):
    mlflow.log_param("k_mer_size", 6)
    mlflow.log_param("shard_size", 100000)
    mlflow.log_param("compression", "snappy")
    
    # Run analysis
    result = compute_kmer_frequencies(df, k=6)
    
    # Log metrics
    mlflow.log_metric("total_kmers", result.count())
    mlflow.log_metric("unique_kmers", result.select("kmer").distinct().count())
    mlflow.log_metric("runtime_seconds", elapsed_time)
    
    # Log artifacts
    mlflow.log_artifact("/results/kmer_freq_k6.parquet")
    mlflow.log_artifact("/results/figures/kmer_dist.png")
```

### Data Versioning with DVC

**Rationale**: Track large datasets separately from Git

```bash
# Initialize DVC in project
dvc init

# Track data directories
dvc add data/parquet/organelle
dvc add results/kmer_analysis

# Commit DVC metafiles to Git
git add data/parquet/organelle.dvc results/kmer_analysis.dvc
git commit -m "Track data with DVC"

# Push data to remote storage (S3/GCS/Azure)
dvc remote add -d storage s3://opengenome-data
dvc push
```

### Reproducible Runs

```bash
# Run with explicit versioning
opengenome pipeline run \
    --config experiments/configs/baseline.yaml \
    --experiment baseline_v1 \
    --git-commit $(git rev-parse HEAD) \
    --data-version $(git rev-parse HEAD:data.dvc)

# Reproduce exact run later
git checkout <commit-hash>
dvc checkout
opengenome pipeline run --config experiments/configs/baseline.yaml
```

### Environment Reproducibility

```dockerfile
# docker/spark-master/Dockerfile
# Pin all package versions
FROM bitnami/spark:3.5.0

# Exact Python version
RUN apt-get update && apt-get install -y python3.11=3.11.6-1

# Pinned dependencies
COPY requirements.lock .
RUN pip install --no-cache-dir -r requirements.lock

# Lock file generated with pip-compile
# requirements.lock contains transitive dependencies with hashes
```

---

## Development Workflow

### Setup & Installation

```bash
# 1. Clone repository
git clone https://github.com/org/opengenome2.git
cd opengenome2

# 2. Copy environment template
cp .env.example .env
# Edit .env with your settings

# 3. Build Docker images
make build

# 4. Start services
make up

# 5. Validate environment
make validate

# 6. Run tests
make test
```

### Development Loop

```bash
# === Development with Live Code Reload ===

# Start services with code mounted as volume
docker-compose -f docker-compose.dev.yml up -d

# Code changes immediately reflected (no rebuild needed)
# Edit src/opengenome/**/*.py

# Run CLI inside container
docker exec -it spark-master python -m opengenome analyze kmer --help

# Or shell into container for interactive development
make shell

# === Testing ===

# Run unit tests
make test-unit

# Run integration tests (slower, needs Spark)
make test-integration

# Run with coverage
make test-coverage

# === Debugging ===

# View logs
make logs

# View Spark UI
open http://localhost:8080

# Check Spark job progress
make spark-status
```

### Code Quality
   # Clone repository
   git clone <repo-url>
   cd opengenome2-project
   
   # Create environment file
   cp .env.example .env
   # Edit .env as needed
   
   # Build containers
   make build
   
   # Start services
   make up
   ```

2. **Development Cycle**:
   ```bash
   # Open Jupyter Lab
   open http://localhost:8888
   
   # Check Spark UI
   open http://localhost:8080
   
   # Work in notebooks or edit src/
   # Changes to notebooks are auto-saved
   # Changes to src/ require container restart
   
   # View logs
   make logs
   
   # Run tests
   make test
   ```

3. **Iterative Development**:
   - Write code in notebooks for experimentation
   - Extract stable functions to `src/` modules
   - Import from `src/` in notebooks: `from src.analysis import kmer`
   - Write tests in `tests/`
   - Run tests before committing

4. **Debugging**:
   ```bash
   # Shell into containers
   docker exec -it opengenome-jupyter bash
   docker exec -it opengenome-spark-master bash
   
   # View Spark logs
   docker logs opengenome-spark-worker-1
   
   # Check resource usage
   docker stats
   ```

### Makefile Commands

```makefile
# Build
build:         Build all Docker images
rebuild:       Force rebuild without cache

# Service Management  
up:            Start all services
down:          Stop all services
restart:       Restart all services
scale:         Scale workers (e.g., make scale workers=4)

# Development
shell:         Open shell in master container
logs:          Tail logs from all services
logs-spark:    View Spark logs only
clean:         Remove containers, volumes, and cache

# Execution
run-pipeline:  Run full analysis pipeline
run-kmer:      Run k-mer analysis only
run-codon:     Run codon analysis only

# Testing
test:          Run all tests
test-unit:     Run unit tests only
test-int:      Run integration tests
test-coverage: Run with coverage report

# Validation
validate:      Check environment setup
spark-status:  Show Spark cluster status
storage-info:  Show disk usage

# Data
download:      Download dataset from HuggingFace
create-sample: Generate test data
```

---

## Testing Strategy

### Test Pyramid

```
               /\
              /  \  Unit Tests (fast, many)
             /────\  ~200 tests, <10 sec
            /      \  
           / Component \ Integration Tests
          /   Tests     \ (medium, some)
         /--------------\ ~50 tests, <2 min
        /                \
       /   Integration     \ End-to-End
      /      Tests          \ (slow, few)
     /______________________\ ~10 tests, <10 min
```

### Unit Tests (Pure Functions)

**Coverage Target**: >80% for business logic

```python
# tests/unit/test_kmer.py
import pytest
from opengenome.analysis.kmer import extract_kmers, count_kmers

def test_extract_kmers_simple():
    sequence = "ATGCATGC"
    k = 3
    result = extract_kmers(sequence, k)
    expected = ["ATG", "TGC", "GCA", "CAT", "ATG", "TGC"]
    assert result == expected

def test_extract_kmers_filter_n():
    sequence = "ATGNCATGC"
    k = 3
    result = extract_kmers(sequence, k, filter_n=True)
    assert "TGN" not in result
    assert "GNC" not in result

def test_count_kmers():
    kmers = ["ATG", "ATG", "TGC", "TGC", "TGC"]
    result = count_kmers(kmers)
    assert result == {"ATG": 2, "TGC": 3}

@pytest.mark.parametrize("k,expected_count", [
    (3, 6), (4, 5), (5, 4), (6, 3)
])
def test_kmer_counts_for_different_k(k, expected_count):
    sequence = "ATGCATGC"
    kmers = extract_kmers(sequence, k)
    assert len(kmers) == expected_count
```

### Component Tests (Spark Operations)

**Strategy**: Test Spark functions with local Spark session

```python
# tests/integration/test_spark_kmer.py
import pytest
from pyspark.sql import SparkSession
from opengenome.analysis.kmer import compute_kmer_frequencies

@pytest.fixture(scope="module")
def spark():
    """Create local Spark session for tests"""
    spark = (
        SparkSession.builder
        .master("local[2]")
        .appName("test")
        .config("spark.driver.memory", "1g")
        .getOrCreate()
    )
    yield spark
    spark.stop()

@pytest.fixture
def sample_sequences(spark):
    """Create sample DataFrame"""
    data = [
        ("seq1", "ATGCATGC"),
        ("seq2", "GCTAGCTA"),
        ("seq3", "TTAATTAA")
    ]
    return spark.createDataFrame(data, ["seq_id", "sequence"])

def test_compute_kmer_frequencies(spark, sample_sequences):
    result = compute_kmer_frequencies(sample_sequences, k=3)
    
    # Verify schema
    assert set(result.columns) == {"kmer", "count"}
    
    # Verify results
    result_dict = {row.kmer: row.count for row in result.collect()}
    assert result_dict["ATG"] == 2  # Appears in seq1 twice
    assert result_dict["GCT"] == 1  # Appears in seq2
    
    # Verify no N-containing k-mers
    assert all('N' not in kmer for kmer in result_dict.keys())

def test_kmer_frequency_top_n(spark, sample_sequences):
    result = compute_kmer_frequencies(sample_sequences, k=3, top_n=5)
    assert result.count() <= 5
    
    # Verify ordering (descending by count)
    counts = [row.count for row in result.collect()]
    assert counts == sorted(counts, reverse=True)
```

### Integration Tests (Full Pipeline)

```python
# tests/integration/test_end_to_end.py
import pytest
from pathlib import Path
from opengenome.cli.pipeline import run_pipeline

@pytest.fixture
def test_config(tmp_path):
    """Create test configuration"""
    config = {
        "input": {"source": "file", "path": str(tmp_path / "test.fasta")},
        "ingestion": {"output": str(tmp_path / "parquet")},
        "analysis": {
            "kmer": {"enabled": True, "k_values": [3], "output": str(tmp_path / "kmer")},
            "codon": {"enabled": True, "output": str(tmp_path / "codon")}
        }
    }
    return config

def test_full_pipeline(test_config, sample_fasta_file):
    """Test complete pipeline execution"""
    # Run pipeline
    result = run_pipeline(test_config)
    
    # Verify outputs exist
    assert result["status"] == "success"
    assert Path(test_config["analysis"]["kmer"]["output"]).exists()
    assert Path(test_config["analysis"]["codon"]["output"]).exists()
    
    # Verify metrics
    assert result["metrics"]["sequences_processed"] > 0
    assert result["metrics"]["kmers_counted"] > 0
```

### Performance Tests

```python
# tests/performance/test_scaling.py
import pytest
import time
from opengenome.analysis.kmer import compute_kmer_frequencies

@pytest.mark.slow
@pytest.mark.parametrize("num_sequences", [100, 1000, 10000])
def test_kmer_scaling(spark, num_sequences):
    """Test performance scales linearly"""
    # Generate test data
    df = generate_synthetic_data(spark, num_sequences=num_sequences)
    
    start = time.time()
    result = compute_kmer_frequencies(df, k=6)
    result.count()  # Trigger computation
    elapsed = time.time() - start
    
    # Performance assertion (should be < 1 sec per 1000 sequences)
    assert elapsed < (num_sequences / 1000) * 1.5
```

### Test Pyramid

```
         ┌─────────────────┐
         │  Integration    │  ← Fewer, slower (full pipeline)
         │  Tests          │
         ├─────────────────┤
         │  Component      │  ← Medium number, medium speed
         │  Tests          │
         ├─────────────────┤
         │  Unit           │  ← Many, fast (pure functions)
         │  Tests          │
         └─────────────────┘
```

### Unit Tests

**Target**: Pure functions in `src/` modules

**Tools**: pytest, pytest-cov

**Example** (`tests/test_kmer.py`):
```python
import pytest
from src.analysis.kmer import extract_kmers, count_kmers

def test_extract_kmers_basic():
    sequence = "ATGCGT"
    kmers = extract_kmers(sequence, k=3)
    assert kmers == ["ATG", "TGC", "GCG", "CGT"]

def test_extract_kmers_filters_n():
    sequence = "ATGNCGT"
    kmers = extract_kmers(sequence, k=3, filter_n=True)
    assert "TGN" not in kmers
    assert "GNC" not in kmers

def test_count_kmers():
    kmers = ["ATG", "ATG", "CGT"]
    counts = count_kmers(kmers)
    assert counts == {"ATG": 2, "CGT": 1}
```

### Component Tests

**Target**: Functions that interact with Spark

**Tools**: pytest, pyspark.testing

**Example** (`tests/test_spark_kmer.py`):
```python
import pytest
from pyspark.sql import SparkSession
from src.analysis.kmer import compute_kmer_frequencies

@pytest.fixture(scope="module")
def spark():
    return SparkSession.builder.master("local[2]").getOrCreate()

def test_compute_kmer_frequencies(spark):
    # Create test data
    data = [
        ("seq1", "ATGCGT"),
        ("seq2", "ATGATG"),
    ]
    df = spark.createDataFrame(data, ["seq_id", "sequence"])
    
    # Run analysis
    result = compute_kmer_frequencies(df, k=3)
    
    # Verify
    result_dict = {row["kmer"]: row["count"] for row in result.collect()}
    assert result_dict["ATG"] == 3
    assert result_dict["TGC"] == 1
```

### Integration Tests

**Target**: End-to-end workflows

**Tools**: pytest, Docker Compose test profile

**Example** (`tests/test_integration.py`):
```python
def test_full_pipeline_on_sample_data(tmp_path):
    """Test complete pipeline from FASTA to k-mer results"""
    # 1. Create sample FASTA
    fasta_path = tmp_path / "sample.fasta.gz"
    create_sample_fasta(fasta_path, num_sequences=100)
    
    # 2. Convert to Parquet
    parquet_dir = tmp_path / "parquet"
    convert_fasta_to_parquet(fasta_path, parquet_dir)
    
    # 3. Run k-mer analysis
    spark = create_spark_session()
    df = spark.read.parquet(str(parquet_dir))
    results = compute_kmer_frequencies(df, k=6)
    
    # 4. Verify results
    assert results.count() > 0
    assert "kmer" in results.columns
    assert "count" in results.columns
```

### Test Data Strategy

**Approach**: Use small, synthetic datasets for fast tests

**Test Data Sets**:
1. **Tiny** (10 sequences, <1KB): Unit tests
2. **Small** (100 sequences, ~10KB): Component tests
3. **Sample** (1000 sequences, ~100KB): Integration tests
4. **Dev** (5000 sequences, ~1MB): Manual testing

**Generation** (`scripts/create_sample_data.py`):
```python
def generate_random_dna_sequence(length: int) -> str:
    """Generate random DNA sequence"""
    import random
    return ''.join(random.choices('ACGT', k=length))

def create_test_fasta(output_path: Path, num_sequences: int, seq_length: int):
    """Create test FASTA file"""
    with gzip.open(output_path, 'wt') as f:
        for i in range(num_sequences):
            seq = generate_random_dna_sequence(seq_length)
            f.write(f">test_seq_{i}\n{seq}\n")
```

### Continuous Integration

**GitHub Actions Workflow** (`.github/workflows/test.yml`):
```yaml
name: Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      - name: Set up Docker Buildx
        uses: docker/setup-buildx-action@v2
      
      - name: Build containers
        run: docker-compose build
      
      - name: Run tests
        run: docker-compose run --rm jupyter pytest tests/ -v --cov=src
      
      - name: Upload coverage
        uses: codecov/codecov-action@v3
```

---

## Deployment Scenarios

### Scenario 1: Local Development (Laptop)

**Use Case**: Development, testing, small datasets (<1GB)

**System Requirements**:
- 8GB RAM minimum
- 20GB free disk space
- Docker Desktop

**Configuration** (`docker-compose.dev.yml`):
```yaml
version: '3.8'

services:
  spark-master:
    environment:
      SPARK_DRIVER_MEMORY: 2g
      SPARK_EXECUTOR_MEMORY: 2g
      SAMPLE_MODE: "true"
      SAMPLE_SIZE: "5000"

  spark-worker:
    deploy:
      replicas: 1
    environment:
      SPARK_WORKER_MEMORY: 2g
      SPARK_WORKER_CORES: 2
```

**Start Services**:
```bash
docker-compose -f docker-compose.yml -f docker-compose.dev.yml up -d
```

**Expected Performance**:
- Ingestion: ~1000 sequences/sec
- K-mer analysis: ~5000 sequences in <1 min
- Full pipeline (sample): <5 min

### Scenario 2: Workstation (Multi-core Desktop)

**Use Case**: Full dataset processing, production analysis, full organelle genome

**System Requirements**:
- 32GB+ RAM
- 100GB free disk space  
- Docker with 24GB+ allocated
- 8+ CPU cores

**Configuration**:
```yaml
# docker-compose.prod.yml
services:
  spark-master:
    environment:
      SPARK_DRIVER_MEMORY: 4g
  
  spark-worker:
    deploy:
      replicas: 4
    environment:
      SPARK_WORKER_MEMORY: 6g
      SPARK_WORKER_CORES: 4
    resources:
      limits:
        memory: 7g
```

**Start Services**:
```bash
# Auto-scale workers based on cores
WORKERS=$(sysctl -n hw.ncpu)  # macOS
# WORKERS=$(nproc)            # Linux
docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d \
  --scale spark-worker=$WORKERS
```

**Expected Performance**:
- Ingestion: ~10M sequences in <10 min
- K-mer analysis: ~10M sequences in <5 min
- Full pipeline: <30 min

### Scenario 3: Cloud VMs (AWS EC2, Azure VM, GCP Compute)

**Use Case**: On-demand large-scale analysis, collaboration

**Recommended Instance Types**:
- AWS: `r6i.2xlarge` (8 vCPU, 64GB RAM) - $0.50/hr
- Azure: `Standard_E8s_v5` (8 vCPU, 64GB RAM)
- GCP: `n2-highmem-8` (8 vCPU, 64GB RAM)

**Setup Script**:
```bash
#!/bin/bash
# deploy_cloud.sh

# Install Docker
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker $USER
sudo systemctl enable docker

# Install Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" \
  -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

# Clone repository
git clone https://github.com/org/opengenome2.git
cd opengenome2

# Setup environment
cp .env.example .env
# Edit .env as needed

# Start services
docker-compose up -d --scale spark-worker=7

# Run analysis
docker exec spark-master python -m opengenome pipeline run \
  --config experiments/configs/production.yaml
```

**Cost Estimate** (AWS us-east-1):
- Instance: $0.50/hr × 2 hrs = $1.00
- Storage: 100GB EBS ($10/month prorated)
- **Total**: ~$1.50 per full analysis run

### Scenario 4: Kubernetes (Production, Multi-user)

**Use Case**: Production deployment, multiple concurrent users, autoscaling

**Architecture**:
```
Kubernetes Cluster
├── Namespace: opengenome
├── Spark Operator (manages Spark clusters)
├── PostgreSQL (MLflow backend)
├── Persistent Volumes (data, results)
└── Load Balancer (API access)
```

**Deployment** (using Spark Operator):
```yaml
# k8s/spark-application.yaml
apiVersion: "sparkoperator.k8s.io/v1beta2"
kind: SparkApplication
metadata:
  name: opengenome-kmer-analysis
  namespace: opengenome
spec:
  type: Python
  pythonVersion: "3.11"
  mode: cluster
  image: "ghcr.io/org/opengenome:latest"
  imagePullPolicy: Always
  mainApplicationFile: "local:///opt/opengenome/main.py"
  arguments:
    - "analyze"
    - "kmer"
    - "--input=/data/parquet/organelle"
  
  driver:
    cores: 2
    memory: "4g"
    serviceAccount: spark
  
  executor:
    cores: 4
    instances: 8
    memory: "6g"
  
  volumes:
    - name: data
      persistentVolumeClaim:
        claimName: opengenome-data
    - name: results
      persistentVolumeClaim:
        claimName: opengenome-results
```

**Benefits**:
- Auto-scaling based on load
- Resource isolation per job
- Fault tolerance
- Rolling updates
- Multi-tenancy support

### Scenario 5: HPC Cluster (Slurm/SGE)

**Use Case**: University/research HPC, very large datasets

**Singularity Container** (HPC-friendly):
```bash
# Convert Docker to Singularity
singularity build opengenome.sif docker://ghcr.io/org/opengenome:latest

# Submit Slurm job
sbatch <<EOF
#!/bin/bash
#SBATCH --job-name=opengenome
#SBATCH --nodes=4
#SBATCH --ntasks-per-node=8
#SBATCH --mem=64G
#SBATCH --time=04:00:00

module load singularity

# Start Spark cluster
srun --nodes=1 --ntasks=1 singularity exec opengenome.sif \
  spark-class org.apache.spark.deploy.master.Master &

sleep 10

# Start workers
srun --nodes=3 --ntasks=24 singularity exec opengenome.sif \
  spark-class org.apache.spark.deploy.worker.Worker \
  spark://\$(hostname):7077 &

sleep 10

# Run analysis
singularity exec opengenome.sif python -m opengenome pipeline run \
  --config /path/to/config.yaml

EOF
```

---

## Spark Performance Tuning

### Memory Configuration

**Key Principle**: Executor memory should be 60-75% of worker memory

```bash
# Worker has 8GB RAM
SPARK_WORKER_MEMORY=8g
SPARK_EXECUTOR_MEMORY=6g  # 75% of worker
SPARK_EXECUTOR_MEMORY_OVERHEAD=2g  # Remaining 25%
```

**Why**: Prevents OOM errors, leaves room for OS and overhead

### Partition Tuning

**Rule of Thumb**: 2-4 partitions per core

```python
# Calculate optimal partitions
num_workers = 4
cores_per_worker = 4
total_cores = num_workers * cores_per_worker  # 16

# Conservative: 2× cores
partitions = total_cores * 2  # 32

# Aggressive: 4× cores (better for skewed data)
partitions = total_cores * 4  # 64

# Apply
df = df.repartition(partitions)
```

### Caching Strategy

**When to Cache**:
- Dataset used multiple times (k-mer + codon analysis)
- Small enough to fit in memory (<50% of total executor memory)
- Expensive to recompute

**How to Cache**:
```python
from pyspark.storagelevel import StorageLevel

# Memory only (fastest, risky if spills)
df.persist(StorageLevel.MEMORY_ONLY)

# Memory + disk (safe, recommended)
df.persist(StorageLevel.MEMORY_AND_DISK)

# Serialized (saves memory, slightly slower)
df.persist(StorageLevel.MEMORY_AND_DISK_SER)

# Always count after persist to trigger caching
df.count()
```

### Shuffle Optimization

**Minimize Shuffles**:
```python
# BAD: Multiple shuffles
df.groupBy("x").count().join(df.groupBy("y").count(), ...)

# GOOD: Single shuffle with combined aggregation
df.groupBy("x", "y").agg(F.count("*"))
```

**Broadcast Small Tables**:
```python
from pyspark.sql.functions import broadcast

# Broadcast IDF table (small) when joining with TF table (large)
tfidf = tf_large.join(broadcast(idf_small), on="kmer")
```

### Data Skew Handling

**Problem**: Some partitions much larger than others

**Solution**: Salt keys
```python
# Add random salt to skewed key
from pyspark.sql.functions import rand, concat

salted = df.withColumn("salted_key", concat(col("key"), (rand() * 10).cast("int")))
result = salted.groupBy("salted_key").agg(...)
# Then aggregate again without salt
final = result.groupBy(remove_salt_udf("salted_key")).agg(...)
```
2. **ECS/AKS/GKE**: Container orchestration, auto-scaling
3. **EMR/HDInsight/Dataproc**: Managed Spark clusters

**Example - AWS EC2**:
```bash
# Launch EC2 instance (e.g., r5.2xlarge: 8 vCPU, 64GB RAM)
# Install Docker & Docker Compose
# Clone repository
# Run: docker-compose up -d
# Access Jupyter via public IP:8888 (with security group rules)
```

**Example - Kubernetes** (`k8s/deployment.yml`):
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: spark-master
spec:
  replicas: 1
  template:
    spec:
      containers:
      - name: spark-master
        image: opengenome/spark-master:latest
        resources:
          requests:
            memory: "2Gi"
          limits:
            memory: "4Gi"
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: spark-worker
spec:
  replicas: 3  # Scale as needed
  template:
    spec:
      containers:
      - name: spark-worker
        image: opengenome/spark-worker:latest
        resources:
          requests:
            memory: "4Gi"
          limits:
            memory: "8Gi"
```

### Scenario 4: HPC Clusters (Singularity)

**Use Case**: University HPC, large-scale genomics analysis

**Conversion**:
```bash
# Build Singularity images from Docker
singularity build opengenome-jupyter.sif docker://opengenome/jupyter:latest
singularity build opengenome-spark.sif docker://opengenome/spark-worker:latest

# Run on HPC
srun --mem=64G --cpus-per-task=16 \
     singularity run opengenome-jupyter.sif
```

**Advantages**:
- No root privileges required
- Compatible with SLURM/PBS
- Can leverage HPC storage (Lustre, GPFS)

---

## Migration Path from Colab

### Phase 1: Core Infrastructure (Days 1-3)

**Objective**: Set up containerized environment with working Spark cluster

**Tasks**:
1. ⬜ Create directory structure (`src/`, `tests/`, `docker/`, etc.)
2. ⬜ Write Dockerfiles:
   - `docker/spark-master/Dockerfile` (Python 3.11 + Spark + app deps)
   - `docker/spark-worker/Dockerfile` (matching dependencies)
3. ⬜ Create `docker-compose.yml` with master + 2 workers
4. ⬜ Set up environment variables (`.env.example`)
5. ⬜ Create `Makefile` with build/up/down/test commands
6. ⬜ Test container communication and Spark connectivity

**Validation Commands**:
```bash
make build            # Build images
make up               # Start services
make validate         # Check Spark connectivity
make logs             # Verify no errors
```

**Success Criteria**:
- ✓ All containers running
- ✓ Spark Master UI accessible (localhost:8080) showing 2 workers
- ✓ Can submit test Spark job from master container

**Estimated Time**: 8-12 hours

---

### Phase 2: CLI Application Foundation (Days 4-6)

**Objective**: Extract notebook logic into testable Python modules with CLI interface

**Tasks**:
1. ⬜ Create Python package structure (`src/opengenome/`)
2. ⬜ Implement configuration management:
   - `src/opengenome/config.py` - Config dataclasses
   - Environment variable loading with defaults
3. ⬜ Build CLI with Click:
   - `src/opengenome/cli/main.py` - Main CLI entry
   - `src/opengenome/__main__.py` - Enable `python -m opengenome`
4. ⬜ Create Spark session factory:
   - `src/opengenome/spark/session.py` - Connection management
   - Proper resource configuration
5. ⬜ Add logging framework:
   - `src/opengenome/logging.py` - Structured logging
   - JSON format for production, human-readable for dev

**Validation Commands**:
```bash
docker exec spark-master python -m opengenome --help
docker exec spark-master python -m opengenome validate
docker exec spark-master python -m opengenome info --spark
```

**Success Criteria**:
- ✓ CLI responds to commands
- ✓ Config loads from environment
- ✓ Spark session creation works
- ✓ Logging outputs structured data

**Estimated Time**: 10-14 hours

---

### Phase 3: Data Ingestion Pipeline (Days 7-9)

**Objective**: Convert FASTA to Parquet with production-quality code

**Tasks**:
1. ⬜ Implement ingestion modules:
   - `src/opengenome/ingestion/downloader.py` - HuggingFace download
   - `src/opengenome/ingestion/fasta_parser.py` - Streaming FASTA parser
   - `src/opengenome/ingestion/parquet_writer.py` - Efficient Parquet writer
2. ⬜ Create CLI commands:
   - `opengenome ingest download` - Download from HuggingFace
   - `opengenome ingest fasta` - Convert FASTA → Parquet
3. ⬜ Write unit tests for parsers and writers
4. ⬜ Add progress reporting and validation

**Validation Commands**:
```bash
# Download sample data
docker exec spark-master python -m opengenome ingest download \
  --repo arcinstitute/opengenome2 \
  --output /data/raw

# Convert to Parquet
docker exec spark-master python -m opengenome ingest fasta \
  --input /data/raw/organelle.fasta.gz \
  --output /data/parquet/organelle \
  --validate
```

**Success Criteria**:
- ✓ Can download from HuggingFace with caching
- ✓ FASTA parsing is memory-efficient (streaming)
- ✓ Parquet output has correct schema
- ✓ Validation passes
- ✓ Unit tests pass

**Estimated Time**: 12-16 hours

---

### Phase 4: Analysis Implementation (Days 10-14)

**Objective**: Implement k-mer and codon analysis with optimized Spark operations

**Tasks**:
1. ⬜ Implement k-mer analysis:
   - `src/opengenome/analysis/kmer.py` - MapReduce k-mer counting
   - Per-sequence TF/TF-IDF vectors
   - CLI: `opengenome analyze kmer`
2. ⬜ Implement codon analysis:
   - `src/opengenome/analysis/codon.py` - Codon frequency, RSCU
   - CLI: `opengenome analyze codon`
3. ⬜ Implement statistics:
   - `src/opengenome/analysis/statistics.py` - GC%, length dist
   - CLI: `opengenome analyze stats`
4. ⬜ Implement search:
   - `src/opengenome/analysis/search.py` - Cosine similarity search
   - CLI: `opengenome search similar`
5. ⬜ Write comprehensive tests (unit + integration)
6. ⬜ Add MLflow tracking for all analyses

**Validation Commands**:
```bash
# K-mer analysis
docker exec spark-master python -m opengenome analyze kmer \
  --input /data/parquet/organelle \
  --k 6 \
  --output /results/kmer_k6 \
  --top-n 1000

# Codon analysis
docker exec spark-master python -m opengenome analyze codon \
  --input /data/parquet/organelle \
  --output /results/codon \
  --rscu

# Verify results match notebook output
docker exec spark-master python tests/verify_results.py
```

**Success Criteria**:
- ✓ K-mer frequencies match notebook results
- ✓ Codon analysis matches notebook results
- ✓ All commands execute without errors
- ✓ Performance is acceptable (< 5 min for 10M sequences)
- ✓ MLflow tracks all runs
- ✓ Test coverage > 70%

**Estimated Time**: 20-24 hours

---

### Phase 5: Visualization & Pipeline (Days 15-17)

**Objective**: Add visualization and full pipeline orchestration

**Tasks**:
1. ⬜ Implement visualization:
   - `src/opengenome/visualization/plots.py` - All plot types
   - CLI: plots generated as part of analysis commands
2. ⬜ Implement pipeline:
   - `src/opengenome/cli/pipeline.py` - Full pipeline command
   - YAML configuration support
   - `experiments/configs/baseline.yaml` - Example config
3. ⬜ Add experiment tracking:
   - `src/opengenome/ml/tracking.py` - MLflow integration
   - `src/opengenome/ml/experiments.py` - Experiment management
4. ⬜ Write integration tests for full pipeline

**Validation Commands**:
```bash
# Run full pipeline
docker exec spark-master python -m opengenome pipeline run \
  --config experiments/configs/baseline.yaml \
  --experiment baseline_v1

# Check MLflow
open http://localhost:5000  # If MLflow UI running
```

**Success Criteria**:
- ✓ Full pipeline runs end-to-end
- ✓ All visualizations generated
- ✓ Results match notebook outputs
- ✓ MLflow tracking complete
- ✓ Pipeline config is clear and documented

**Estimated Time**: 12-16 hours

---

### Phase 6: Testing & Documentation (Days 18-20)

**Objective**: Comprehensive testing and production-ready documentation

**Tasks**:
1. ⬜ Write comprehensive test suite:
   - Unit tests for all modules
   - Component tests for Spark operations
   - Integration test for full pipeline
   - Performance benchmarks
2. ⬜ Set up CI/CD:
   - `.github/workflows/test.yml` - Run tests on push
   - `.github/workflows/build.yml` - Build Docker images
3. ⬜ Write documentation:
   - `README.md` - Quick start, usage examples
   - `docs/architecture.md` - System design
   - `docs/api.md` - CLI reference
   - `docs/development.md` - Contributing guide
   - `docs/deployment.md` - Deployment scenarios
   - `docs/troubleshooting.md` - Common issues
4. ⬜ Create deployment scripts:
   - `scripts/setup.sh` - Initial setup automation
   - `scripts/validate_environment.sh` - Pre-flight checks
   - `scripts/benchmark.sh` - Performance testing

**Validation Commands**:
```bash
# Run full test suite
make test

# Generate coverage report
make test-coverage

# Validate documentation
make docs-validate

# Test deployment from scratch
./scripts/setup.sh
./scripts/validate_environment.sh
make run-pipeline
```

**Success Criteria**:
- ✓ Test coverage > 80%
- ✓ All tests pass
- ✓ CI/CD pipeline working
- ✓ Documentation complete and accurate
- ✓ Deployment tested on clean system

**Estimated Time**: 12-16 hours

---

### Phase 7: Production Deployment (Days 21-23)

**Objective**: Deploy to production environment and validate

**Tasks**:
1. ⬜ Deploy to target environment (cloud/workstation/HPC)
2. ⬜ Run full dataset processing
3. ⬜ Benchmark performance
4. ⬜ Compare results with original Colab notebook
5. ⬜ Optimize configuration based on benchmarks
6. ⬜ Set up monitoring and alerting
7. ⬜ Create backup/restore procedures
8. ⬜ Train users on new system

**Validation Commands**:
```bash
# Full dataset processing
time opengenome pipeline run --config production.yaml

# Benchmark
./scripts/benchmark.sh

# Validate results
python tests/compare_with_notebook.py
```

**Success Criteria**:
- ✓ Full dataset processes successfully
- ✓ Results match original analysis (within numerical precision)
- ✓ Performance is acceptable or better than Colab
- ✓ System is stable and reproducible
- ✓ Users can run analyses independently

**Estimated Time**: 12-16 hours

---

### Total Migration Timeline

- **Minimum**: 86 hours (~2.5 weeks full-time or ~3 months part-time)
- **Expected**: 104-120 hours (~3-4 weeks full-time or ~4-5 months part-time)
- **Buffer**: +20% for unexpected issues

### Incremental Migration Strategy

**Can use partially migrated system**:
- After Phase 3: Can ingest data
- After Phase 4: Can run analyses
- After Phase 5: Can run full pipeline
- Phase 6-7: Polish and production hardening

**Risk Mitigation**:
- Keep original notebook as reference
- Compare outputs at each phase
- Use sample data for quick iteration
- Test each component before moving forward

---

## Risk Assessment

### Technical Risks

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| **Memory OOM**: Executors crash on large sequences | Medium | High | Sequence length filtering, adaptive partitioning, increase executor memory |
| **Spark Performance**: Slower than expected | Medium | Medium | Benchmark early, tune configurations, use Spark UI for diagnostics |
| **Docker Resource Limits**: Containers throttled | Low | Medium | Set appropriate resource limits, monitor with `docker stats` |
| **Network Latency**: Container communication slow | Low | Low | Use same network, avoid external routing |
| **Dependency Conflicts**: Package version issues | Medium | Medium | Pin all versions with hash checking, use `requirements.lock` |
| **Data Skew**: Uneven partition sizes | Medium | Medium | Salting keys, custom partitioners, monitor partition sizes |
| **Storage Exhaustion**: Disk fills up | Low | Medium | Named volumes, automated cleanup, disk usage alerts |

### Operational Risks

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| **Learning Curve**: CLI unfamiliar to users | Medium | Low | Comprehensive documentation, examples, gradual migration |
| **Testing Gaps**: Edge cases not covered | Medium | Medium | Comprehensive test suite, property-based testing, fuzzing |
| **Configuration Errors**: Wrong environment variables | Medium | Medium | Validation on startup, sensible defaults, error messages |
| **Cost Overruns**: Cloud spending exceeds budget | Medium | Medium | Use spot instances, auto-shutdown, budget alerts |
| **Results Divergence**: Output doesn't match notebook | High | High | Systematic validation, compare at each step, numerical tolerance tests |
| **Production Incidents**: Failures in production | Low | High | Comprehensive monitoring, logging, rollback procedures |

### Advantages Over Colab

| Aspect | Colab | New Design | Improvement |
|--------|-------|------------|-------------|
| **Reproducibility** | ❌ Environment varies | ✅ Fixed Docker images | 100% reproducible |
| **Version Control** | ❌ Hard to version notebooks | ✅ Git-friendly Python | Full history |
| **Scalability** | ❌ Fixed resources | ✅ Horizontal scaling | Unlimited |
| **Testing** | ❌ Manual only | ✅ Automated CI/CD | Continuous validation |
| **Collaboration** | ⚠️ Notebook sharing | ✅ Code review, branches | Better workflow |
| **Production** | ❌ Not production-ready | ✅ Production-grade | Deploy anywhere |
| **Debugging** | ⚠️ Limited | ✅ Full access, logging | Easier troubleshooting |
| **Cost** | ✅ Free | ⚠️ Infrastructure cost | $0-50/month typically |

---

## Design Decisions Log

### Decision 1: Remove Jupyter, Use CLI

**Rationale**:
- **Pro**: Better version control, testability, CI/CD integration
- **Pro**: Clearer separation of concerns (code vs results)
- **Pro**: Easier to run in production, HPC, cloud
- **Con**: Less interactive for exploration
- **Decision**: CLI primary interface, optional notebooks for visualization

**Alternatives Considered**:
- Keep Jupyter: Rejected due to versioning and testing difficulties
- Use both CLI and notebooks: Chose CLI-first to avoid maintenance of two interfaces

### Decision 2: Use 3 Containers Instead of 5

**Rationale**:
- **Pro**: Simpler architecture, fewer moving parts
- **Pro**: Driver colocated with master reduces network hops
- **Pro**: No MinIO needed for file-based storage
- **Con**: Less separation of concerns
- **Decision**: Start simple, add complexity only if needed

**Alternatives Considered**:
- 5-container design (v1.0): Too complex for development use case
- Single container: Insufficient for learning distributed computing

### Decision 3: Python 3.11 with Pinned Dependencies

**Rationale**:
- **Pro**: Latest stable Python with performance improvements
- **Pro**: Pinned versions ensure reproducibility
- **Pro**: `requirements.lock` with hashes prevents tampering
- **Con**: More rigid, harder to update packages
- **Decision**: Use pinned versions, document update process

### Decision 4: MLflow for Experiment Tracking

**Rationale**:
- **Pro**: Industry standard for ML workflows
- **Pro**: Tracks parameters, metrics, artifacts
- **Pro**: Easy to compare experiments
- **Con**: Adds complexity and storage overhead
- **Decision**: Make optional, default to SQLite for simplicity

### Decision 5: CLI with Click Framework

**Rationale**:
- **Pro**: Clean, hierarchical command structure
- **Pro**: Auto-generated help messages
- **Pro**: Easy to test and extend
- **Con**: Learning curve for contributors
- **Decision**: Use Click, provide examples and documentation

### Decision 6: MapReduce Pattern for K-mer Analysis

**Rationale**:
- **Pro**: Proven pattern for this exact use case
- **Pro**: Map-side aggregation reduces shuffle by 100×
- **Pro**: Handles large k-mer vocabularies efficiently
- **Con**: More complex than naive approach
- **Decision**: Use optimized MapReduce, document clearly

### Decision 7: Parquet for Data Storage

**Rationale**:
- **Pro**: Columnar format ideal for Spark
- **Pro**: Excellent compression (10× vs JSON)
- **Pro**: Predicate pushdown for fast queries
- **Con**: Not human-readable
- **Decision**: Use Parquet with schema validation

---

## Summary

This design document presents a **production-grade, CLI-based architecture** for the OpenGenome2 genomic analysis pipeline. The redesign eliminates Jupyter notebook complexity in favor of a testable, version-controllable Python application with industry-standard ML workflow patterns.

### Key Improvements

1. **Simplified Architecture**: 3 containers (master + driver, workers, optional postgres) vs 5
2. **Better Reproducibility**: Docker images, pinned dependencies, DVC data versioning, MLflow tracking
3. **Production Ready**: Comprehensive testing, CI/CD, monitoring, multiple deployment scenarios
4. **Scalable**: Horizontal scaling, optimized Spark configurations, proper resource management
5. **Developer Friendly**: CLI interface, live code reloading, comprehensive documentation
6. **Big Data Optimized**: MapReduce patterns, partitioning strategies, caching, shuffle optimization

### Technology Stack

- **Infrastructure**: Docker Compose, Kubernetes (optional)
- **Compute**: Apache Spark 3.5.0, Python 3.11
- **Storage**: Parquet, PostgreSQL (optional)
- **ML Workflow**: MLflow, DVC
- **CLI**: Click
- **Testing**: Pytest, coverage
- **CI/CD**: GitHub Actions

### Migration Effort

- **Timeline**: 86-120 hours (~3-4 weeks full-time)
- **Phases**: 7 phases from infrastructure to production
- **Risk**: Medium (mitigated with incremental approach)

### Next Steps

1. Review and approve this design
2. Begin Phase 1: Infrastructure setup
3. Follow migration path systematically
4. Validate at each phase
5. Deploy to production

**This design prioritizes working simplicity over clever complexity, following battle-tested patterns from production ML and big data systems.**

### Mitigation Strategies

1. **Memory Management**:
   - Implement DEV/SAMPLE modes with limited data
   - Add memory monitoring to notebooks
   - Use `persist()` judiciously
   - Filter long sequences early

2. **Performance Optimization**:
   - Profile with Spark UI
   - Tune `spark.sql.shuffle.partitions`
   - Use broadcast joins where appropriate
   - Cache frequently accessed DataFrames

3. **Debugging Support**:
   - Extensive logging with levels
   - Health check endpoints
   - Easy shell access to containers
   - Clear error messages with context

4. **Documentation**:
   - Architecture diagrams
   - API documentation
   - Troubleshooting guide
   - Example workflows

---

## Success Criteria

### Functional Requirements
- ✅ All analysis from original notebook reproduced
- ✅ Can run on local laptop, workstation, and cloud
- ✅ No dependencies on Google Colab or Drive
- ✅ Results match original analysis
- ✅ Full dataset processing completes successfully

### Non-Functional Requirements
- ✅ Setup time <30 minutes for new user
- ✅ Notebook execution matches or exceeds Colab performance
- ✅ Can scale from dev sample (5K sequences) to full dataset (>1M)
- ✅ Memory usage optimized (no OOM on 16GB machine)
- ✅ Test coverage >70%
- ✅ Documentation complete and clear

### Usability Requirements
- ✅ Simple commands (make up, make down, make test)
- ✅ Clear error messages
- ✅ Working examples for all major functions
- ✅ Jupyter notebooks load without modification
- ✅ Can run analysis without understanding Docker internals

---

## Next Steps

After design approval, proceed with:

1. **Create file structure and Docker configurations**
2. **Build and test containers**
3. **Refactor Config management**
4. **Extract code modules**
5. **Refactor notebooks**
6. **Write tests**
7. **Document deployment**

---

## Appendix: Design Decisions Log

### Decision 1: Why Docker Compose vs Kubernetes?
**Rationale**: Start simple. Compose is sufficient for single-machine and small cluster deployments. Can migrate to K8s later if needed. Follows "working simplicity over clever design".

### Decision 2: Why BioPython vs custom parser?
**Rationale**: BioPython is battle-tested, handles edge cases, widely used in bioinformatics. No need to reinvent.

### Decision 3: Why Parquet vs other formats?
**Rationale**: Columnar storage, excellent compression, native Spark support, schema enforcement.

### Decision 4: Why mapInPandas vs regular Spark operations?
**Rationale**: Avoids explode() memory issues, leverages Pandas performance, easier to write complex logic.

### Decision 5: Why include MinIO?
**Rationale**: Provides cloud-agnostic S3 API, useful for large datasets, enables future cloud migration without code changes. Optional for simple deployments.

### Decision 6: Why separate workers from master?
**Rationale**: Mirrors production Spark architecture, allows easy scaling, clear resource allocation.

### Decision 7: Why split notebooks?
**Rationale**: Single-responsibility principle, easier to maintain, can run stages independently, better for collaboration.

---

**End of Design Document**
