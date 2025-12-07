# OpenGenome2 Web UI Demonstration Guide

**Duration:** 15-20 minutes  
**Prerequisites:** Docker containers running (`docker-compose up -d`)  
**URL:** http://localhost:5002

---

## 🎯 Overview

This guide walks you through all features of the OpenGenome2 web interface, demonstrating:
- System health monitoring
- Data ingestion (local upload & HuggingFace)
- K-mer frequency analysis
- Codon usage analysis
- Results browsing and download

---

## 📋 Step-by-Step Demonstration

### **Step 1: Access the Web Interface**

1. Open your web browser
2. Navigate to: **http://localhost:5002**
3. You should see the OpenGenome2 home page with:
   - Welcome message
   - System status indicators
   - Quick navigation cards

**Expected Result:** Green "System Healthy" indicator in the top-right corner

---

### **Step 2: Check System Status (Home Page)**

On the home page, observe:

**System Information:**
- ✅ Web Service: Running
- ✅ Spark Cluster: Connected
- ✅ Data Directory: /data
- ✅ Results Directory: /results

**Quick Stats** (if datasets exist):
- Number of available datasets
- Total sequences ingested
- Recent analyses count

**Navigation Cards:**
- 📥 Data Ingestion
- 🧬 Analysis Tools
- 📊 Results Browser
- 🔍 Sequence Search

---

### **Step 3: Data Ingestion - HuggingFace Download**

**Goal:** Download and ingest the organelle dataset from HuggingFace

1. Click **"Data Ingestion"** card or navigate to http://localhost:5002/ingest

2. Locate the **"Download from HuggingFace"** section

3. Fill in the form:
   - **Dataset Name:** `LynixID/NCBI_Organelles` (default)
   - **Output Name:** `organelle_demo`
   - **Chunk Size:** `10000` (sequences per shard)
   - **Compression:** `snappy` (default)
   - **Max Sequences:** Leave empty for full dataset, or enter `5000` for quick test

4. Click **"Start Download & Ingestion"**

**What Happens:**
- Browser shows "Processing..." spinner
- Backend downloads FASTA from HuggingFace
- Converts to Parquet format
- Stores in `/data/parquet/organelle_demo/`

**Expected Duration:**
- Full dataset (~32K sequences): 2-3 minutes
- Test sample (5K sequences): 30-45 seconds

**Expected Result:**
- Success message with statistics:
  - Total sequences processed
  - Total bases
  - Number of Parquet shards created
  - Output location

**Verification:**
- Dataset appears in the "Available Datasets" list
- Shows sequence count and size

---

### **Step 4: Data Ingestion - Local File Upload**

**Goal:** Upload a local FASTA file

1. On the same ingestion page, locate **"Upload Local File"** section

2. Prepare a test file:
   - Use an existing FASTA file, or
   - Use one from `data/downloads/` directory

3. Fill in the form:
   - **Select File:** Choose your FASTA file (.fasta, .fa, .fasta.gz, .fa.gz)
   - **Dataset Name:** `my_sequences`
   - **Chunk Size:** `1000`
   - **Compression:** `snappy`

4. Click **"Upload & Ingest"**

**What Happens:**
- File uploads to server
- Parses FASTA records
- Converts to Parquet shards
- Stores in specified output directory

**Expected Result:**
- Upload progress bar (for large files)
- Success message with ingestion statistics
- New dataset appears in dataset list

**Note:** For demonstration purposes, uploading a small subset file is recommended.

---

### **Step 5: Browse Available Datasets**

1. Scroll to the **"Available Datasets"** section on the ingestion page

2. You should see:
   - `organelle_demo` (from Step 3)
   - `my_sequences` (from Step 4)
   - Any pre-existing datasets (`organelle`, `plasmids_phage`)

3. For each dataset, note:
   - Dataset name
   - Number of Parquet files (shards)
   - Total size on disk
   - Location path

**Use This Information:** You'll need the dataset name for analysis in the next steps

---

### **Step 6: K-mer Analysis**

**Goal:** Run k-mer frequency analysis on a dataset

