from flask import Flask, render_template, request, jsonify, send_file, flash, redirect, url_for
import os
import json
import pandas as pd
import tempfile
import uuid
from pathlib import Path
import logging
import subprocess
from werkzeug.utils import secure_filename
import argparse
import sys

# Initialize Flask app
app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'fuel-blending-app-secret-key')

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(os.path.join('logs', 'webapp.log')),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('fuel-blending-webapp')

# Configuration settings
UPLOAD_FOLDER = os.path.join(os.getcwd(), 'uploads')
OUTPUT_FOLDER = os.path.join(os.getcwd(), 'output')
ALLOWED_EXTENSIONS = {'xlsx', 'xls', 'csv', 'json', 'yaml', 'yml'}

# Ensure directories exist
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['OUTPUT_FOLDER'] = OUTPUT_FOLDER

def run_cli_optimize_directly():
    """Constructs and runs the fuel-blending CLI optimize command directly."""
    logger.info("Attempting to run fuel-blending CLI directly via app.py launcher.")

    # Define paths to example files (relative to workspace root)
    # Ensure these are the correct paths you intend to use for the example run
    base_path = Path.cwd() # Assumes app.py is at the workspace root
    
    # Corrected paths to be relative to the project root where app.py is
    # The fuel-blending CLI will be run from this directory (app.py's location)
    # So, paths for the CLI should be relative from here.
    components_file = str(base_path / "home" / "ubuntu" / "fuel_blending" / "data_examples" / "components_example_raw.xlsx")
    grades_file = str(base_path / "home" / "ubuntu" / "fuel_blending" / "data_examples" / "grades_example.xlsx")
    additives_file = str(base_path / "home" / "ubuntu" / "fuel_blending" / "data_examples" / "additives_example.yaml")
    cli_output_path = str(base_path / "output" / "app_launched_cli_run")

    os.makedirs(cli_output_path, exist_ok=True)

    cmd = [
        'fuel-blending',
        'optimize',
        components_file,
        '--grades-file', grades_file,
        '--additives', additives_file,
        '--output-path', cli_output_path,
        '--output-format', 'json',
        '--solver', 'slsqp',
        '--flat-price', '700.0',
        '--rvp-exp', '1.25',
        '--include-shadow-prices',
        '--include-neutral-prices'
    ]

    logger.info(f"Launcher: Executing command: {' '.join(cmd)}")
    try:
        # Capture stdout and stderr
        result = subprocess.run(cmd, check=False, capture_output=True, text=True)
        
        logger.info("Launcher: --- fuel-blending CLI STDOUT ---")
        if result.stdout:
            for line in result.stdout.splitlines(): # Split to log each line
                logger.info(line)
        logger.info("Launcher: --- END fuel-blending CLI STDOUT ---")

        if result.returncode != 0:
            logger.error(f"Launcher: fuel-blending CLI exited with error code {result.returncode}.")
            logger.error("Launcher: --- fuel-blending CLI STDERR ---")
            if result.stderr:
                for line in result.stderr.splitlines(): # Split to log each line
                    logger.error(line) # Log stderr as error
            logger.error("Launcher: --- END fuel-blending CLI STDERR ---")
            # Optionally re-raise or handle error
        else:
            logger.info("Launcher: fuel-blending CLI completed successfully.")

    except FileNotFoundError:
        logger.error("Launcher: The 'fuel-blending' command was not found. Is the package installed and in PATH?")
    except Exception as e:
        logger.error(f"Launcher: An unexpected error occurred while trying to run the CLI: {e}", exc_info=True)
    
    sys.exit(0) # Exit after attempting the CLI run


def allowed_file(filename):
    """Check if a file has an allowed extension"""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


@app.route('/')
def index():
    """Render the main page of the application"""
    return render_template('index.html')


