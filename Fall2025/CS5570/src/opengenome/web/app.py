"""
Simple Flask web application for OpenGenome2.
Provides web UI for ingestion and analysis operations.
"""

import os
import json
import logging
from pathlib import Path
from datetime import datetime
from flask import Flask, render_template, request, jsonify, send_file

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize Flask app
app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 1024 * 1024 * 1024  # 1GB max file size
app.config['UPLOAD_FOLDER'] = '/data/uploads'

# Ensure upload directory exists
Path(app.config['UPLOAD_FOLDER']).mkdir(parents=True, exist_ok=True)


@app.route('/')
def index():
    """Home page with navigation."""
    return render_template('index.html')


@app.route('/ingest')
def ingest_page():
    """Ingestion page."""
    return render_template('ingest.html')


@app.route('/analyze')
def analyze_page():
    """Analysis page."""
    return render_template('analyze.html')


@app.route('/results')
def results_page():
    """Results browser page."""
    return render_template('results.html')


# API Endpoints

@app.route('/api/ingest/organelle', methods=['POST'])
def api_ingest_organelle():
    """Ingest organelle sequences from HuggingFace."""
    try:
        # Import here to avoid issues if Spark isn't ready at startup
        from opengenome.ingestion import FASTADownloader, FASTAToParquetConverter
        
        data = request.get_json() or {}
        output = data.get('output', '/data/parquet/organelle')
        chunk_size = int(data.get('chunk_size', 50000))
        compression = data.get('compression', 'snappy')
        max_sequences = data.get('max_sequences')
        if max_sequences:
            max_sequences = int(max_sequences)
        
        # Download
        downloader = FASTADownloader()
        fasta_path = downloader.download_organelle_sequences()
        
        # Convert
        converter = FASTAToParquetConverter(
            chunk_rows=chunk_size,
            compression=compression,
            output_dir=Path(output).parent
        )
        
        stats = converter.convert(
            fasta_path=fasta_path,
            source_name="organelle",
            output_subdir=Path(output).name,
            max_sequences=max_sequences
        )
        
        return jsonify({
            'status': 'success',
            'stats': stats,
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Organelle ingestion failed: {e}")
        return jsonify({
            'status': 'error',
            'message': str(e)
@app.route('/api/ingest/local', methods=['POST'])
def api_ingest_local():
    """Ingest local FASTA file."""
    try:
        # Import here to avoid issues if Spark isn't ready at startup
        from opengenome.ingestion import FASTAToParquetConverter
        
        # Check if file was uploaded
        if 'file' not in request.files:
    try:
        # Check if file was uploaded
        if 'file' not in request.files:
            return jsonify({
                'status': 'error',
                'message': 'No file uploaded'
            }), 400
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({
                'status': 'error',
                'message': 'No file selected'
            }), 400
        
        # Get parameters
        output = request.form.get('output', '/data/parquet/local')
        source_name = request.form.get('source_name', 'local')
        chunk_size = int(request.form.get('chunk_size', 50000))
        compression = request.form.get('compression', 'snappy')
        append = request.form.get('append', 'false').lower() == 'true'
        max_sequences = request.form.get('max_sequences')
        if max_sequences:
            max_sequences = int(max_sequences)
        
        # Save uploaded file
        upload_path = Path(app.config['UPLOAD_FOLDER']) / file.filename
        file.save(str(upload_path))
        
        # Convert
        converter = FASTAToParquetConverter(
            chunk_rows=chunk_size,
            compression=compression,
            output_dir=Path(output).parent
        )
        
        stats = converter.convert(
            fasta_path=upload_path,
            source_name=source_name,
            output_subdir=Path(output).name,
            max_sequences=max_sequences,
            append=append
        )
        
        # Clean up uploaded file
        upload_path.unlink()
        
        return jsonify({
            'status': 'success',
            'stats': stats,
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Local ingestion failed: {e}")
        return jsonify({
            'status': 'error',
            'message': str(e)
@app.route('/api/analyze/kmer', methods=['POST'])
def api_analyze_kmer():
    """Run k-mer analysis."""
    try:
        # Import here to avoid issues if Spark isn't ready at startup
        from opengenome.analysis import KmerAnalyzer
        
        data = request.get_json()
        input_path = data.get('input')
        output = data.get('output', '/results/kmer')
        k = int(data.get('k', 5))
        skip_n = data.get('skip_n', True)
        min_count = int(data.get('min_count', 1))
        top = data.get('top')
        if top:
            top = int(top)
        
        if not input_path:
            return jsonify({
                'status': 'error',
                'message': 'Input path required'
            }), 400
        
        # Run analysis
        analyzer = KmerAnalyzer(
            spark_master="spark://spark-master:7077",
            app_name="OpenGenome2-KmerAnalysis-WebUI"
        )
        
        try:
            result = analyzer.analyze(
                input_path=input_path,
                output_path=output,
                k=k,
                skip_n=skip_n,
                min_count=min_count,
                top_n=top
            )
            
            return jsonify({
                'status': 'success',
                'result': result,
                'timestamp': datetime.now().isoformat()
            })
        finally:
            # Always stop Spark session to release resources
            analyzer.stop()  'status': 'success',
            'result': result,
            'timestamp': datetime.now().isoformat()
@app.route('/api/analyze/codon', methods=['POST'])
def api_analyze_codon():
    """Run codon usage analysis."""
    try:
        # Import here to avoid issues if Spark isn't ready at startup
        from opengenome.analysis import CodonAnalyzer
        
        data = request.get_json()
        input_path = data.get('input')
        output = data.get('output', '/results/codon')
        frame = int(data.get('frame', 0))
        skip_n = data.get('skip_n', True)
        skip_stops = data.get('skip_stops', False)
        min_count = int(data.get('min_count', 1))
        rscu = data.get('rscu', False)
        top = data.get('top')
        if top:
            top = int(top)
        
        if not input_path:
            return jsonify({
                'status': 'error',
                'message': 'Input path required'
            }), 400
        
        # Run analysis
        analyzer = CodonAnalyzer(
            spark_master="spark://spark-master:7077",
            app_name="OpenGenome2-CodonAnalysis-WebUI"
        )
        
        try:
            result = analyzer.analyze(
                input_path=input_path,
                output_path=output,
                frame=frame,
                skip_n=skip_n,
                skip_stops=skip_stops,
                min_count=min_count,
                calculate_rscu=rscu,
                top_n=top
            )
            
            return jsonify({
                'status': 'success',
                'result': result,
                'timestamp': datetime.now().isoformat()
            })
        finally:
            # Always stop Spark session to release resources
            analyzer.stop()  skip_stops=skip_stops,
            min_count=min_count,
            calculate_rscu=rscu,
            top_n=top
        )
        
        return jsonify({
            'status': 'success',
            'result': result,
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Codon analysis failed: {e}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500


@app.route('/api/datasets', methods=['GET'])
def api_list_datasets():
    """List available Parquet datasets."""
    try:
        parquet_dir = Path('/data/parquet')
        datasets = []
        
        if parquet_dir.exists():
            for subdir in parquet_dir.iterdir():
                if subdir.is_dir():
                    shards = list(subdir.glob('*.parquet'))
                    if shards:
                        datasets.append({
                            'name': subdir.name,
                            'path': str(subdir),
                            'shards': len(shards),
                            'size_mb': sum(s.stat().st_size for s in shards) / (1024**2)
                        })
        
        return jsonify({
            'status': 'success',
            'datasets': datasets
        })
        
    except Exception as e:
        logger.error(f"Failed to list datasets: {e}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500


@app.route('/api/results', methods=['GET'])
def api_list_results():
    """List available analysis results."""
    try:
        results_dir = Path('/results')
        results = []
        
        if results_dir.exists():
            for item in results_dir.iterdir():
                if item.is_file() and item.suffix in ['.parquet', '.csv', '.json']:
                    results.append({
                        'name': item.name,
                        'path': str(item),
                        'size_mb': item.stat().st_size / (1024**2),
                        'modified': datetime.fromtimestamp(item.stat().st_mtime).isoformat()
                    })
        
        return jsonify({
            'status': 'success',
            'results': results
        })
        
    except Exception as e:
        logger.error(f"Failed to list results: {e}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500


@app.route('/api/health', methods=['GET'])
def api_health():
    """Health check endpoint."""
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now().isoformat()
    })


if __name__ == '__main__':
    # Run Flask development server
    app.run(host='0.0.0.0', port=5000, debug=os.getenv('FLASK_DEBUG', 'false').lower() == 'true')
