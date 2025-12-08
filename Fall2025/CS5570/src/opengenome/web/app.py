"""
OpenGenome2 Web UI - Flask application for browser-based genomic data ingestion and analysis
"""
from flask import Flask, render_template, request, jsonify, send_file
import os
import logging
from pathlib import Path

# Initialize Flask app
app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 1024 * 1024 * 1024  # 1GB max file size

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Get base paths from environment
DATA_DIR = Path(os.getenv('DATA_DIR', '/data'))
RESULTS_DIR = Path(os.getenv('RESULTS_DIR', '/results'))


# ==================== HTML Pages ====================

@app.route('/')
def index():
    """Home page with system status"""
    return render_template('index.html')


@app.route('/ingest')
def ingest():
    """Data ingestion page"""
    return render_template('ingest.html')


@app.route('/analyze')
def analyze():
    """Analysis page"""
    return render_template('analyze.html')


@app.route('/results')
def results():
    """Results browser page"""
    return render_template('results.html')


@app.route('/search')
def search():
    """Sequence search page"""
    return render_template('search.html')


# ==================== API Endpoints ====================

@app.route('/api/health', methods=['GET'])
def api_health():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'service': 'opengenome-web',
        'data_dir': str(DATA_DIR),
        'results_dir': str(RESULTS_DIR)
    })


@app.route('/api/ingest/organelle', methods=['POST'])
def api_ingest_organelle():
    """Ingest organelle genomes from HuggingFace"""
    try:
        # Lazy import to avoid Spark initialization at startup
        from opengenome.cli.main import ingest_organelle_impl
        
        data = request.json
        dataset_name = data.get('dataset_name', 'LynixID/NCBI_Organelles')
        output_dir = DATA_DIR / 'organelles'
        chunk_size = int(data.get('chunk_size', 10000))
        compression = data.get('compression', 'snappy')
        max_sequences = data.get('max_sequences')
        if max_sequences:
            max_sequences = int(max_sequences)
        
        logger.info(f"Starting organelle ingestion: {dataset_name}")
        
        # Run ingestion
        stats = ingest_organelle_impl(
            dataset_name=dataset_name,
            output_dir=str(output_dir),
            chunk_size=chunk_size,
            compression=compression,
            max_sequences=max_sequences
        )
        
        logger.info(f"Organelle ingestion completed: {stats}")
        return jsonify({'status': 'success', 'stats': stats})
        
    except Exception as e:
        logger.error(f"Organelle ingestion failed: {str(e)}", exc_info=True)
        return jsonify({'status': 'error', 'message': str(e)}), 500


@app.route('/api/ingest/local', methods=['POST'])
def api_ingest_local():
    """Ingest local FASTA files"""
    try:
        # Lazy import to avoid Spark initialization at startup
        from opengenome.ingestion.converter import FASTAToParquetConverter
        
        if 'file' not in request.files:
            return jsonify({'status': 'error', 'message': 'No file provided'}), 400
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({'status': 'error', 'message': 'Empty filename'}), 400
        
        # Save uploaded file
        upload_path = DATA_DIR / 'uploads' / file.filename
        upload_path.parent.mkdir(parents=True, exist_ok=True)
        file.save(upload_path)
        
        # Get parameters
        source_name = request.form.get('source_name', 'local')
        output_dir = DATA_DIR / source_name
        chunk_size = int(request.form.get('chunk_size', 10000))
        compression = request.form.get('compression', 'snappy')
        append = request.form.get('append', 'false').lower() == 'true'
        max_sequences = request.form.get('max_sequences')
        if max_sequences:
            max_sequences = int(max_sequences)
        
        logger.info(f"Starting local file ingestion: {file.filename}")
        
        # Convert to Parquet
        converter = FASTAToParquetConverter(
            chunk_rows=chunk_size,
            compression=compression
        )
        
        stats = converter.convert(
            fasta_path=upload_path,
            source_name=source_name,
            output_subdir=None,  # Use source_name directly in path
            max_sequences=max_sequences,
            append=append
        )
        
        logger.info(f"Local ingestion completed: {stats}")
        return jsonify({'status': 'success', 'stats': stats})
        
    except Exception as e:
        logger.error(f"Local ingestion failed: {str(e)}", exc_info=True)
        return jsonify({'status': 'error', 'message': str(e)}), 500