1. Click **"Analysis Tools"** or navigate to http://localhost:5002/analyze

2. Locate the **"K-mer Analysis"** section

3. Fill in the form:
   - **Dataset:** Select `organelle_demo` from dropdown
   - **K value:** `6` (start small for quick results)
   - **Output Name:** `kmer_6_demo`
   - **Skip N:** ✅ Checked (skip ambiguous bases)
   - **Min Count:** `1` (include all k-mers)
   - **Sample Size:** Leave empty for full analysis, or enter `5000` for quick test

4. Click **"Run K-mer Analysis"**

**What Happens:**
- Spark cluster processes the dataset
- Extracts all k-mers from sequences
- Counts frequency of each unique k-mer
- Saves results to `/results/kmer_6_demo/`

**Expected Duration:**
- Full dataset (32K sequences): 1-2 minutes
- Sample (5K sequences): 20-30 seconds

**Expected Result:**
- Success message showing:
  - Number of unique k-mers found
  - Total k-mer occurrences
  - Output location
  - Processing time

**Interpretation:**
- For k=6: Expect 4,000-4,500 unique k-mers (maximum possible is 4^6 = 4,096)
- Higher frequencies indicate common motifs in the genome

---

### **Step 7: K-mer Analysis - Different K Values**

**Goal:** Compare k-mer distributions at different lengths

Repeat Step 6 with different k values:

1. **k=8** (output: `kmer_8_demo`)
   - Expected: ~12,000-15,000 unique k-mers
   - Duration: ~2-3 minutes
   - Use case: Medium-length motif detection

2. **k=12** (output: `kmer_12_demo`)
   - Expected: ~1-2 million unique k-mers
   - Duration: ~3-5 minutes
   - Use case: Longer pattern analysis

**Note:** Larger k values take longer and produce more unique k-mers

---

### **Step 8: Codon Usage Analysis**

**Goal:** Analyze codon frequency and calculate RSCU

1. On the Analysis page, locate **"Codon Usage Analysis"** section

2. Fill in the form:
   - **Dataset:** Select `organelle_demo`
   - **Output Name:** `codon_demo`
   - **Reading Frame:** `0` (default)
   - **Skip N:** ✅ Checked
   - **Skip Stop Codons:** ⬜ Unchecked (include stop codons)
   - **Calculate RSCU:** ✅ Checked (Relative Synonymous Codon Usage)
   - **Min Count:** `1`

3. Click **"Run Codon Analysis"**

**What Happens:**
- Extracts codons (triplets) from sequences
- Counts frequency of each of 64 possible codons
- Maps codons to amino acids
- Calculates RSCU (if selected)
- Saves results to `/results/codon_demo/`

**Expected Duration:**
- Full dataset: 2-4 minutes
- Sample: 30-60 seconds

**Expected Result:**
- Success message with:
  - Total codons analyzed (e.g., ~10-50 million)
  - 64 unique codons identified
  - Frequency distribution
  - RSCU values (if calculated)

**Biological Insight:**
- Shows codon preference in the genome
- RSCU > 1: Codon used more than expected
- RSCU < 1: Codon used less than expected
- Useful for gene expression optimization

---

### **Step 9: Browse Analysis Results**

**Goal:** View and download completed analyses

1. Click **"Results Browser"** or navigate to http://localhost:5002/results

2. You should see a list of all completed analyses:
   - `kmer_6_demo/`
   - `kmer_8_demo/`
   - `kmer_12_demo/`
   - `codon_demo/`
   - Any pre-existing results

3. For each result, note:
   - Result name and type
   - Number of output files
   - Total size
   - Creation timestamp

4. **Explore a Result:**
   - Click on a result name (e.g., `kmer_6_demo`)
   - View detailed file listing
   - See Parquet file sizes
   - Note file counts

5. **Download Results:**
   - Most results are in Parquet format
   - Can be opened with pandas: `pd.read_parquet()`
   - Or use Spark: `spark.read.parquet()`

---

### **Step 10: Check Analysis via API**

**Goal:** Use REST API endpoints directly (optional, for developers)

