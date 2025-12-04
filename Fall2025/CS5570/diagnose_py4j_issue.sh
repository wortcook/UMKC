#!/bin/bash
#
# Diagnostic script to debug py4j installation issues
#

echo "==== Docker Version ===="
docker --version
docker-compose --version

echo -e "\n==== Container Status ===="
docker-compose ps

echo -e "\n==== Checking if containers are running ===="
docker ps | grep opengenome

echo -e "\n==== Checking py4j in master container ===="
docker exec opengenome-spark-master pip list 2>&1 | grep -i py4j || echo "py4j NOT FOUND"

echo -e "\n==== Checking py4j in worker container ===="
docker exec opengenome-spark-worker-1 pip list 2>&1 | grep -i py4j || echo "py4j NOT FOUND"

echo -e "\n==== Attempting to import py4j in master ===="
docker exec opengenome-spark-master python3 -c "import py4j; print(f'SUCCESS: py4j {py4j.__version__}')" 2>&1

echo -e "\n==== Attempting to import py4j in worker ===="
docker exec opengenome-spark-worker-1 python3 -c "import py4j; print(f'SUCCESS: py4j {py4j.__version__}')" 2>&1

echo -e "\n==== Testing opengenome CLI ===="
./opengenome --help 2>&1 | head -5

echo -e "\n==== Checking Docker images ===="
docker images | grep -E "cs5570|opengenome|spark"

echo -e "\n==== Checking when master image was built ===="
docker inspect cs5570-spark-master:latest --format='{{.Created}}' 2>/dev/null || echo "Image not found"

echo -e "\n==== Checking Dockerfile for py4j ===="
grep -n "py4j" docker/spark-master/Dockerfile docker/spark-worker/Dockerfile

echo -e "\n==== All installed packages in master ===="
docker exec opengenome-spark-master pip list 2>&1

echo -e "\n==== Python version in master ===="
docker exec opengenome-spark-master python3 --version 2>&1

echo -e "\n==== PySpark version in master ===="
docker exec opengenome-spark-master python3 -c "import pyspark; print(pyspark.__version__)" 2>&1