@app.route('/optimize', methods=['GET', 'POST'])
def optimize():
    """Handle the optimization page and optimization requests"""
    if request.method == 'POST':
        # Check if files were uploaded
        if 'components_file' not in request.files or 'grades_file' not in request.files:
            flash('Components file and grades file are required')
            return redirect(request.url)
        
        components_file = request.files['components_file']
        grades_file = request.files['grades_file']
        additives_file = request.files.get('additives_file', None)
        
        # Check if the user did not select files
        if components_file.filename == '' or grades_file.filename == '':
            flash('Components file and grades file are required')
            return redirect(request.url)
        
        # Create a session ID for this optimization run
        session_id = str(uuid.uuid4())
        session_folder = os.path.join(app.config['UPLOAD_FOLDER'], session_id)
        os.makedirs(session_folder, exist_ok=True)
        
        # Save the uploaded files
        components_path = None
        grades_path = None
        additives_path = None
        
        if components_file and allowed_file(components_file.filename):
            components_filename = secure_filename(components_file.filename)
            components_path = os.path.join(session_folder, components_filename)
            components_file.save(components_path)
        
        if grades_file and allowed_file(grades_file.filename):
            grades_filename = secure_filename(grades_file.filename)
            grades_path = os.path.join(session_folder, grades_filename)
            grades_file.save(grades_path)
        
        if additives_file and additives_file.filename != '' and allowed_file(additives_file.filename):
            additives_filename = secure_filename(additives_file.filename)
            additives_path = os.path.join(session_folder, additives_filename)
            additives_file.save(additives_path)
        
        # Get the optimization parameters from the form
        grades_to_optimize = request.form.get('grades_to_optimize', '')
        flat_price = request.form.get('flat_price', '700.0')
        rvp_exp = request.form.get('rvp_exp', '1.25')
        solver = request.form.get('solver', 'trust-constr')
        output_format = request.form.get('output_format', 'json')
        include_shadow_prices = 'include_shadow_prices' in request.form
        include_neutral_prices = 'include_neutral_prices' in request.form
        
        # Construct the output path
        output_path = os.path.join(app.config['OUTPUT_FOLDER'], session_id)
        os.makedirs(output_path, exist_ok=True)
        
        # Build the command for the fuel-blending CLI
        cmd = [
            'fuel-blending',
            'optimize',
            components_path,
        ]
        # Add grades to optimize as positional arguments if provided
        if grades_to_optimize:
            cmd.extend(grades_to_optimize.split())
        cmd.extend([
            '--grades-file', grades_path,
            '--output-path', os.path.join(output_path, 'optimization'),
            '--output-format', output_format,
            '--flat-price', flat_price,
            '--rvp-exp', rvp_exp,
            '--solver', solver
        ])
        
        # Add optional arguments
        if additives_path:
            cmd.extend(['--additives', additives_path])
        
        if include_shadow_prices:
            cmd.append('--include-shadow-prices')
        
        if include_neutral_prices:
            cmd.append('--include-neutral-prices')
        
        try:
            # Run the optimization command
            logger.info(f"Running command: {' '.join(cmd)}")
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            logger.info(f"Command output: {result.stdout}")
            
            # Read the results
            result_file = os.path.join(output_path, 'optimization', f'optimization_results.{output_format}')
            
            if not os.path.exists(result_file):
                # Log CLI output and error
                logger.error(f"Result file not found: {result_file}")
                logger.error(f"CLI stdout: {result.stdout}")
                logger.error(f"CLI stderr: {result.stderr}")
                # List output directory contents for debugging
                output_dir = os.path.join(output_path, 'optimization')
                if os.path.exists(output_dir):
                    logger.error(f"Files in output directory: {os.listdir(output_dir)}")
                else:
                    logger.error(f"Output directory does not exist: {output_dir}")
                flash(f'Optimization failed: result file not found. Please check your input files and parameters. See logs for details.')
                return redirect(request.url)
            
            if output_format == 'json':
                with open(result_file, 'r') as f:
                    results = json.load(f)
            else:  # csv
                results = pd.read_csv(result_file).to_dict(orient='records')
            
            # Read shadow prices if included
            shadow_prices_file = os.path.join(output_path, 'optimization', 'shadow_prices.json')
            shadow_prices = None
            if os.path.exists(shadow_prices_file):
                with open(shadow_prices_file, 'r') as f:
                    shadow_prices = json.load(f)
            
            # Read neutral prices if included
            neutral_prices_file = os.path.join(output_path, 'optimization', 'neutral_prices.json')
            neutral_prices = None
            if os.path.exists(neutral_prices_file):
                with open(neutral_prices_file, 'r') as f:
                    neutral_prices = json.load(f)
            
            return render_template(
                'optimization_results.html',
                results=results,
                shadow_prices=shadow_prices,
                neutral_prices=neutral_prices,
                session_id=session_id,
                output_format=output_format
            )
            
        except subprocess.CalledProcessError as e:
            logger.error(f"Command failed: {e.stderr}")
            flash(f'Optimization failed: {e.stderr}')
            return redirect(request.url)
        
    return render_template('optimize.html')


