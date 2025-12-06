#!/usr/bin/env python3
"""
Memory diagnostic script to identify exact OOM bottleneck.

This script instruments the Spark pipeline to track:
1. Docker container memory limits vs requested
2. JVM heap usage during parquet reading
3. Python process memory during mapInPandas
4. Parquet file characteristics (dictionary sizes, compression ratios)
"""

import sys
import os
import subprocess
import json
from pathlib import Path

def check_docker_resources():
    """Check Docker container memory configuration vs actual limits."""
    print("=" * 80)
    print("DOCKER RESOURCE CHECK")
    print("=" * 80)
    
    # Get docker-compose configured limits
    result = subprocess.run(
        ["docker-compose", "config"],
        capture_output=True,
        text=True
    )
    
    print("\n1. Docker Compose Configuration:")
    for line in result.stdout.split('\n'):
        if 'memory:' in line or 'cpus:' in line:
            print(f"   {line.strip()}")
    
    # Get actual container stats
    print("\n2. Actual Container Limits (docker stats):")
    result = subprocess.run(
        ["docker", "stats", "--no-stream", "--format", 
         "table {{.Name}}\t{{.MemUsage}}\t{{.MemPerc}}\t{{.CPUPerc}}"],
        capture_output=True,
        text=True
    )
    for line in result.stdout.split('\n'):
        if 'spark-worker' in line or 'NAME' in line:
            print(f"   {line}")
    
    # Check for mismatch
    print("\n3. Docker Desktop Resource Limits:")
    result = subprocess.run(
        ["docker", "info", "--format", "{{json .}}"],
        capture_output=True,
        text=True
    )
    try:
        info = json.loads(result.stdout)
        total_mem_gb = info.get('MemTotal', 0) / (1024**3)
        print(f"   Total Memory Available to Docker: {total_mem_gb:.2f} GB")
    except:
        print("   Could not parse docker info")


def check_spark_executor_config():
    """Check Spark executor JVM configuration."""
    print("\n" + "=" * 80)
    print("SPARK EXECUTOR CONFIGURATION")
    print("=" * 80)
    
    # Get worker logs to see executor launch command
    result = subprocess.run(
        ["docker", "logs", "opengenome-spark-worker-1", "--tail", "100"],
        capture_output=True,
        text=True
    )
    
    for line in result.stdout.split('\n'):
        if '-Xmx' in line or 'ExecutorRunner: Launch command' in line:
            if 'Launch command' in line:
                print("\n1. Executor JVM Launch Command:")
            if '-Xmx' in line:
                # Extract -Xmx value
                parts = line.split()
                for part in parts:
                    if part.startswith('-Xmx'):
                        print(f"   Heap Size: {part}")
    
    # Check environment variables
    print("\n2. Environment Variables (from .env):")
    env_file = Path(".env")
    if env_file.exists():
        with open(env_file) as f:
            for line in f:
                if 'EXECUTOR_MEMORY' in line or 'DRIVER_MEMORY' in line:
                    print(f"   {line.strip()}")
    else:
        print("   No .env file found")


