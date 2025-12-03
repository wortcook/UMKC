# OpenGenome2 Docker Refactoring - Implementation Plan

**Date**: December 2, 2025  
**Version**: 1.0  
**Status**: Ready for Execution

---

## Overview

This document provides a detailed, step-by-step implementation plan for refactoring the OpenGenome2 project from Google Colab to a Docker-based architecture. Each phase includes specific tasks, acceptance criteria, and estimated effort.

---

## Implementation Phases

### Phase 1: Infrastructure Setup
**Goal**: Create working Docker environment with all containers communicating properly  
**Duration**: 2-3 days  
**Priority**: CRITICAL - Must complete before any code refactoring

### Phase 2: Code Modularization
**Goal**: Extract reusable code from notebook into Python modules  
**Duration**: 3-4 days  
**Priority**: HIGH - Enables testing and maintainability

### Phase 3: Notebook Refactoring
**Goal**: Split monolithic notebook and update for Docker environment  
**Duration**: 2-3 days  
**Priority**: HIGH - Main deliverable

### Phase 4: Testing Framework
**Goal**: Implement comprehensive test suite  
**Duration**: 2-3 days  
**Priority**: MEDIUM - Ensures reliability

### Phase 5: Documentation & Deployment
**Goal**: Complete documentation and deploy to target environment  
**Duration**: 2-3 days  
**Priority**: MEDIUM - Enables adoption

**Total Estimated Duration**: 11-16 days (2-3 weeks)

---

## Phase 1: Infrastructure Setup

### Task 1.1: Create Project Structure
**Estimated Time**: 1 hour

**Steps**:
1. Create root directory structure
2. Create subdirectories (docker/, notebooks/, src/, tests/, data/, results/, cache/, scripts/, docs/)
3. Create .gitkeep files in empty directories
4. Create .gitignore file

**Deliverables**:
- Complete directory structure matching DESIGN.md
- .gitignore with appropriate exclusions

**Acceptance Criteria**:
- [ ] All directories exist
- [ ] .gitignore excludes data/, results/, cache/, .env
- [ ] Directory structure matches design document

**Commands**:
```bash
mkdir -p opengenome2-project/{docker/{jupyter,spark-master,spark-worker},notebooks,src/{ingestion,analysis,spark,visualization},tests,data/{raw,parquet,samples},results/{figures,reports},cache,scripts,docs}
touch data/.gitkeep results/.gitkeep cache/.gitkeep
```

---

### Task 1.2: Create Dockerfile for Jupyter Container
**Estimated Time**: 2 hours

**Steps**:
1. Create `docker/jupyter/Dockerfile`
2. Base from `jupyter/pyspark-notebook:spark-3.5.0`
3. Install system dependencies (Java 17, curl, wget)
4. Create requirements.txt with Python packages
5. Install Python dependencies
6. Set environment variables
7. Test build locally

**Deliverables**:
- `docker/jupyter/Dockerfile`
- `docker/jupyter/requirements.txt`

**Acceptance Criteria**:
- [ ] Dockerfile builds without errors
- [ ] Java 17 is installed and accessible
- [ ] All Python packages install successfully
- [ ] Image size is reasonable (<3GB)

**Key Dependencies**:
```
biopython==1.81
huggingface-hub==0.19.4
pyarrow==14.0.1
pandas==2.1.3
pyspark==3.5.0
matplotlib==3.8.2
seaborn==0.13.0
pytest==7.4.3
pytest-cov==4.1.0
```

---

### Task 1.3: Create Dockerfile for Spark Master
**Estimated Time**: 1 hour

**Steps**:
1. Create `docker/spark-master/Dockerfile`
2. Base from `bitnami/spark:3.5.0`
3. Install Python dependencies (biopython, pyarrow, pandas)
4. Configure Spark defaults
5. Test build locally

**Deliverables**:
- `docker/spark-master/Dockerfile`
- `docker/spark-master/spark-defaults.conf` (optional)