Open a terminal or use browser dev tools:

1. **Health Check:**
   ```bash
   curl http://localhost:5002/api/health
   ```
   Expected: `{"status": "healthy", ...}`

2. **List Datasets:**
   ```bash
   curl http://localhost:5002/api/datasets
   ```
   Expected: JSON array of datasets with metadata

3. **List Results:**
   ```bash
   curl http://localhost:5002/api/results
   ```
   Expected: JSON array of analysis results

4. **Start Analysis (POST):**
   ```bash
   curl -X POST http://localhost:5002/api/analyze/kmer \
     -H "Content-Type: application/json" \
     -d '{
       "dataset": "organelle_demo",
       "k": 6,
       "output_name": "kmer_api_test"
     }'
   ```
   Expected: `{"status": "success", "stats": {...}}`

---

### **Step 11: Monitor Progress (Spark UI)**

**Goal:** Observe Spark job execution in real-time

1. While an analysis is running, open **Spark UI:** http://localhost:8081

2. On the Spark Master page, observe:
   - **Running Applications:** Your analysis job should appear
   - **Worker Status:** 2 workers should be alive
   - **Resource Usage:** CPU and memory allocation

3. Click on the **Application ID** to see:
   - **Jobs:** MapReduce stages
   - **Stages:** Task breakdown
   - **Executors:** Worker node details
   - **Environment:** Configuration settings

**What to Look For:**
- All stages completing successfully (green checkmarks)
- No failed tasks (red indicators)
- Reasonable task duration (~1-10 seconds per task)
- Memory usage staying below limits

**Troubleshooting:**
- If you see failed tasks: Check memory settings
- If analysis hangs: Check worker logs
- If connection errors: Verify Spark master is running

---

### **Step 12: Sequence Search (Bonus)**

**Goal:** Search for specific sequence patterns

1. Navigate to http://localhost:5002/search (if implemented)

2. Enter a search query:
   - **Pattern:** `ATGATGATG` (start codon repeated)
   - **Dataset:** `organelle_demo`
   - **Method:** `exact` or `similarity`

3. Click **"Search"**

**Expected Result:**
- List of sequences containing the pattern
- Match positions within sequences
- Similarity scores (if using similarity search)

---

## 🎓 Advanced Demonstrations

### **Scenario 1: Comparative Analysis**

**Goal:** Compare k-mer distributions across multiple datasets

1. Ingest two different datasets:
   - `organelle_demo` (done)
   - Download `plasmids_phage` if not present

2. Run same k-mer analysis (k=6) on both:
   - `kmer_6_organelle`
   - `kmer_6_plasmid`

3. Compare results:
   - Download both Parquet files
   - Load in Python/pandas
   - Create comparison visualizations

**Expected Insight:**
- Different k-mer distributions indicate different sequence composition
- Organelles may show different patterns than plasmids

---

### **Scenario 2: Performance Testing**

**Goal:** Test system limits

1. **Small Dataset Test:**
   - Ingest with sample_size=1000
   - Run k-mer (k=6)
   - Note duration: ~10-20 seconds

2. **Medium Dataset Test:**
   - Ingest with sample_size=10000
   - Run k-mer (k=8)
   - Note duration: ~1-2 minutes

3. **Large Dataset Test:**
   - Full dataset (32K sequences)
   - Run k-mer (k=12)
   - Note duration: ~3-5 minutes
   - Monitor memory in Spark UI

**Observation:**
- Processing time scales roughly linearly with dataset size
- Memory usage increases with k value

---

### **Scenario 3: Batch Processing**

**Goal:** Run multiple analyses sequentially

1. Create a workflow:
   - Ingest dataset → k=6 → k=8 → k=12 → codon
   
2. Start first analysis, then queue others

3. Monitor in Spark UI:
   - Jobs should process sequentially
   - Each job releases resources when complete

**Expected Result:**
- All analyses complete successfully
- Total time = sum of individual times
- No resource contention

---

## 📊 Understanding Results

### **K-mer Analysis Output**

