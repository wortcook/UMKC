# OpenGenome2 Web UI

Simple web interface for OpenGenome2 genomic analysis platform.

## Overview

The Web UI provides a browser-based interface to all OpenGenome2 capabilities:

- **Data Ingestion**: Upload local FASTA files or download from HuggingFace
- **Analysis**: Run k-mer and codon usage analysis
- **Results**: Browse and download analysis results

## Quick Start

1. **Start all services including web UI:**
   ```bash
   make up
   ```

2. **Open web interface:**
   ```bash
   make web-ui
   ```
   Or navigate to: http://localhost:5000

3. **View web logs:**
   ```bash
   make logs-web
   ```

## Features

### Home Page
- System status dashboard
- Quick navigation to all features
- Dataset and result counters

### Ingest Page
- **Local File Upload**: Drag and drop FASTA files (gzipped or plain)
- **HuggingFace Download**: Pre-configured organelle sequences
- **Options**: Chunk size, compression, append mode
- Real-time progress and statistics

### Analyze Page
- **Dataset Browser**: View available Parquet datasets
- **K-mer Analysis**: Configure k-mer size, filters, and output
- **Codon Analysis**: Configure reading frame, RSCU calculation
- Click dataset paths to auto-fill input fields

### Results Page
- Browse all completed analyses
- View file sizes and modification dates
- Quick access to result files

## API Endpoints

All operations are available via REST API:

### Health
```bash
GET /api/health
```

### Data Management
```bash
GET  /api/datasets     # List Parquet datasets
GET  /api/results      # List analysis results
```

### Ingestion
```bash
POST /api/ingest/local      # Upload local FASTA
POST /api/ingest/organelle  # Download organelle sequences
```

### Analysis
```bash
POST /api/analyze/kmer   # Run k-mer analysis
POST /api/analyze/codon  # Run codon analysis
```

## Architecture

```
┌─────────────┐
│   Browser   │
└──────┬──────┘
       │ HTTP
       ↓
┌─────────────┐
│  Flask App  │ (Port 5000)
│  Web UI     │
└──────┬──────┘
       │
       ├─→ Ingestion Module (FASTA → Parquet)
       │
       └─→ Analysis Module (via Spark)
            │
            ↓
       ┌──────────────┐
       │ Spark Master │
       │  + Workers   │
       └──────────────┘
```

## Technology Stack

- **Framework**: Flask 3.0
- **Frontend**: Vanilla JavaScript (no dependencies)
- **Styling**: CSS (no frameworks)
- **Backend**: Python 3.11
- **Processing**: PySpark, BioPython

## Configuration

Environment variables (in `.env`):

```bash
FLASK_ENV=production
FLASK_DEBUG=false
```

## Volume Mounts

The web container shares volumes with other services:

- `/data` - Parquet datasets and uploads
- `/results` - Analysis results
- `/cache` - HuggingFace download cache
- `/logs` - Application logs

## Security Considerations

**This is a development/research tool. For production use:**

1. Add authentication/authorization
2. Implement rate limiting
3. Add HTTPS/TLS
4. Validate file uploads more strictly
5. Implement user quotas
6. Add audit logging

## Troubleshooting

**Web UI not accessible:**
```bash
docker-compose logs web
make validate
```

**Upload fails:**
- Check file size (1GB limit)
- Verify FASTA format
- Check available disk space

**Analysis fails:**
- Ensure Spark cluster is running: `make validate`
- Check dataset path exists
- View Spark UI: `make spark-ui`

## Development

Run in development mode:
```bash
cd src
FLASK_DEBUG=true python -m flask --app opengenome.web.app run --port 5000
```

## Limitations

Current version does not support:
- Multi-user sessions
- Authentication
- File downloads via browser
- Real-time progress updates
- Visualization rendering

These features use the existing CLI and analysis modules.