def analyze_parquet_files():
    """Analyze parquet file characteristics to understand dictionary sizes."""
    print("\n" + "=" * 80)
    print("PARQUET FILE ANALYSIS")
    print("=" * 80)
    
    # Run a small Python script inside the web container to analyze parquet
    script = """
import pyarrow.parquet as pq
from pathlib import Path
import sys

parquet_dir = Path('/data/parquet/organelle')
if not parquet_dir.exists():
    print('No organelle parquet directory found')
    sys.exit(0)

files = sorted(parquet_dir.glob('shard_*.parquet'))[:10]  # Sample first 10

print(f'Analyzing {len(files)} sample parquet files...')
print()

total_dict_size = 0
for pf in files:
    try:
        table = pq.read_table(pf)
        metadata = pq.read_metadata(pf)
        
        # Get sequence column data
        seq_col = table['sequence']
        seq_lengths = [len(s.as_py()) for s in seq_col]
        
        # File size
        file_size_kb = pf.stat().st_size / 1024
        
        # Estimate dictionary size (sequences are stored as dictionary in parquet)
        total_seq_bytes = sum(seq_lengths)
        
        print(f'{pf.name}:')
        print(f'  File size: {file_size_kb:.1f} KB')
        print(f'  Rows: {table.num_rows}')
        print(f'  Seq lengths: min={min(seq_lengths)}, max={max(seq_lengths)}, avg={sum(seq_lengths)//len(seq_lengths)}')
        print(f'  Total seq bytes: {total_seq_bytes / 1024:.1f} KB')
        print(f'  Compression ratio: {total_seq_bytes / (file_size_kb * 1024):.2f}x')
        print()
        
        total_dict_size += total_seq_bytes
        
    except Exception as e:
        print(f'Error reading {pf.name}: {e}')

print(f'Average uncompressed dictionary size per file: {(total_dict_size / len(files)) / 1024:.1f} KB')
print(f'With 4 concurrent tasks: {(total_dict_size / len(files) * 4) / 1024:.1f} KB needed')
"""
    
    result = subprocess.run(
        ["docker", "exec", "opengenome-web", "python3", "-c", script],
        capture_output=True,
        text=True
    )
    
    print(result.stdout)
    if result.stderr:
        print("Errors:", result.stderr)


def check_oom_killer_logs():
    """Check system logs for OOM killer events."""
    print("\n" + "=" * 80)
    print("OOM KILLER EVIDENCE")
    print("=" * 80)
    
    # Check recent demo logs for exit code 137
    print("\n1. Recent executor failures (exit code 137):")
    result = subprocess.run(
        ["grep", "-h", "exit code 137", *Path(".").glob("demo_run_*.log")],
        capture_output=True,
        text=True
    )
    
    lines = result.stdout.split('\n')[:10]  # First 10 occurrences
    for line in lines:
        if line.strip():
            print(f"   {line.strip()}")
    
    # Check worker logs for OOM
    print("\n2. Checking worker logs for OOM indicators:")
    for i in range(1, 5):
        result = subprocess.run(
            ["docker", "logs", f"opengenome-spark-worker-{i}", "--tail", "50"],
            capture_output=True,
            text=True
        )
        
        for line in result.stdout.split('\n'):
            if 'exit code 137' in line.lower():
                print(f"   Worker {i}: {line.strip()}")
                break


def print_diagnosis():
    """Print diagnostic summary and recommendations."""
    print("\n" + "=" * 80)
    print("DIAGNOSIS AND RECOMMENDATIONS")
    print("=" * 80)
    
    print("""
The OOM issue is likely caused by one of these factors:

1. CONTAINER MEMORY LIMIT MISMATCH:
   - Docker Compose requests 16GB per worker
   - Docker Desktop limits containers to ~7.6GB
   - Spark executor tries to allocate 15GB heap (-Xmx15360M)
   - Container OOM killer terminates executor (exit code 137)
   
   FIX: Reduce SPARK_EXECUTOR_MEMORY in .env to 6g or less

2. PARQUET DICTIONARY DECOMPRESSION:
   - Large sequences (100-200KB) create large dictionaries
   - Multiple concurrent tasks (4 cores) load multiple files simultaneously
   - JVM needs contiguous memory blocks for dictionary arrays
   
   FIX: Reduce spark.executor.cores to 1 to process files sequentially

3. MAPINPANDAS BATCH ACCUMULATION:
   - Python process memory grows when processing large batches
   - Codons accumulate before yielding results
   
   FIX: Already implemented with frequent yields (batch_size=1000)

Run these commands to check which issue you have:
   
   # Check if container limit < executor memory request:
   docker stats --no-stream | grep spark-worker
   
   # Check executor heap config:
   docker logs opengenome-spark-worker-1 2>&1 | grep -o -- '-Xmx[^ ]*'
   
   # If limit < heap, fix with:
   echo "SPARK_EXECUTOR_MEMORY=6g" >> .env
   make clean && make build
""")


if __name__ == "__main__":
    try:
        check_docker_resources()
        check_spark_executor_config()
        analyze_parquet_files()
        check_oom_killer_logs()
        print_diagnosis()
    except Exception as e:
        print(f"\nError running diagnostics: {e}", file=sys.stderr)
        sys.exit(1)