**Acceptance Criteria**:
- [ ] Dockerfile builds without errors
- [ ] Python packages installed in Spark environment
- [ ] Spark version is 3.5.0

---

### Task 1.4: Create Dockerfile for Spark Worker
**Estimated Time**: 1 hour

**Steps**:
1. Create `docker/spark-worker/Dockerfile`
2. Base from `bitnami/spark:3.5.0`
3. Install same Python dependencies as master
4. Test build locally

**Deliverables**:
- `docker/spark-worker/Dockerfile`
- `docker/spark-worker/requirements.txt`

**Acceptance Criteria**:
- [ ] Dockerfile builds without errors
- [ ] Python dependencies match master
- [ ] Can function as Spark worker

---

### Task 1.5: Create Docker Compose Configuration
**Estimated Time**: 3 hours

**Steps**:
1. Create `docker-compose.yml` with all services
2. Define networks (spark-network)
3. Define volumes (spark-logs, minio-data)
4. Configure service dependencies
5. Set up environment variables
6. Configure volume mounts
7. Expose appropriate ports
8. Test full stack startup

**Deliverables**:
- `docker-compose.yml`
- `docker-compose.dev.yml` (development overrides)

**Acceptance Criteria**:
- [ ] All services defined (jupyter, spark-master, spark-worker-1, spark-worker-2, minio)
- [ ] Network configuration allows inter-container communication
- [ ] Volumes properly mounted
- [ ] Ports exposed correctly (8888, 8080, 7077, 9000, 9001)
- [ ] Services start in correct order

**Key Configuration Points**:
- Spark Master URL: `spark://spark-master:7077`
- Jupyter work directory: `/home/jovyan/work`
- Shared data volumes: `/data`, `/results`, `/cache`

---

### Task 1.6: Create Environment Configuration
**Estimated Time**: 1 hour

**Steps**:
1. Create `.env.example` with all variables and documentation
2. Create Makefile with common commands
3. Test environment variable loading

**Deliverables**:
- `.env.example`
- `Makefile`

**Acceptance Criteria**:
- [ ] .env.example contains all necessary variables
- [ ] Variables have sensible defaults
- [ ] Documentation explains each variable
- [ ] Makefile commands work (build, up, down, logs, test)

**Makefile Targets**:
```makefile
build: Build all containers
up: Start all services
down: Stop all services
restart: Restart all services
logs: View logs (follow mode)
clean: Remove volumes and containers
test: Run test suite
shell-jupyter: Shell into Jupyter container
shell-spark: Shell into Spark master
scale-workers: Scale worker count
validate: Validate environment
```

---

### Task 1.7: Initial Integration Test
**Estimated Time**: 2 hours

**Steps**:
1. Build all containers: `make build`
2. Start services: `make up`
3. Verify Jupyter Lab accessible at localhost:8888
4. Verify Spark Master UI at localhost:8080
5. Verify MinIO console at localhost:9001
6. Test Spark connection from Jupyter
7. Test file system mounts
8. Test container-to-container communication
9. Document any issues and fix

**Deliverables**:
- Working Docker Compose stack
- Integration test results

**Acceptance Criteria**:
- [ ] All containers start without errors
- [ ] No port conflicts
- [ ] Jupyter Lab loads and shows work directory
- [ ] Spark Master UI shows 2 workers
- [ ] Can create Spark session from Jupyter
- [ ] Can read/write files to mounted volumes
- [ ] Container logs show no errors

**Test Script** (run in Jupyter):
```python
# Test Spark connectivity
from pyspark.sql import SparkSession

spark = SparkSession.builder \
    .appName("ConnectivityTest") \
    .master("spark://spark-master:7077") \
    .getOrCreate()

# Test data creation
test_data = [("test1", 123), ("test2", 456)]
df = spark.createDataFrame(test_data, ["id", "value"])
df.show()

# Test file system
from pathlib import Path
assert Path("/data").exists()
assert Path("/results").exists()
assert Path("/cache").exists()

print("✅ All connectivity tests passed!")
```