@app.route('/eval-candidate', methods=['GET', 'POST'])
def eval_candidate():
    """Handle the candidate evaluation page and evaluation requests"""
    if request.method == 'POST':
        # Check if files were uploaded
        if ('candidates_file' not in request.files or 
            'grades_file' not in request.files or 
            'results_file' not in request.files or 
            'components_np_file' not in request.files):
            flash('All required files must be uploaded')
            return redirect(request.url)
        
        candidates_file = request.files['candidates_file']
        grades_file = request.files['grades_file']
        results_file = request.files['results_file']
        components_np_file = request.files['components_np_file']
        additives_file = request.files.get('additives_file', None)
        
        # Check if the user did not select files
        if (candidates_file.filename == '' or 
            grades_file.filename == '' or 
            results_file.filename == '' or 
            components_np_file.filename == ''):
            flash('All required files must be uploaded')
            return redirect(request.url)
        
        # Create a session ID for this evaluation run
        session_id = str(uuid.uuid4())
        session_folder = os.path.join(app.config['UPLOAD_FOLDER'], session_id)
        os.makedirs(session_folder, exist_ok=True)
        
        # Save the uploaded files
        candidates_path = None
        grades_path = None
        results_path = None
        components_np_path = None
        additives_path = None
        
        if candidates_file and allowed_file(candidates_file.filename):
            candidates_filename = secure_filename(candidates_file.filename)
            candidates_path = os.path.join(session_folder, candidates_filename)
            candidates_file.save(candidates_path)
        
        if grades_file and allowed_file(grades_file.filename):
            grades_filename = secure_filename(grades_file.filename)
            grades_path = os.path.join(session_folder, grades_filename)
            grades_file.save(grades_path)
        
        if results_file and allowed_file(results_file.filename):
            results_filename = secure_filename(results_file.filename)
            results_path = os.path.join(session_folder, results_filename)
            results_file.save(results_path)
        
        if components_np_file and allowed_file(components_np_file.filename):
            components_np_filename = secure_filename(components_np_file.filename)
            components_np_path = os.path.join(session_folder, components_np_filename)
            components_np_file.save(components_np_path)
        
        if additives_file and additives_file.filename != '' and allowed_file(additives_file.filename):
            additives_filename = secure_filename(additives_file.filename)
            additives_path = os.path.join(session_folder, additives_filename)
            additives_file.save(additives_path)
        
        # Get the evaluation parameters from the form
        flat_price = request.form.get('flat_price', '700.0')
        output_format = request.form.get('format', 'json')
        
        # Construct the output path
        output_path = os.path.join(app.config['OUTPUT_FOLDER'], session_id)
        os.makedirs(output_path, exist_ok=True)
        
        # Build the command for the fuel-blending CLI
        cmd = [
            'fuel-blending',
            'eval-candidate',
            candidates_path,
            grades_path,
            results_path,
            components_np_path,
            '--output', os.path.join(output_path, 'evaluation'),
            '--format', output_format,
            '--flat-price', flat_price
        ]
        
        # Add optional arguments
        if additives_path:
            cmd.extend(['--additives', additives_path])
        
        try:
            # Run the evaluation command
            logger.info(f"Running command: {' '.join(cmd)}")
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            logger.info(f"Command output: {result.stdout}")
            
            # Define the specific output directory used by the CLI
            cli_output_dir = os.path.join(app.config['OUTPUT_FOLDER'], session_id, 'evaluation')

            # Read the results
            # Adjusted filename based on typical CLI output patterns (e.g. optimize command)
            evaluation_file = os.path.join(cli_output_dir, f'candidate_evaluation.{output_format}')
            
            if not os.path.exists(evaluation_file):
                logger.error(f"Evaluation result file not found: {evaluation_file}")
                logger.error(f"CLI stdout: {result.stdout}")
                logger.error(f"CLI stderr: {result.stderr}")
                if os.path.exists(cli_output_dir):
                    logger.error(f"Files in output directory '{cli_output_dir}': {os.listdir(cli_output_dir)}")
                else:
                    logger.error(f"Output directory does not exist: {cli_output_dir}")
                flash(f'Evaluation failed: result file not found. Please check logs.')
                return redirect(request.url)

            if output_format == 'json':
                with open(evaluation_file, 'r') as f:
                    evaluations = json.load(f)
            else:  # csv
                evaluations = pd.read_csv(evaluation_file).to_dict(orient='records')
            
            # Read neutral prices
            # Adjusted filename
            neutral_prices_file = os.path.join(cli_output_dir, 'neutral_prices.csv')
            neutral_prices = None
            if os.path.exists(neutral_prices_file):
                neutral_prices = pd.read_csv(neutral_prices_file).to_dict(orient='records')
            else:
                logger.warning(f"Neutral prices file not found: {neutral_prices_file}")

            return render_template(
                'evaluation_results.html',
                evaluations=evaluations,
                neutral_prices=neutral_prices,
                session_id=session_id,
                output_format=output_format
            )
            
        except subprocess.CalledProcessError as e:
            logger.error(f"Command failed: {e.stderr}")
            flash(f'Evaluation failed: {e.stderr}')
            return redirect(request.url)
        
    return render_template('eval_candidate.html')