@app.route('/api/analyze/kmer', methods=['POST'])
def api_analyze_kmer():
    """Run k-mer frequency analysis"""
    try:
        # Lazy import to avoid Spark initialization at startup
        from opengenome.analysis.kmer import KmerAnalyzer
        from opengenome.spark.session import get_spark_session
        
        data = request.json
        input_path = data.get('input', '/data/parquet/organelle')
        k = int(data.get('k', 6))
        output_path = data.get('output', f'/results/kmer/k{k}_results')
        skip_n = data.get('skip_n', True)
        min_count = int(data.get('min_count', 1))
        
        logger.info(f"Starting k-mer analysis: k={k}, input={input_path}")
        
        spark = get_spark_session()
        analyzer = KmerAnalyzer(spark=spark, k=k)
        
        result_df = analyzer.analyze(
            input_path=input_path,
            output_path=output_path,
            skip_n=skip_n,
            min_count=min_count
        )
        
        # Get stats
        unique_kmers = result_df.count()
        
        logger.info(f"K-mer analysis completed: {unique_kmers} unique k-mers")
        return jsonify({
            'status': 'success', 
            'result': {
                'unique_kmers': unique_kmers,
                'k': k,
                'output_path': output_path
            }
        })
        
    except Exception as e:
        logger.error(f"K-mer analysis failed: {str(e)}", exc_info=True)
        return jsonify({'status': 'error', 'message': str(e)}), 500


@app.route('/api/analyze/codon', methods=['POST'])
def api_analyze_codon():
    """Run codon usage analysis"""
    try:
        # Lazy import to avoid Spark initialization at startup
        from opengenome.analysis.codon import CodonAnalyzer
        from opengenome.spark.session import get_spark_session
        
        data = request.json
        input_path = data.get('input', '/data/parquet/organelle')
        output_path = data.get('output', '/results/codon/codon_results')
        frame = int(data.get('frame', 0))
        skip_n = data.get('skip_n', True)
        min_count = int(data.get('min_count', 1))
        
        logger.info(f"Starting codon analysis: input={input_path}, frame={frame}")
        
        spark = get_spark_session()
        analyzer = CodonAnalyzer(spark=spark, frame=frame)
        
        result_df = analyzer.analyze(
            input_path=input_path,
            output_path=output_path,
            skip_n=skip_n,
            min_count=min_count
        )
        
        # Get stats
        total_codons = result_df.count()
        
        logger.info(f"Codon analysis completed: {total_codons} codons")
        return jsonify({
            'status': 'success', 
            'result': {
                'total_codons': total_codons,
                'output_path': output_path
            }
        })
        
    except Exception as e:
        logger.error(f"Codon analysis failed: {str(e)}", exc_info=True)
        return jsonify({'status': 'error', 'message': str(e)}), 500


@app.route('/api/datasets', methods=['GET'])
def api_datasets():
    """List available datasets in the parquet directory"""
    try:
        datasets = []
        parquet_dir = DATA_DIR / 'parquet'
        
        if parquet_dir.exists():
            for item in parquet_dir.iterdir():
                if item.is_dir():
                    # Count parquet files (including in subdirectories)
                    parquet_files = list(item.glob('**/*.parquet'))
                    if parquet_files:
                        # Calculate total size
                        total_size = sum(f.stat().st_size for f in parquet_files)
                        size_mb = total_size / (1024 * 1024)
                        
                        datasets.append({
                            'name': item.name,
                            'path': f'/data/parquet/{item.name}',
                            'shards': len(parquet_files),
                            'size_mb': size_mb,
                            'file_count': len(parquet_files)
                        })
        
        return jsonify({'status': 'success', 'datasets': datasets})
        
    except Exception as e:
        logger.error(f"Failed to list datasets: {str(e)}", exc_info=True)
        return jsonify({'status': 'error', 'message': str(e)}), 500


@app.route('/api/analyze/search', methods=['POST'])
def api_analyze_search():
    """Search for sequences containing a specific pattern"""
    try:
        # Lazy import to avoid Spark initialization at startup
        from opengenome.analysis.sequence_search import SequenceSearcher
        from opengenome.spark.session import get_spark_session
        from datetime import datetime
        
        data = request.json
        pattern = data.get('pattern')
        if not pattern:
            return jsonify({'status': 'error', 'message': 'Pattern is required'}), 400
        
        # Validate pattern server-side
        try:
            SequenceSearcher.validate_dna_pattern(pattern)
        except ValueError as e:
            return jsonify({'status': 'error', 'message': str(e)}), 400
        
        input_dir = DATA_DIR / data.get('input_dir', 'organelles')
        case_sensitive = data.get('case_sensitive', False)
        reverse_complement = data.get('reverse_complement', False)
        max_results = data.get('max_results')
        if max_results:
            max_results = int(max_results)
        
        # Create timestamped output path
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_path = RESULTS_DIR / 'search' / f"search_{timestamp}.parquet"
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"Starting sequence search: pattern={pattern}, input={input_dir}, reverse_complement={reverse_complement}")
        
        spark = get_spark_session(app_name="WebSequenceSearch")
        searcher = SequenceSearcher(spark)
        try:
            result = searcher.search(
                input_path=str(input_dir),
                pattern=pattern,
                output_path=str(output_path),
                case_sensitive=case_sensitive,
                max_results=max_results,
                search_reverse_complement=reverse_complement
            )
            
            logger.info(f"Search completed: {result}")
            return jsonify({'status': 'success', 'result': result})
        finally:
            # Note: Not stopping spark session as it's managed by the web app lifecycle
            pass
        
    except Exception as e:
        logger.error(f"Sequence search failed: {str(e)}", exc_info=True)
        return jsonify({'status': 'error', 'message': str(e)}), 500