---

## Phase 2: Code Modularization

### Task 2.1: Create Configuration Module
**Estimated Time**: 2 hours

**Steps**:
1. Create `src/__init__.py`
2. Create `src/config.py` with Config class
3. Implement all configuration parameters from DESIGN.md
4. Add validation method
5. Add print_config method for debugging
6. Write unit tests for Config class

**Deliverables**:
- `src/config.py`
- `tests/test_config.py`

**Acceptance Criteria**:
- [ ] Config class has all parameters from design
- [ ] Environment variables properly read
- [ ] Defaults work when env vars not set
- [ ] validate() method creates necessary directories
- [ ] Tests pass

---

### Task 2.2: Create Spark Session Factory
**Estimated Time**: 2 hours

**Steps**:
1. Create `src/spark/__init__.py`
2. Create `src/spark/session.py`
3. Implement `create_spark_session()` function
4. Configure for Docker environment
5. Add error handling
6. Write tests

**Deliverables**:
- `src/spark/session.py`
- `tests/test_spark_session.py`

**Acceptance Criteria**:
- [ ] Function creates working Spark session
- [ ] Connects to spark-master correctly
- [ ] Configuration values from Config used
- [ ] Works in both local[*] and cluster modes
- [ ] Proper error messages on failure

**Function Signature**:
```python
def create_spark_session(
    app_name: str = None,
    master: str = None,
    configs: Optional[Dict[str, str]] = None
) -> SparkSession:
    """
    Create a configured Spark session.
    
    Args:
        app_name: Application name (default from Config)
        master: Spark master URL (default from Config)
        configs: Additional Spark configurations
    
    Returns:
        Configured SparkSession
    """
```

---

### Task 2.3: Create Data Ingestion Module
**Estimated Time**: 4 hours

**Steps**:
1. Create `src/ingestion/__init__.py`
2. Create `src/ingestion/downloader.py`
   - Implement HuggingFace download function
   - Add caching logic
   - Add progress reporting
3. Create `src/ingestion/parser.py`
   - Implement FASTA streaming parser
   - Handle gzipped files
   - Add sequence filtering
4. Create `src/ingestion/parquet_writer.py`
   - Implement batch writing
   - Add schema definition
   - Add compression
5. Write comprehensive tests

**Deliverables**:
- `src/ingestion/downloader.py`
- `src/ingestion/parser.py`
- `src/ingestion/parquet_writer.py`
- `tests/test_ingestion.py`

**Acceptance Criteria**:
- [ ] Can download from HuggingFace with caching
- [ ] Can parse FASTA files efficiently
- [ ] Can write Parquet with correct schema
- [ ] Handles errors gracefully
- [ ] Tests cover main functionality

**Key Functions**:
```python
# downloader.py
def download_organelle_data(
    cache_dir: Path = None,
    force_download: bool = False
) -> Path:
    """Download organelle FASTA from HuggingFace"""

# parser.py
def parse_fasta_streaming(
    fasta_path: Path,
    max_length: Optional[int] = None,
    filter_n: bool = True
) -> Iterator[Dict[str, Any]]:
    """Stream parse FASTA file"""

# parquet_writer.py
def write_parquet_shards(
    records: Iterator[Dict[str, Any]],
    output_dir: Path,
    chunk_size: int = 50000,
    compression: str = "snappy"
) -> List[Path]:
    """Write records to Parquet shards"""
```

---

### Task 2.4: Create K-mer Analysis Module
**Estimated Time**: 4 hours

**Steps**:
1. Create `src/analysis/__init__.py`
2. Create `src/analysis/kmer.py`
3. Implement k-mer extraction functions
4. Implement MapReduce k-mer counting
5. Implement per-sequence k-mer vectors
6. Add TF and TF-IDF calculations
7. Write comprehensive tests