@app.route('/download/<path:filename>')
def download_file(filename):
    """Download a result file"""
    return send_file(os.path.join(app.config['OUTPUT_FOLDER'], filename), as_attachment=True)


@app.route('/about')
def about():
    """Render the about page"""
    return render_template('about.html')


@app.route('/help')
def help_page():
    """Render the help page"""
    return render_template('help.html')


@app.route('/api/optimize', methods=['POST'])
def api_optimize():
    """API endpoint for optimization"""
    try:
        # Create a temporary directory for this request
        temp_dir = tempfile.mkdtemp(prefix='fuel_blending_api_')
        files_dir = os.path.join(temp_dir, 'files')
        os.makedirs(files_dir, exist_ok=True)
        output_dir = os.path.join(temp_dir, 'output')
        os.makedirs(output_dir, exist_ok=True)
        
        # Process uploaded files
        components_path = None
        grades_path = None
        additives_path = None
        
        # Get file data from request
        if 'components_file' in request.files:
            components_file = request.files['components_file']
            if components_file.filename != '':
                components_path = os.path.join(files_dir, secure_filename(components_file.filename))
                components_file.save(components_path)
        
        if 'grades_file' in request.files:
            grades_file = request.files['grades_file']
            if grades_file.filename != '':
                grades_path = os.path.join(files_dir, secure_filename(grades_file.filename))
                grades_file.save(grades_path)
        
        if 'additives_file' in request.files:
            additives_file = request.files['additives_file']
            if additives_file.filename != '':
                additives_path = os.path.join(files_dir, secure_filename(additives_file.filename))
                additives_file.save(additives_path)
        
        # Check required files
        if not components_path or not grades_path:
            return jsonify({'error': 'Components and grades files are required'}), 400
        
        # Get parameters from form data
        grades_to_optimize = request.form.get('grades_to_optimize', '').split()
        flat_price = request.form.get('flat_price', '700.0')
        rvp_exp = request.form.get('rvp_exp', '1.25')
        solver = request.form.get('solver', 'trust-constr')
        output_format = request.form.get('output_format', 'json')
        include_shadow_prices = request.form.get('include_shadow_prices') == 'true'
        include_neutral_prices = request.form.get('include_neutral_prices') == 'true'
        
        # Build command
        cmd = [
            'fuel-blending',
            'optimize',
            components_path,
        ]
        # Add grades to optimize as positional arguments if provided
        if grades_to_optimize:
            cmd.extend(grades_to_optimize)
        cmd.extend([
            '--grades-file', grades_path,
            '--output-path', os.path.join(output_dir, 'optimization'),
            '--output-format', output_format,
            '--flat-price', flat_price,
            '--rvp-exp', rvp_exp,
            '--solver', solver
        ])
        
        # Add optional arguments
        if additives_path:
            cmd.extend(['--additives', additives_path])
        
        if include_shadow_prices:
            cmd.append('--include-shadow-prices')
        
        if include_neutral_prices:
            cmd.append('--include-neutral-prices')
        
        # Run command
        logger.info(f"API running command: {' '.join(cmd)}")
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode != 0:
            return jsonify({
                'error': 'Optimization failed',
                'message': result.stderr
            }), 500
        
        # Collect results
        response_data = {
            'status': 'success',
            'command_output': result.stdout,
            'results': None,
            'shadow_prices': None,
            'neutral_prices': None
        }
        
        # Read result files
        result_file = os.path.join(output_dir, f'optimization_optimization_results.{output_format}')
        if os.path.exists(result_file):
            if output_format == 'json':
                with open(result_file, 'r') as f:
                    response_data['results'] = json.load(f)
            else:  # csv
                response_data['results'] = pd.read_csv(result_file).to_dict(orient='records')
        
        shadow_prices_file = os.path.join(output_dir, 'optimization_shadow_prices.json')
        if os.path.exists(shadow_prices_file):
            with open(shadow_prices_file, 'r') as f:
                response_data['shadow_prices'] = json.load(f)
        
        neutral_prices_file = os.path.join(output_dir, 'optimization_neutral_prices.json')
        if os.path.exists(neutral_prices_file):
            with open(neutral_prices_file, 'r') as f:
                response_data['neutral_prices'] = json.load(f)
        
        return jsonify(response_data)
        
    except Exception as e:
        logger.exception("API error")
        return jsonify({'error': str(e)}), 500


