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
        from opengenome.ingestion.converter import FastaToParquetConverter
        
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
        converter = FastaToParquetConverter(
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
        from opengenome.analysis.kmer_analyzer import KmerAnalyzer
        
        data = request.json
        input_dir = DATA_DIR / data.get('input_dir', 'organelles')
        k = int(data.get('k', 4))
        output_path = RESULTS_DIR / 'kmer' / f"k{k}_results.parquet"
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"Starting k-mer analysis: k={k}, input={input_dir}")
        
        analyzer = KmerAnalyzer(k=k)
        try:
            result = analyzer.analyze(
                input_path=str(input_dir),
                output_path=str(output_path)
            )
            
            logger.info(f"K-mer analysis completed: {result}")
            return jsonify({'status': 'success', 'result': result})
        finally:
            analyzer.stop()
        
    except Exception as e:
        logger.error(f"K-mer analysis failed: {str(e)}", exc_info=True)
        return jsonify({'status': 'error', 'message': str(e)}), 500


@app.route('/api/analyze/codon', methods=['POST'])
def api_analyze_codon():
    """Run codon usage analysis"""
    try:
        # Lazy import to avoid Spark initialization at startup
        from opengenome.analysis.codon_analyzer import CodonAnalyzer
        
        data = request.json
        input_dir = DATA_DIR / data.get('input_dir', 'organelles')
        output_path = RESULTS_DIR / 'codon' / 'codon_results.parquet'
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"Starting codon analysis: input={input_dir}")
        
        analyzer = CodonAnalyzer()
        try:
            result = analyzer.analyze(
                input_path=str(input_dir),
                output_path=str(output_path)
            )
            
            logger.info(f"Codon analysis completed: {result}")
            return jsonify({'status': 'success', 'result': result})
        finally:
            analyzer.stop()
        
    except Exception as e:
        logger.error(f"Codon analysis failed: {str(e)}", exc_info=True)
        return jsonify({'status': 'error', 'message': str(e)}), 500


@app.route('/api/datasets', methods=['GET'])
def api_datasets():
    """List available datasets"""
    try:
        datasets = []
        if DATA_DIR.exists():
            for item in DATA_DIR.iterdir():
                if item.is_dir() and item.name != 'uploads':
                    # Count parquet files
                    parquet_files = list(item.glob('*.parquet'))
                    if parquet_files:
                        datasets.append({
                            'name': item.name,
                            'path': str(item.relative_to(DATA_DIR)),
                            'file_count': len(parquet_files)
                        })
        
        return jsonify({'datasets': datasets})
        
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
    """List available analysis results"""
    try:
        results = []
        if RESULTS_DIR.exists():
            for analysis_type in RESULTS_DIR.iterdir():
                if analysis_type.is_dir():
                    for result_file in analysis_type.glob('*.parquet'):
                        results.append({
                            'type': analysis_type.name,
                            'name': result_file.name,
                            'path': str(result_file.relative_to(RESULTS_DIR)),
                            'size': result_file.stat().st_size
                        })
        
        return jsonify({'results': results})
        
    except Exception as e:
        logger.error(f"Failed to list results: {str(e)}", exc_info=True)
        return jsonify({'status': 'error', 'message': str(e)}), 500


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