**Deliverables**:
- `src/analysis/kmer.py`
- `tests/test_kmer.py`

**Acceptance Criteria**:
- [ ] Pure Python functions for k-mer extraction
- [ ] Spark functions for distributed processing
- [ ] mapInPandas implementation works
- [ ] Memory efficient (no explode)
- [ ] Tests cover edge cases

**Key Functions**:
```python
def extract_kmers(sequence: str, k: int, filter_n: bool = True) -> List[str]:
    """Extract k-mers from a sequence (pure Python)"""

def count_kmers(kmers: List[str]) -> Dict[str, int]:
    """Count k-mer occurrences (pure Python)"""

def compute_global_kmer_frequencies(
    df: DataFrame,
    k: int = 6,
    filter_n: bool = True
) -> DataFrame:
    """Compute global k-mer frequencies using Spark MapReduce"""

def compute_per_sequence_kmers(
    df: DataFrame,
    k: int = 6
) -> DataFrame:
    """Compute per-sequence k-mer TF vectors"""

def compute_idf(tf_df: DataFrame) -> DataFrame:
    """Compute IDF values for k-mers"""
```

---

### Task 2.5: Create Codon Analysis Module
**Estimated Time**: 3 hours

**Steps**:
1. Create `src/analysis/codon.py`
2. Implement codon extraction
3. Implement codon frequency calculation
4. Implement RSCU calculation
5. Add genetic code mapping
6. Write tests

**Deliverables**:
- `src/analysis/codon.py`
- `tests/test_codon.py`

**Acceptance Criteria**:
- [ ] Can extract codons from sequences
- [ ] Handles all three reading frames
- [ ] RSCU calculation correct
- [ ] Genetic code mapping accurate
- [ ] Tests validate biology

**Key Functions**:
```python
def extract_codons(
    sequence: str,
    frame: int = 0,
    filter_n: bool = True
) -> List[str]:
    """Extract codons from sequence"""

def compute_codon_frequencies(
    df: DataFrame,
    frame: int = 0
) -> DataFrame:
    """Compute global codon frequencies"""

def compute_rscu(codon_freq_df: DataFrame) -> DataFrame:
    """Compute Relative Synonymous Codon Usage"""

GENETIC_CODE: Dict[str, str] = {
    "ATG": "M", "ATT": "I", ...
}
```

---

### Task 2.6: Create Search Module
**Estimated Time**: 3 hours

**Steps**:
1. Create `src/analysis/search.py`
2. Implement query vectorization
3. Implement cosine similarity search
4. Implement exact k-mer match search
5. Add result ranking
6. Write tests

**Deliverables**:
- `src/analysis/search.py`
- `tests/test_search.py`

**Acceptance Criteria**:
- [ ] Can vectorize query sequences
- [ ] Cosine similarity computation correct
- [ ] Search returns top-N results
- [ ] Performance acceptable on test data
- [ ] Tests validate search accuracy

**Key Functions**:
```python
def vectorize_query(
    query_seq: str,
    k: int,
    spark: SparkSession
) -> DataFrame:
    """Convert query sequence to k-mer vector"""

def cosine_similarity_search(
    query_vec: DataFrame,
    corpus_tf: DataFrame,
    corpus_norms: DataFrame,
    idf: Optional[DataFrame] = None,
    top_n: int = 20
) -> DataFrame:
    """Search corpus for similar sequences"""

def exact_kmer_match(
    kmer: str,
    corpus_tf: DataFrame,
    min_count: int = 1,
    top_n: int = 50
) -> DataFrame:
    """Find sequences containing exact k-mer"""
```

---

### Task 2.7: Create Visualization Module
**Estimated Time**: 3 hours