@app.route('/api/eval-candidate', methods=['POST'])
def api_eval_candidate():
    """API endpoint for candidate evaluation"""
    try:
        # Create a temporary directory for this request
        temp_dir = tempfile.mkdtemp(prefix='fuel_blending_api_')
        files_dir = os.path.join(temp_dir, 'files')
        os.makedirs(files_dir, exist_ok=True)
        output_dir = os.path.join(temp_dir, 'output')
        os.makedirs(output_dir, exist_ok=True)
        
        # Process uploaded files
        candidates_path = None
        grades_path = None
        results_path = None
        components_np_path = None
        additives_path = None
        
        # Get file data from request
        if 'candidates_file' in request.files:
            candidates_file = request.files['candidates_file']
            if candidates_file.filename != '':
                candidates_path = os.path.join(files_dir, secure_filename(candidates_file.filename))
                candidates_file.save(candidates_path)
        
        if 'grades_file' in request.files:
            grades_file = request.files['grades_file']
            if grades_file.filename != '':
                grades_path = os.path.join(files_dir, secure_filename(grades_file.filename))
                grades_file.save(grades_path)
        
        if 'results_file' in request.files:
            results_file = request.files['results_file']
            if results_file.filename != '':
                results_path = os.path.join(files_dir, secure_filename(results_file.filename))
                results_file.save(results_path)
        
        if 'components_np_file' in request.files:
            components_np_file = request.files['components_np_file']
            if components_np_file.filename != '':
                components_np_path = os.path.join(files_dir, secure_filename(components_np_file.filename))
                components_np_file.save(components_np_path)
        
        if 'additives_file' in request.files:
            additives_file = request.files['additives_file']
            if additives_file.filename != '':
                additives_path = os.path.join(files_dir, secure_filename(additives_file.filename))
                additives_file.save(additives_path)
        
        # Check required files
        if not all([candidates_path, grades_path, results_path, components_np_path]):
            return jsonify({'error': 'All required files must be provided'}), 400
        
        # Get parameters from form data
        flat_price = request.form.get('flat_price', '700.0')
        output_format = request.form.get('format', 'json')
        
        # Build command
        cmd = [
            'fuel-blending',
            'eval-candidate',
            candidates_path,
            grades_path,
            results_path,
            components_np_path,
            '--output', os.path.join(output_dir, 'evaluation'),
            '--format', output_format,
            '--flat-price', flat_price
        ]
        
        # Add optional arguments
        if additives_path:
            cmd.extend(['--additives', additives_path])
        
        # Run command
        logger.info(f"API running command: {' '.join(cmd)}")
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode != 0:
            return jsonify({
                'error': 'Evaluation failed',
                'message': result.stderr
            }), 500
        
        # Define the specific output directory used by the CLI
        cli_output_dir = os.path.join(output_dir, 'evaluation')

        # Collect results
        response_data = {
            'status': 'success',
            'command_output': result.stdout,
            'evaluations': None,
            'neutral_prices': None
        }
        
        # Read result files
        # Adjusted filename
        evaluation_file = os.path.join(cli_output_dir, f'candidate_evaluation.{output_format}')
        if os.path.exists(evaluation_file):
            if output_format == 'json':
                with open(evaluation_file, 'r') as f:
                    response_data['evaluations'] = json.load(f)
            else:  # csv
                response_data['evaluations'] = pd.read_csv(evaluation_file).to_dict(orient='records')
        else:
            logger.warning(f"API: Evaluation result file not found: {evaluation_file}")
            if os.path.exists(cli_output_dir):
                logger.warning(f"API: Files in output directory '{cli_output_dir}': {os.listdir(cli_output_dir)}")

        # Adjusted filename
        neutral_prices_file = os.path.join(cli_output_dir, 'neutral_prices.csv')
        if os.path.exists(neutral_prices_file):
            response_data['neutral_prices'] = pd.read_csv(neutral_prices_file).to_dict(orient='records')
        else:
            logger.warning(f"API: Neutral prices file not found: {neutral_prices_file}")
            
        return jsonify(response_data)
        
    except Exception as e:
        logger.exception("API error")
        return jsonify({'error': str(e)}), 500


if __name__ == '__main__':
    # Add argument parsing for CLI mode
    cli_parser = argparse.ArgumentParser(description='Flask App or CLI Launcher')
    cli_parser.add_argument('--run-cli-optimize', action='store_true', help='Run the fuel-blending CLI directly and exit.')
    
    # Parse only known args at this stage to not interfere with Flask's args
    app_args, unknown_args = cli_parser.parse_known_args()

    if app_args.run_cli_optimize:
        run_cli_optimize_directly()
    else:
        # Default Flask app execution
        # Pass unknown_args to Flask if necessary, though usually Flask doesn't use them here
        # For development server, Flask picks up its own args like --host, --port from sys.argv
        # We need to ensure sys.argv is appropriately set for Flask if we've modified it.
        # Since parse_known_args doesn't modify sys.argv, Flask should be fine.
        
        # Make sure UPLOAD_FOLDER and OUTPUT_FOLDER are created before app.run
        # This was already done globally, so it's fine.

        logger.info("Starting Flask development server.")
        app.run(debug=True, host='0.0.0.0', port=5000) 