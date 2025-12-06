# K-mer Analysis Memory Requirements

## Current Status

- **k=8**: ✅ Works with 4GB workers (3.5GB executors)
- **k=16**: ❌ Fails with OOM errors
- **k=32**: ❌ Not attempted (would fail)

## Problem Analysis

The 214,950 sequence dataset generates:
- **k=8**: ~83K unique k-mers (manageable)
- **k=16**: Estimated ~50-100M unique k-mers 
- **k=32**: Estimated ~1-5B unique k-mers

Each partition with current setup processes ~21,500 sequences (after repartitioning to 10 partitions), generating 15-35 million k-mers per partition. This exceeds the 3.5GB executor memory available.

## Solutions Implemented

### ✅ Optimization #1: Repartitioning
**Code**: `src/opengenome/analysis/kmer.py`
```python
if self.k >= 16:
    target_partitions = 10  # Reduced from ~29
    df = df.repartition(target_partitions)
```
**Result**: Reduces Python worker overhead but still insufficient for k=16+

### ✅ Optimization #2: Smaller Batch Sizes
```python
batch_size = 5000 if k >= 16 else 10000
```
**Result**: Yields k-mers more frequently to reduce memory spikes

### ✅ Optimization #3: Sequence Chunking
```python
# For sequences > 50KB, process in 50KB chunks
if len(seq_upper) > 50000 and k >= 16:
    chunk_size = 50000
    # Process in overlapping chunks
```
**Result**: Prevents large sequences from causing memory spikes

## Required for k=16 and k=32 Success

### Option A: Increase Worker Memory (RECOMMENDED)

1. **Edit `docker-compose.yml`**:
```yaml
services:
  spark-worker-1:
    deploy:
      resources:
        limits:
          memory: 8G  # Increased from 4G
          cpus: '2'
  
  spark-worker-2:
    deploy:
      resources:
        limits:
          memory: 8G  # Increased from 4G
          cpus: '2'
```

2. **Edit `.env`**:
```bash
SPARK_EXECUTOR_MEMORY=7g  # Increased from 3.5g
SPARK_WORKER_MEMORY=8g    # Increased from 4g
```

3. **System Requirements**:
   - **For k=16**: 16GB+ RAM recommended (2 workers × 8GB)
   - **For k=32**: 24GB+ RAM recommended (2 workers × 12GB)

4. **Restart cluster**:
```bash
docker-compose down
docker-compose up -d
```

### Option B: Sample the Dataset

For testing k=16/k=32 without hardware upgrades:

```bash
# Analyze 10% of sequences
./opengenome analyze kmer \
    --input /data/parquet/plasmids_phage \
    --output /results/demo/kmer_16_sample \
    --k 16 \
    --sample 0.1 \
    --top 100
```

**Note**: Requires implementing `--sample` parameter in kmer analyzer.

### Option C: Use Smaller Dataset

Test with the 10K sequence test dataset:
```bash
./opengenome analyze kmer \
    --input /data/parquet/test_10k \
    --output /results/kmer_16_test \
    --k 16 \
    --top 100
```

## Performance Estimates (with 8GB workers)

| K-value | Sequences | Executor Memory | Expected Time | Status |
|---------|-----------|-----------------|---------------|--------|
| k=8     | 214,950   | 3.5GB          | ~15 min       | ✅ Works |
| k=16    | 214,950   | 7GB            | ~30-45 min    | Should work |
| k=32    | 214,950   | 12GB           | ~60-90 min    | Requires testing |

## Current Demo Script

The `demo_end_to_end.sh` currently skips k=16 and k=32 to ensure completion on limited hardware:

```bash
# Only runs k=8 analysis
for k in 8; do
    echo "[K-mer Analysis] k=$k"
    ./opengenome analyze kmer --input /data/parquet/plasmids_phage --output /results/demo/kmer_${k} --k $k --top 100
done
```

To enable k=16 and k=32, first increase worker memory per Option A above.