**Steps**:
1. Create `src/visualization/__init__.py`
2. Create `src/visualization/plots.py`
3. Implement plot functions for:
   - GC content histogram
   - K-mer frequency bar charts
   - Codon frequency plots
   - RSCU plots
   - Codon usage heatmap
4. Create `src/visualization/styles.py` for consistent styling
5. Write tests (visual regression optional)

**Deliverables**:
- `src/visualization/plots.py`
- `src/visualization/styles.py`
- `tests/test_visualization.py`

**Acceptance Criteria**:
- [ ] All plot types implemented
- [ ] Consistent styling
- [ ] High-resolution output (300 DPI)
- [ ] Can save to file or display
- [ ] Tests verify plot generation

**Key Functions**:
```python
def plot_gc_distribution(
    gc_data: pd.Series,
    output_path: Optional[Path] = None,
    title: str = "GC Content Distribution"
) -> None:
    """Plot GC content histogram"""

def plot_kmer_frequencies(
    kmer_df: pd.DataFrame,
    top_n: int = 20,
    output_path: Optional[Path] = None
) -> None:
    """Plot k-mer frequency bar chart"""

def plot_codon_usage_heatmap(
    codon_freq_df: pd.DataFrame,
    output_path: Optional[Path] = None
) -> None:
    """Plot codon usage heatmap (8x8 layout)"""
```

---

## Phase 3: Notebook Refactoring

### Task 3.1: Create Setup Notebook
**Estimated Time**: 1 hour

**Steps**:
1. Create `notebooks/00_setup_and_test.ipynb`
2. Import and validate Config
3. Test Spark connectivity
4. Test file system access
5. Display system information
6. Run smoke tests

**Deliverables**:
- `notebooks/00_setup_and_test.ipynb`

**Acceptance Criteria**:
- [ ] Notebook runs without errors
- [ ] All tests pass
- [ ] Clear output for troubleshooting
- [ ] Serves as environment validation

**Notebook Outline**:
```
Cell 1: Imports and Config
Cell 2: Spark Session Test
Cell 3: File System Test
Cell 4: System Information
Cell 5: Simple Data Test
Cell 6: Summary
```

---

### Task 3.2: Create Data Ingestion Notebook
**Estimated Time**: 2 hours

**Steps**:
1. Create `notebooks/01_data_ingestion.ipynb`
2. Import ingestion modules
3. Download data from HuggingFace
4. Parse and convert to Parquet
5. Validate output
6. Display statistics

**Deliverables**:
- `notebooks/01_data_ingestion.ipynb`

**Acceptance Criteria**:
- [ ] Can download organelle data
- [ ] Can convert to Parquet
- [ ] Shows progress and statistics
- [ ] Validates output schema
- [ ] Clear documentation

---

### Task 3.3: Create Exploratory Analysis Notebook
**Estimated Time**: 2 hours

**Steps**:
1. Create `notebooks/02_exploratory_analysis.ipynb`
2. Load Parquet data
3. Display sample records
4. Compute basic statistics (length distribution, GC content)
5. Create visualizations
6. Profile data quality

**Deliverables**:
- `notebooks/02_exploratory_analysis.ipynb`

**Acceptance Criteria**:
- [ ] Loads data successfully
- [ ] Shows meaningful statistics
- [ ] Visualizations are clear
- [ ] Identifies data quality issues
- [ ] Fast execution on samples

---

### Task 3.4: Create K-mer Analysis Notebook
**Estimated Time**: 2 hours

**Steps**:
1. Create `notebooks/03_kmer_analysis.ipynb`
2. Load data and create Spark session
3. Compute global k-mer frequencies
4. Compute per-sequence k-mer vectors
5. Visualize top k-mers
6. Export results

**Deliverables**:
- `notebooks/03_kmer_analysis.ipynb`

**Acceptance Criteria**:
- [ ] Computes k-mer frequencies correctly
- [ ] No memory issues
- [ ] Visualizations match original
- [ ] Can export results
- [ ] Clear explanations