Result Parquet files contain:
- **Column 1: kmer** - The k-mer sequence (e.g., "ATGATG")
- **Column 2: count** - Number of occurrences
- **Column 3: frequency** - Percentage of total (if calculated)

**Example:**
```
kmer     count      frequency
AAAAAA   123456     0.0234
TTTTTT   98765      0.0187
ATGATG   45678      0.0087
```

### **Codon Analysis Output**

Result Parquet files contain:
- **codon** - Three-letter codon (e.g., "ATG")
- **count** - Number of occurrences
- **frequency** - Percentage
- **amino_acid** - Single letter code (e.g., "M")
- **rscu** - Relative Synonymous Codon Usage (if calculated)

**Example:**
```
codon  count     frequency  amino_acid  rscu
ATG    234567    0.0456     M           1.00
TTT    198765    0.0387     F           1.23
TTC    156789    0.0305     F           0.77
```

---

## 🐛 Troubleshooting

### **Issue: "Connection Refused" Error**

**Solution:**
1. Check containers are running:
   ```bash
   docker-compose ps
   ```
2. Restart if needed:
   ```bash
   docker-compose restart web
   ```

### **Issue: Analysis Takes Too Long**

**Solutions:**
- Use sample_size parameter to test with subset
- Reduce k value for k-mer analysis
- Check Spark UI for stuck tasks
- Review memory settings in `.env`

### **Issue: "Dataset Not Found"**

**Solution:**
1. Verify dataset name matches exactly (case-sensitive)
2. Check dataset exists:
   ```bash
   ls -la data/parquet/
   ```
3. Re-ingest if necessary

### **Issue: Out of Memory (OOM)**

**Symptoms:**
- Analysis fails partway through
- Spark workers disconnect
- "Exit code 137" in logs

**Solutions:**
1. Use smaller sample size
2. Reduce k value (for k-mer)
3. Check memory settings in `.env`
4. Restart containers:
   ```bash
   docker-compose restart
   ```

---

## 📝 Demonstration Checklist

Use this checklist to ensure you've covered all features:

- [ ] Accessed home page and verified system health
- [ ] Downloaded dataset from HuggingFace
- [ ] Uploaded local FASTA file (optional)
- [ ] Ran k-mer analysis with k=6
- [ ] Ran k-mer analysis with k=8 or k=12
- [ ] Ran codon usage analysis
- [ ] Browsed results page
- [ ] Downloaded a result file
- [ ] Checked Spark UI during analysis
- [ ] Used API endpoints directly (optional)
- [ ] Tested with different sample sizes
- [ ] Explored advanced scenarios (optional)

---

## 🎯 Key Takeaways

After completing this demonstration, you should understand:

1. **Data Ingestion:** How to load genomic data from multiple sources
2. **Analysis Workflow:** Running distributed analyses on large datasets
3. **Result Management:** Browsing and accessing analysis outputs
4. **Monitoring:** Using Spark UI to observe job execution
5. **Scalability:** How the system handles different data sizes
6. **Integration:** Using both web UI and REST API

---

## 📚 Next Steps

**For Users:**
- Load your own genomic datasets
- Experiment with different k values
- Compare results across datasets
- Export results to visualization tools

**For Developers:**
- Explore API endpoints in depth
- Integrate with external pipelines
- Customize analysis parameters
- Extend with new analysis types

**For Administrators:**
- Monitor resource usage
- Tune memory settings
- Scale worker nodes
- Implement backup strategies

---

## 🔗 Additional Resources

- **Main Documentation:** `README.md`
- **Architecture Details:** `docs/FINAL_PROJECT_SUMMARY.md`
- **API Documentation:** `src/opengenome/web/README.md`
- **Performance Guide:** `docs/KMER_MEMORY_REQUIREMENTS.md`
- **CLI Alternative:** Use `./opengenome` command-line tool

---

## ✅ Demo Complete!

You've successfully explored all major features of the OpenGenome2 web interface. The platform is now ready for:
- Production genomic analysis workflows
- Educational demonstrations
- Research applications
- Integration with existing bioinformatics pipelines

**Questions or Issues?** Check the main README.md or project documentation.