@app.route('/api/results', methods=['GET'])
def api_results():
    """List available analysis results (grouped by result directory)"""
    try:
        results = []
        if RESULTS_DIR.exists():
            for item in RESULTS_DIR.iterdir():
                if item.is_dir():
                    # Count parquet files and calculate total size
                    parquet_files = list(item.glob('**/*.parquet'))
                    if parquet_files:
                        total_size = sum(f.stat().st_size for f in parquet_files)
                        # Get most recent modification time
                        latest_mtime = max(f.stat().st_mtime for f in parquet_files)
                        
                        results.append({
                            'name': item.name,
                            'path': f'/results/{item.name}',
                            'size_mb': total_size / (1024 * 1024),
                            'file_count': len(parquet_files),
                            'modified': latest_mtime * 1000  # JavaScript expects milliseconds
                        })
        
        # Sort by modification time, most recent first
        results.sort(key=lambda x: x['modified'], reverse=True)
        
        return jsonify({'status': 'success', 'results': results})
        
    except Exception as e:
        logger.error(f"Failed to list results: {str(e)}", exc_info=True)
        return jsonify({'status': 'error', 'message': str(e)}), 500


@app.route('/api/results/<name>/preview', methods=['GET'])
def api_results_preview(name):
    """Preview the first N rows of a result dataset"""
    try:
        import pandas as pd
        
        result_path = RESULTS_DIR / name
        if not result_path.exists():
            return jsonify({'status': 'error', 'message': f'Result {name} not found'}), 404
        
        # Find parquet files
        parquet_files = list(result_path.glob('**/*.parquet'))
        if not parquet_files:
            return jsonify({'status': 'error', 'message': 'No parquet files found'}), 404
        
        # Read first parquet file for preview
        df = pd.read_parquet(parquet_files[0])
        
        # Get total rows across all files (approximate)
        total_rows = len(df)
        if len(parquet_files) > 1:
            total_rows = total_rows * len(parquet_files)  # Approximate
        
        # Get first 50 rows for preview
        preview_df = df.head(50)
        
        return jsonify({
            'status': 'success',
            'name': name,
            'columns': list(preview_df.columns),
            'preview': preview_df.to_dict(orient='records'),
            'total_rows': total_rows,
            'file_count': len(parquet_files)
        })
        
    except Exception as e:
        logger.error(f"Failed to preview result {name}: {str(e)}", exc_info=True)
        return jsonify({'status': 'error', 'message': str(e)}), 500


@app.route('/api/results/<name>/download', methods=['GET'])
def api_results_download(name):
    """Download result as CSV"""
    try:
        import pandas as pd
        import io
        
        result_path = RESULTS_DIR / name
        if not result_path.exists():
            return jsonify({'status': 'error', 'message': f'Result {name} not found'}), 404
        
        # Find parquet files
        parquet_files = list(result_path.glob('**/*.parquet'))
        if not parquet_files:
            return jsonify({'status': 'error', 'message': 'No parquet files found'}), 404
        
        # Read all parquet files and combine
        dfs = []
        for pf in parquet_files[:10]:  # Limit to first 10 files to avoid memory issues
            dfs.append(pd.read_parquet(pf))
        
        df = pd.concat(dfs, ignore_index=True)
        
        # Limit to 100k rows for download
        if len(df) > 100000:
            df = df.head(100000)
            logger.warning(f"Download for {name} truncated to 100k rows")
        
        # Convert to CSV
        csv_buffer = io.StringIO()
        df.to_csv(csv_buffer, index=False)
        csv_data = csv_buffer.getvalue()
        
        from flask import Response
        return Response(
            csv_data,
            mimetype='text/csv',
            headers={'Content-Disposition': f'attachment; filename={name}.csv'}
        )
        
    except Exception as e:
        logger.error(f"Failed to download result {name}: {str(e)}", exc_info=True)
        return jsonify({'status': 'error', 'message': str(e)}), 500


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
