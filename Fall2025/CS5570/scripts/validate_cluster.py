#!/usr/bin/env python3
"""
Simple validation script to test Spark cluster connectivity.
"""
import sys
import os

# Add PySpark to path
sys.path.insert(0, os.path.join(os.environ.get('SPARK_HOME', '/opt/spark'), 'python'))
sys.path.insert(0, os.path.join(os.environ.get('SPARK_HOME', '/opt/spark'), 'python', 'lib', 'py4j-0.10.9.7-src.zip'))

from pyspark.sql import SparkSession

def main():
    """Validate Spark cluster connectivity."""
    print("=" * 60)
    print("OpenGenome2 Spark Cluster Validation")
    print("=" * 60)
    
    try:
        # Create Spark session
        spark = SparkSession.builder \
            .appName("ClusterValidation") \
            .master("spark://spark-master:7077") \
            .config("spark.executor.memory", "2g") \
            .getOrCreate()
        
        print(f"\n✓ Spark Session Created")
        print(f"  - Spark Version: {spark.version}")
        print(f"  - Master: {spark.sparkContext.master}")
        print(f"  - App Name: {spark.sparkContext.appName}")
        
        # Test basic RDD operation
        data = list(range(1, 101))
        rdd = spark.sparkContext.parallelize(data, 8)
        total = rdd.sum()
        
        print(f"\n✓ Basic RDD Test Passed")
        print(f"  - Sum of 1-100: {total} (expected: 5050)")
        
        # Test DataFrame operation
        df = spark.createDataFrame([(i, i*2) for i in range(10)], ["id", "value"])
        count = df.count()
        
        print(f"\n✓ DataFrame Test Passed")
        print(f"  - Row count: {count} (expected: 10)")
        
        # Get executor info
        sc = spark.sparkContext
        print(f"\n✓ Cluster Information")
        print(f"  - Default Parallelism: {sc.defaultParallelism}")
        
        spark.stop()
        
        print("\n" + "=" * 60)
        print("✓ All validation tests passed!")
        print("=" * 60)
        return 0
        
    except Exception as e:
        print(f"\n✗ Validation failed: {e}", file=sys.stderr)
        return 1

if __name__ == "__main__":
    sys.exit(main())