---

### Task 3.5: Create Codon Analysis Notebook
**Estimated Time**: 2 hours

**Steps**:
1. Create `notebooks/04_codon_analysis.ipynb`
2. Compute codon frequencies
3. Calculate RSCU
4. Create codon usage plots
5. Generate heatmap
6. Export results

**Deliverables**:
- `notebooks/04_codon_analysis.ipynb`

**Acceptance Criteria**:
- [ ] Codon frequencies correct
- [ ] RSCU calculation accurate
- [ ] Visualizations clear
- [ ] Results match original
- [ ] Biologically meaningful

---

### Task 3.6: Create Sequence Search Notebook
**Estimated Time**: 2 hours

**Steps**:
1. Create `notebooks/05_sequence_search.ipynb`
2. Build search indices (TF, IDF, norms)
3. Implement query interface
4. Demonstrate similarity search
5. Demonstrate exact match search
6. Visualize results

**Deliverables**:
- `notebooks/05_sequence_search.ipynb`

**Acceptance Criteria**:
- [ ] Search works correctly
- [ ] Query interface user-friendly
- [ ] Results are ranked
- [ ] Performance acceptable
- [ ] Examples are clear

---

### Task 3.7: Create Visualization Notebook
**Estimated Time**: 1 hour

**Steps**:
1. Create `notebooks/06_visualization.ipynb`
2. Load analysis results
3. Generate all publication-quality figures
4. Create summary report
5. Export all plots

**Deliverables**:
- `notebooks/06_visualization.ipynb`

**Acceptance Criteria**:
- [ ] All plot types generated
- [ ] High-resolution output
- [ ] Consistent styling
- [ ] Saved to results/figures/
- [ ] Ready for presentations

---

### Task 3.8: Create Notebook README
**Estimated Time**: 1 hour

**Steps**:
1. Create `notebooks/README.md`
2. Document execution order
3. Explain each notebook's purpose
4. List dependencies
5. Provide troubleshooting tips

**Deliverables**:
- `notebooks/README.md`

**Acceptance Criteria**:
- [ ] Clear execution instructions
- [ ] Purpose of each notebook explained
- [ ] Prerequisites listed
- [ ] Common issues documented

---

## Phase 4: Testing Framework

### Task 4.1: Set Up Pytest Infrastructure
**Estimated Time**: 2 hours

**Steps**:
1. Create `tests/conftest.py` with fixtures
2. Create pytest configuration (`pytest.ini` or `pyproject.toml`)
3. Set up coverage configuration
4. Create test data generation script
5. Test pytest works in container

**Deliverables**:
- `tests/conftest.py`
- `pytest.ini` or test section in `pyproject.toml`
- `.coveragerc`
- `scripts/create_sample_data.py`

**Acceptance Criteria**:
- [ ] Pytest discovers all tests
- [ ] Fixtures work correctly
- [ ] Coverage tracking enabled
- [ ] Can run: `make test`
- [ ] Sample data generation works

**Key Fixtures**:
```python
@pytest.fixture(scope="session")
def spark_session():
    """Provide Spark session for tests"""

@pytest.fixture
def sample_fasta(tmp_path):
    """Create sample FASTA file"""

@pytest.fixture
def sample_parquet(tmp_path, spark_session):
    """Create sample Parquet dataset"""
```

---

### Task 4.2: Write Unit Tests
**Estimated Time**: 4 hours

**Steps**:
1. Write tests for `config.py`
2. Write tests for ingestion modules (pure functions)
3. Write tests for k-mer analysis (pure functions)
4. Write tests for codon analysis (pure functions)
5. Write tests for visualization (plot generation)
6. Aim for >70% coverage of pure functions

**Deliverables**:
- `tests/test_config.py`
- `tests/test_ingestion.py`
- `tests/test_kmer.py`
- `tests/test_codon.py`
- `tests/test_visualization.py`

**Acceptance Criteria**:
- [ ] All pure functions tested
- [ ] Edge cases covered
- [ ] Tests are fast (<1 min total)
- [ ] Coverage >70% for src/ modules
- [ ] All tests pass

---

### Task 4.3: Write Component Tests
**Estimated Time**: 3 hours

**Steps**:
1. Write tests for Spark session creation
2. Write tests for Spark-based k-mer analysis
3. Write tests for Spark-based codon analysis
4. Write tests for search functionality
5. Use small synthetic datasets

**Deliverables**:
- `tests/test_spark_session.py`
- `tests/test_spark_kmer.py`
- `tests/test_spark_codon.py`
- `tests/test_search.py`

**Acceptance Criteria**:
- [ ] Tests use local Spark
- [ ] Tests are reasonably fast (<5 min)
- [ ] Cover main Spark operations
- [ ] Validate correctness of distributed computing

---

### Task 4.4: Write Integration Test
**Estimated Time**: 2 hours

**Steps**:
1. Create `tests/test_integration.py`
2. Test full pipeline: FASTA → Parquet → Analysis → Results
3. Use small test dataset (100 sequences)
4. Validate end-to-end correctness

**Deliverables**:
- `tests/test_integration.py`

**Acceptance Criteria**:
- [ ] Full pipeline tested
- [ ] Uses realistic data
- [ ] Verifies output correctness
- [ ] Can run in CI/CD

---

## Phase 5: Documentation & Deployment

### Task 5.1: Write User Documentation
**Estimated Time**: 3 hours

**Steps**:
1. Create comprehensive `README.md`
2. Create `docs/architecture.md` (reference DESIGN.md)
3. Create `docs/deployment.md`
4. Create `docs/troubleshooting.md`
5. Create `docs/api.md` for module API reference

**Deliverables**:
- `README.md`
- `docs/architecture.md`
- `docs/deployment.md`
- `docs/troubleshooting.md`
- `docs/api.md`

**Acceptance Criteria**:
- [ ] README has quick start guide
- [ ] Architecture clearly explained
- [ ] Deployment scenarios documented
- [ ] Common issues addressed
- [ ] API reference complete

**README Structure**:
```markdown
# OpenGenome2 - Genomic Sequence Analysis Pipeline

## Quick Start
## Features
## Architecture
## Requirements
## Installation
## Usage
## Development
## Testing
## Deployment
## Troubleshooting
## Contributing
## License
```

---

### Task 5.2: Create Deployment Scripts
**Estimated Time**: 2 hours

**Steps**:
1. Create `scripts/setup_minio.sh` for MinIO bucket initialization
2. Create `scripts/validate_environment.py` for pre-flight checks
3. Create `scripts/download_dataset.sh` for batch downloads
4. Create `scripts/cleanup.sh` for maintenance
5. Make all scripts executable
6. Test all scripts

**Deliverables**:
- `scripts/setup_minio.sh`
- `scripts/validate_environment.py`
- `scripts/download_dataset.sh`
- `scripts/cleanup.sh`

**Acceptance Criteria**:
- [ ] All scripts work correctly
- [ ] Scripts have error handling
- [ ] Scripts are documented (comments)
- [ ] Scripts are idempotent where applicable

---

### Task 5.3: Set Up CI/CD
**Estimated Time**: 2 hours

**Steps**:
1. Create `.github/workflows/test.yml` for automated testing
2. Create `.github/workflows/build.yml` for Docker image builds
3. Configure GitHub Actions
4. Test workflows

**Deliverables**:
- `.github/workflows/test.yml`
- `.github/workflows/build.yml`

**Acceptance Criteria**:
- [ ] Tests run on every push
- [ ] Docker images build successfully
- [ ] Badges added to README
- [ ] Workflows pass

---

### Task 5.4: Local Deployment Validation
**Estimated Time**: 2 hours

**Steps**:
1. Fresh clone of repository
2. Follow README from scratch
3. Run all notebooks
4. Verify all outputs
5. Document any issues
6. Fix issues and update documentation

**Deliverables**:
- Validated deployment on clean machine
- Updated documentation

**Acceptance Criteria**:
- [ ] Can set up from README alone
- [ ] All notebooks run successfully
- [ ] Results are correct
- [ ] No missing dependencies
- [ ] Setup time <30 minutes

---

### Task 5.5: Cloud Deployment (Optional)
**Estimated Time**: 4 hours

**Steps**:
1. Choose cloud provider (AWS/Azure/GCP)
2. Deploy to cloud environment
3. Test with full dataset
4. Benchmark performance
5. Document cloud deployment
6. Create cloud-specific configurations

**Deliverables**:
- Cloud deployment documentation
- Performance benchmarks
- Cost estimates

**Acceptance Criteria**:
- [ ] Successfully deployed to cloud
- [ ] Full dataset processed
- [ ] Performance documented
- [ ] Costs estimated

---

## Quality Gates

### After Phase 1
- [ ] All containers build successfully
- [ ] All services start without errors
- [ ] Spark connectivity verified
- [ ] File system mounts working

### After Phase 2
- [ ] All modules importable
- [ ] Config system working
- [ ] Unit tests pass
- [ ] Code linting passes

### After Phase 3
- [ ] All notebooks run successfully
- [ ] Results match original analysis
- [ ] No Colab dependencies remain
- [ ] Documentation updated

### After Phase 4
- [ ] Test coverage >70%
- [ ] All tests pass
- [ ] Integration test works
- [ ] No critical bugs

### After Phase 5
- [ ] Documentation complete
- [ ] Deployment validated
- [ ] CI/CD working
- [ ] Ready for production use

---

## Risk Mitigation Checklist

Before starting each phase:
- [ ] Review phase objectives
- [ ] Check all prerequisites met
- [ ] Prepare test data if needed
- [ ] Review relevant documentation
- [ ] Allocate sufficient time

During each phase:
- [ ] Test incrementally
- [ ] Commit working code frequently
- [ ] Document issues immediately
- [ ] Ask for help when stuck
- [ ] Take breaks for complex problems

After each phase:
- [ ] Verify quality gates
- [ ] Update progress tracking
- [ ] Document lessons learned
- [ ] Plan next phase
- [ ] Celebrate progress!

---

## Progress Tracking

Use the todo list to track overall progress:

**Phase Status**:
- [ ] Phase 1: Infrastructure Setup
- [ ] Phase 2: Code Modularization
- [ ] Phase 3: Notebook Refactoring
- [ ] Phase 4: Testing Framework
- [ ] Phase 5: Documentation & Deployment

**Task Completion** (to be updated as work progresses):
- Phase 1: 0/7 tasks complete
- Phase 2: 0/7 tasks complete
- Phase 3: 0/8 tasks complete
- Phase 4: 0/4 tasks complete
- Phase 5: 0/5 tasks complete

**Overall Progress**: 0/31 tasks complete (0%)

---

## Resources & References

### Documentation to Consult
- Docker Compose documentation
- Apache Spark documentation
- BioPython documentation
- Pytest documentation
- GitHub Actions documentation

### Tools Available
- Docker and Docker Compose
- Python development tools
- Git for version control
- VS Code or Jupyter for development
- Command line tools

### When to Ask for Help
- Unclear requirements
- Technical blockers
- Design decisions needed
- Testing strategy questions
- Deployment issues

---

## Next Session Preview

At the start of the next session, we will:
1. Mark Phase 1 as active
2. Begin with Task 1.1 (Create Project Structure)
3. Work through infrastructure setup systematically
4. Test each component before moving forward
5. Update progress tracking as we go

**Remember**: Working simplicity over clever design. Test early, test often, commit frequently!

---

**End of Implementation Plan**
