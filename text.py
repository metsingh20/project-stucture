
"""
Smart ZIP Project File Concatenator - Web Server
Extracts only important source code files, skipping dependencies and build artifacts.
"""

from flask import Flask, request, send_file, render_template_string, jsonify
import zipfile
import os
import tempfile
import shutil
from io import BytesIO
import time
import threading

app = Flask(__name__)

# Store processing status and cancellation flags
processing_status = {}
cancellation_flags = {}

# HTML template for the upload page
HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>Smart ZIP File Processor</title>
    <style>
        body {
            font-family: Arial, sans-serif;
            max-width: 800px;
            margin: 50px auto;
            padding: 20px;
            background: #f5f5f5;
        }
        .upload-box {
            border: 2px dashed #ccc;
            padding: 40px;
            text-align: center;
            border-radius: 10px;
            background: white;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }
        h1 {
            color: #333;
            text-align: center;
        }
        .subtitle {
            text-align: center;
            color: #666;
            margin-bottom: 30px;
        }
        button {
            background-color: #4CAF50;
            color: white;
            padding: 12px 24px;
            border: none;
            border-radius: 4px;
            cursor: pointer;
            font-size: 16px;
            margin-top: 10px;
        }
        button:hover {
            background-color: #45a049;
        }
        button:disabled {
            background-color: #ccc;
            cursor: not-allowed;
        }
        .cancel-btn {
            background-color: #f44336;
            margin-left: 10px;
        }
        .cancel-btn:hover {
            background-color: #da190b;
        }
        input[type="file"] {
            margin: 20px 0;
            padding: 10px;
            border: 1px solid #ddd;
            border-radius: 4px;
            width: 100%;
            max-width: 400px;
        }
        .options-container {
            margin: 20px 0;
            text-align: left;
            display: inline-block;
            background: #f9f9f9;
            padding: 15px 20px;
            border-radius: 8px;
            border: 1px solid #e0e0e0;
        }
        .options-container label {
            display: block;
            margin: 10px 0;
            cursor: pointer;
        }
        .options-container input[type="checkbox"] {
            margin-right: 8px;
        }
        .info-box {
            background: #e3f2fd;
            border-left: 4px solid #2196F3;
            padding: 15px;
            margin: 20px 0;
            border-radius: 4px;
            text-align: left;
        }
        .info-box h4 {
            margin-top: 0;
            color: #1976D2;
        }
        .info-box ul {
            margin: 10px 0;
            padding-left: 20px;
        }
        .info-box li {
            margin: 5px 0;
            color: #555;
        }
        .skip-info {
            background: #fff3e0;
            border-left: 4px solid #ff9800;
            padding: 15px;
            margin: 20px 0;
            border-radius: 4px;
            text-align: left;
        }
        .skip-info h4 {
            margin-top: 0;
            color: #f57c00;
        }
        .progress-container {
            display: none;
            margin-top: 20px;
        }
        .progress-bar {
            width: 100%;
            height: 30px;
            background-color: #f0f0f0;
            border-radius: 15px;
            overflow: hidden;
        }
        .progress-fill {
            height: 100%;
            background-color: #4CAF50;
            width: 0%;
            transition: width 0.3s;
            display: flex;
            align-items: center;
            justify-content: center;
            color: white;
            font-weight: bold;
        }
        .status-text {
            margin-top: 10px;
            color: #666;
        }
        .timer {
            font-size: 14px;
            color: #888;
            margin-top: 5px;
        }
        .button-container {
            margin-top: 10px;
        }
        .stats {
            background: #f5f5f5;
            padding: 10px;
            border-radius: 4px;
            margin-top: 10px;
            font-size: 14px;
            color: #666;
        }
    </style>
</head>
<body>
    <h1>🚀 Smart ZIP File Processor</h1>
    <p class="subtitle">Extracts only source code files, skipping dependencies and build artifacts</p>
    
    <div class="info-box">
        <h4>✅ What Gets Included:</h4>
        <ul>
            <li>Source code files (.tsx, .ts, .jsx, .js, .py, .java, .cpp, etc.)</li>
            <li>Stylesheets (.css, .scss, .sass, .less)</li>
            <li>Config files (package.json, tsconfig.json, vite.config.ts, etc.)</li>
            <li>HTML templates and markdown files</li>
            <li>Environment files (.env.example)</li>
        </ul>
    </div>
    
    <div class="skip-info">
        <h4>🚫 What Gets Skipped:</h4>
        <ul>
            <li>node_modules, vendor, dependencies folders</li>
            <li>Build artifacts (dist, build, .next, out)</li>
            <li>Cache and temp files (.cache, .vite, __pycache__)</li>
            <li>Git files (.git folder)</li>
            <li>Binary files (images, videos, compiled files)</li>
            <li>Map files (.js.map, .css.map)</li>
            <li>Lock files (package-lock.json, yarn.lock, bun.lockb)</li>
        </ul>
    </div>
    
    <div class="upload-box">
        <h3>Upload Your Project ZIP</h3>
        <form id="uploadForm" method="POST" enctype="multipart/form-data">
            <input type="file" name="zipfile" id="zipfile" accept=".zip" required>
            <br>
            <div class="options-container">
                <strong>Output Options:</strong>
                <label>
                    <input type="checkbox" name="include_structure" id="include_structure" checked>
                    📁 Include folder structure diagram
                </label>
                <label>
                    <input type="checkbox" name="include_code" id="include_code" checked>
                    📄 Include file contents with line numbers
                </label>
                <label>
                    <input type="checkbox" name="include_stats" id="include_stats" checked>
                    📊 Include processing statistics
                </label>
            </div>
            <br>
            <div class="button-container">
                <button type="submit" id="submitBtn">Process & Download</button>
                <button type="button" class="cancel-btn" id="cancelBtn" style="display:none;">Cancel</button>
            </div>
        </form>
        
        <div class="progress-container" id="progressContainer">
            <div class="progress-bar">
                <div class="progress-fill" id="progressFill">0%</div>
            </div>
            <div class="status-text" id="statusText">Counting files...</div>
            <div class="timer" id="timer">Time elapsed: 0s</div>
            <div class="stats" id="stats" style="display:none;"></div>
        </div>
    </div>
    <p style="text-align: center;"><small>Output will be named based on your ZIP filename</small></p>

    <script>
        let startTime;
        let timerInterval;
        let statusInterval;
        let currentJobId = null;
        let isCancelled = false;
        
        document.getElementById('cancelBtn').onclick = async function() {
            if (currentJobId && !isCancelled) {
                isCancelled = true;
                
                // Send cancellation request
                await fetch(`/cancel/${currentJobId}`, {method: 'POST'});
                
                // Update UI
                document.getElementById('statusText').textContent = '✗ Cancelled by user';
                document.getElementById('progressFill').style.backgroundColor = '#f44336';
                
                // Clean up
                clearInterval(timerInterval);
                clearInterval(statusInterval);
                
                // Reset after 2 seconds
                setTimeout(() => {
                    resetUI();
                }, 2000);
            }
        };
        
        function resetUI() {
            document.getElementById('progressContainer').style.display = 'none';
            document.getElementById('progressFill').style.width = '0%';
            document.getElementById('progressFill').style.backgroundColor = '#4CAF50';
            document.getElementById('submitBtn').disabled = false;
            document.getElementById('cancelBtn').style.display = 'none';
            document.getElementById('statusText').textContent = 'Counting files...';
            document.getElementById('stats').style.display = 'none';
            currentJobId = null;
            isCancelled = false;
        }
        
        document.getElementById('uploadForm').onsubmit = async function(e) {
            e.preventDefault();
            
            const formData = new FormData(this);
            const submitBtn = document.getElementById('submitBtn');
            const cancelBtn = document.getElementById('cancelBtn');
            const progressContainer = document.getElementById('progressContainer');
            const progressFill = document.getElementById('progressFill');
            const statusText = document.getElementById('statusText');
            const timerDiv = document.getElementById('timer');
            const statsDiv = document.getElementById('stats');
            
            // Check if at least one option is selected
            const includeStructure = document.getElementById('include_structure').checked;
            const includeCode = document.getElementById('include_code').checked;
            
            if (!includeStructure && !includeCode) {
                alert('Please select at least one option (Folder structure or File contents)');
                return;
            }
            
            // Show progress bar and cancel button
            progressContainer.style.display = 'block';
            submitBtn.disabled = true;
            cancelBtn.style.display = 'inline-block';
            isCancelled = false;
            startTime = Date.now();
            
            // Start timer
            timerInterval = setInterval(() => {
                const elapsed = ((Date.now() - startTime) / 1000).toFixed(1);
                timerDiv.textContent = `Time elapsed: ${elapsed}s`;
            }, 100);
            
            // Generate unique job ID
            const jobId = Date.now() + '_' + Math.random().toString(36).substr(2, 9);
            currentJobId = jobId;
            formData.append('job_id', jobId);
            
            // Start status polling
            statusInterval = setInterval(async () => {
                if (isCancelled) {
                    clearInterval(statusInterval);
                    return;
                }
                
                try {
                    const statusResponse = await fetch(`/status/${jobId}`);
                    const status = await statusResponse.json();
                    
                    if (status.cancelled) {
                        clearInterval(statusInterval);
                        return;
                    }
                    
                    if (status.current !== undefined && status.total !== undefined) {
                        const percent = status.total > 0 ? Math.round((status.current / status.total) * 100) : 0;
                        progressFill.style.width = percent + '%';
                        progressFill.textContent = percent + '%';
                        statusText.textContent = status.message || `Processing file ${status.current} of ${status.total}`;
                        
                        // Show stats if available
                        if (status.stats) {
                            statsDiv.style.display = 'block';
                            statsDiv.innerHTML = `
                                📊 Processed: ${status.stats.processed} files | 
                                ⏭️ Skipped: ${status.stats.skipped} files
                            `;
                        }
                    }
                } catch (err) {
                    console.log('Status check error:', err);
                }
            }, 200);
            
            try {
                const response = await fetch('/process', {
                    method: 'POST',
                    body: formData
                });
                
                clearInterval(timerInterval);
                clearInterval(statusInterval);
                
                if (isCancelled) {
                    return;
                }
                
                if (response.ok) {
                    progressFill.style.width = '100%';
                    progressFill.textContent = '100%';
                    
                    const elapsed = ((Date.now() - startTime) / 1000).toFixed(1);
                    statusText.textContent = `✓ Complete in ${elapsed}s`;
                    timerDiv.textContent = `Total time: ${elapsed}s`;
                    
                    // Get filename from response header
                    const contentDisposition = response.headers.get('Content-Disposition');
                    let filename = 'output.txt';
                    if (contentDisposition) {
                        const filenameMatch = contentDisposition.match(/filename="?(.+)"?/);
                        if (filenameMatch) {
                            filename = filenameMatch[1];
                        }
                    }
                    
                    // Download file
                    const blob = await response.blob();
                    const url = window.URL.createObjectURL(blob);
                    const a = document.createElement('a');
                    a.href = url;
                    a.download = filename;
                    a.click();
                    
                    // Clean up status
                    fetch(`/cleanup/${jobId}`, {method: 'POST'});
                    
                    // Reset after 3 seconds
                    setTimeout(() => {
                        resetUI();
                    }, 3000);
                } else if (response.status === 499) {
                    // Cancelled
                    statusText.textContent = '✗ Processing cancelled';
                    setTimeout(() => {
                        resetUI();
                    }, 2000);
                } else {
                    const errorText = await response.text();
                    statusText.textContent = '✗ Error: ' + errorText;
                    submitBtn.disabled = false;
                    cancelBtn.style.display = 'none';
                }
            } catch (error) {
                if (!isCancelled) {
                    clearInterval(timerInterval);
                    clearInterval(statusInterval);
                    statusText.textContent = '✗ Error: ' + error.message;
                    submitBtn.disabled = false;
                    cancelBtn.style.display = 'none';
                }
            }
        };
    </script>
</body>
</html>
"""

# Set terminal width for separator lines
TERMINAL_WIDTH = 80

# ============================================================================
# SMART FILTERING CONFIGURATION
# ============================================================================

# Folders to completely skip (never enter these directories)
SKIP_FOLDERS = {
    'node_modules',
    'vendor',
    'venv',
    'env',
    '.env',
    'virtualenv',
    '__pycache__',
    '.pytest_cache',
    '.mypy_cache',
    '.git',
    '.svn',
    '.hg',
    'dist',
    'build',
    'out',
    '.next',
    '.nuxt',
    'coverage',
    '.nyc_output',
    '.cache',
    '.vite',
    '.turbo',
    '.parcel-cache',
    'tmp',
    'temp',
    '.temp',
    '.tmp',
    'logs',
    'target',  # Rust, Java
    'bin',
    'obj',
    '.gradle',
    '.idea',
    '.vscode',
    '.vs',
    'bower_components',
}

# File extensions that are source code (always include)
SOURCE_CODE_EXTENSIONS = {
    # Web/JavaScript/TypeScript
    '.js', '.jsx', '.ts', '.tsx', '.mjs', '.cjs',
    '.vue', '.svelte',
    
    # Python
    '.py', '.pyw', '.pyx',
    
    # Java/Kotlin/Scala
    '.java', '.kt', '.kts', '.scala',
    
    # C/C++/C#
    '.c', '.cpp', '.cc', '.cxx', '.h', '.hpp', '.cs',
    
    # Go, Rust, Swift
    '.go', '.rs', '.swift',
    
    # Ruby, PHP
    '.rb', '.php',
    
    # Styles
    '.css', '.scss', '.sass', '.less', '.styl',
    
    # HTML/Templates
    '.html', '.htm', '.ejs', '.hbs', '.handlebars', '.mustache', '.pug', '.jade',
    
    # Config/Data
    '.json', '.yaml', '.yml', '.toml', '.xml', '.ini', '.conf', '.config',
    
    # Documentation
    '.md', '.mdx', '.txt', '.rst',
    
    # Shell scripts
    '.sh', '.bash', '.zsh', '.fish',
    
    # SQL
    '.sql',
    
    # GraphQL
    '.graphql', '.gql',
    
    # Dockerfile
    '.dockerfile',
}

# Specific filenames to always include (no extension)
IMPORTANT_FILES = {
    'Makefile',
    'Dockerfile',
    'docker-compose.yml',
    'docker-compose.yaml',
    'Procfile',
    'Rakefile',
    'Gemfile',
    'Podfile',
    'CMakeLists.txt',
    'README',
    'LICENSE',
    'CHANGELOG',
    '.gitignore',
    '.dockerignore',
    '.eslintrc',
    '.prettierrc',
    '.babelrc',
    '.env.example',
    '.env.sample',
    'requirements.txt',
    'setup.py',
    'pyproject.toml',
    'Cargo.toml',
    'go.mod',
    'go.sum',
}

# Config file patterns to include
CONFIG_PATTERNS = {
    'package.json',
    'tsconfig',
    'jsconfig',
    'webpack.config',
    'vite.config',
    'rollup.config',
    'babel.config',
    'jest.config',
    'vitest.config',
    'tailwind.config',
    'postcss.config',
    'eslint.config',
    'prettier.config',
    '.eslintrc',
    '.prettierrc',
    'next.config',
    'nuxt.config',
    'svelte.config',
    'vue.config',
    'angular.json',
}

# Patterns to skip (even if they match source extensions)
SKIP_PATTERNS = {
    '.min.js',
    '.min.css',
    '.bundle.js',
    '.chunk.js',
    '.map',
    '.lock',
    'package-lock.json',
    'yarn.lock',
    'pnpm-lock.yaml',
    'bun.lockb',
    'poetry.lock',
    'Gemfile.lock',
    'Cargo.lock',
    '.DS_Store',
    'Thumbs.db',
    '.swp',
    '.swo',
}

# Binary/media extensions to always skip
BINARY_EXTENSIONS = {
    # Images
    '.jpg', '.jpeg', '.png', '.gif', '.bmp', '.ico', '.svg', '.webp', '.tiff',
    
    # Videos
    '.mp4', '.avi', '.mov', '.wmv', '.flv', '.webm', '.mkv',
    
    # Audio
    '.mp3', '.wav', '.ogg', '.m4a', '.flac',
    
    # Fonts
    '.ttf', '.otf', '.woff', '.woff2', '.eot',
    
    # Archives
    '.zip', '.tar', '.gz', '.rar', '.7z', '.bz2',
    
    # Executables/Compiled
    '.exe', '.dll', '.so', '.dylib', '.bin', '.o', '.pyc', '.pyo',
    
    # Documents
    '.pdf', '.doc', '.docx', '.xls', '.xlsx', '.ppt', '.pptx',
    
    # Database
    '.db', '.sqlite', '.sqlite3',
}

def should_skip_folder(folder_name):
    """Check if a folder should be skipped."""
    return folder_name.lower() in SKIP_FOLDERS or folder_name.startswith('.')

def should_include_file(filename):
    """Determine if a file should be included in the output."""
    filename_lower = filename.lower()
    
    # Check if it's in skip patterns
    for pattern in SKIP_PATTERNS:
        if pattern in filename_lower:
            return False
    
    # Check if it's a binary file
    _, ext = os.path.splitext(filename_lower)
    if ext in BINARY_EXTENSIONS:
        return False
    
    # Check if it's an important file (exact match)
    if filename in IMPORTANT_FILES:
        return True
    
    # Check config patterns
    for pattern in CONFIG_PATTERNS:
        if pattern in filename_lower:
            return True
    
    # Check if it has a source code extension
    if ext in SOURCE_CODE_EXTENSIONS:
        return True
    
    return False

def is_text_file(filepath):
    """Check if a file is text-based (not binary)."""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            f.read(8192)  # Try to read as text
        return True
    except (UnicodeDecodeError, PermissionError):
        return False

def generate_separator(text):
    """Generate separator line that spans full width with text in center."""
    text_with_spaces = f" {text} "
    text_length = len(text_with_spaces)
    
    if text_length >= TERMINAL_WIDTH:
        return f"={'=' * TERMINAL_WIDTH}\n"
    
    remaining = TERMINAL_WIDTH - text_length
    left_padding = remaining // 2
    right_padding = remaining - left_padding
    
    return f"{'=' * left_padding}{text_with_spaces}{'=' * right_padding}\n"

def generate_tree_structure(temp_dir, stats=None):
    """Generate folder structure using ASCII tree (only showing included files)."""
    lines = []
    lines.append(generate_separator("FOLDER STRUCTURE"))
    
    def add_tree(directory, prefix=""):
        """Recursively build tree structure."""
        try:
            entries = sorted(os.listdir(directory))
            
            # Filter out skipped folders
            dirs = [e for e in entries 
                   if os.path.isdir(os.path.join(directory, e)) 
                   and not should_skip_folder(e)]
            
            # Filter files to only show included ones
            files = [e for e in entries 
                    if os.path.isfile(os.path.join(directory, e)) 
                    and should_include_file(e)]
            
            all_entries = dirs + files
            
            for i, entry in enumerate(all_entries):
                path = os.path.join(directory, entry)
                is_last = (i == len(all_entries) - 1)
                
                # Choose connector
                connector = "└── " if is_last else "├── "
                
                if os.path.isdir(path):
                    lines.append(prefix + connector + entry + "/\n")
                else:
                    lines.append(prefix + connector + entry + "\n")
                
                # Recurse into directories
                if os.path.isdir(path):
                    extension = "    " if is_last else "│   "
                    add_tree(path, prefix + extension)
        except PermissionError:
            pass
    
    # Get root folder name
    root_name = os.path.basename(temp_dir)
    lines.append(root_name + "/\n")
    add_tree(temp_dir)
    lines.append("\n")
    
    return "".join(lines)

def count_processable_files(temp_dir):
    """Count total number of files that will be processed."""
    count = 0
    for root, dirs, files in os.walk(temp_dir):
        # Remove skipped folders from dirs in-place to prevent walking into them
        dirs[:] = [d for d in dirs if not should_skip_folder(d)]
        
        for filename in files:
            if should_include_file(filename):
                filepath = os.path.join(root, filename)
                if is_text_file(filepath):
                    count += 1
    return count

def is_cancelled(job_id):
    """Check if job has been cancelled."""
    return cancellation_flags.get(job_id, False)

def process_zip_to_text(zip_file, include_structure=True, include_code=True, include_stats=True, job_id=None):
    """Process ZIP file and return text output as bytes."""
    temp_dir = tempfile.mkdtemp()
    output = BytesIO()
    
    stats = {
        'processed': 0,
        'skipped': 0,
        'total_files': 0,
        'total_size': 0,
    }
    
    try:
        # Extract ZIP contents
        if job_id:
            processing_status[job_id] = {
                'current': 0, 
                'total': 0, 
                'message': 'Extracting ZIP...', 
                'cancelled': False,
                'stats': stats
            }
        
        if is_cancelled(job_id):
            processing_status[job_id]['cancelled'] = True
            return None
        
        with zipfile.ZipFile(zip_file, 'r') as zip_ref:
            zip_ref.extractall(temp_dir)
        
        # Count total files if we need to process code
        if include_code:
            if job_id:
                processing_status[job_id]['message'] = 'Analyzing project structure...'
            
            if is_cancelled(job_id):
                processing_status[job_id]['cancelled'] = True
                return None
            
            total_files = count_processable_files(temp_dir)
            
            if job_id:
                processing_status[job_id]['total'] = total_files
                processing_status[job_id]['message'] = f'Found {total_files} source files to process...'
        else:
            if job_id:
                processing_status[job_id]['total'] = 1
                processing_status[job_id]['current'] = 0
        
        # Add folder structure if requested
        if include_structure:
            if job_id:
                processing_status[job_id]['message'] = 'Generating folder structure...'
            
            if is_cancelled(job_id):
                processing_status[job_id]['cancelled'] = True
                return None
            
            tree = generate_tree_structure(temp_dir, stats)
            output.write(tree.encode('utf-8'))
            
            if not include_code and job_id:
                processing_status[job_id]['current'] = 1
        
        # Process files if requested
        if include_code:
            current_file = 0
            
            for root, dirs, files in os.walk(temp_dir):
                # Skip unwanted directories
                dirs[:] = [d for d in dirs if not should_skip_folder(d)]
                
                for filename in sorted(files):
                    # Check for cancellation
                    if is_cancelled(job_id):
                        processing_status[job_id]['cancelled'] = True
                        return None
                    
                    filepath = os.path.join(root, filename)
                    stats['total_files'] += 1
                    
                    # Check if file should be included
                    if not should_include_file(filename):
                        stats['skipped'] += 1
                        continue
                    
                    # Check if file is text-based
                    if not is_text_file(filepath):
                        stats['skipped'] += 1
                        continue
                    
                    current_file += 1
                    stats['processed'] += 1
                    
                    # Update progress
                    if job_id:
                        processing_status[job_id]['current'] = current_file
                        processing_status[job_id]['message'] = f'Processing {filename} ({current_file}/{total_files})'
                        processing_status[job_id]['stats'] = stats
                    
                    # Get relative path
                    rel_path = os.path.relpath(filepath, temp_dir)
                    
                    # Write file header with full-width separator
                    output.write(generate_separator(rel_path).encode('utf-8'))
                    
                    # Read and write file contents with line numbers
                    try:
                        file_size = os.path.getsize(filepath)
                        stats['total_size'] += file_size
                        
                        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                            for line_num, line in enumerate(f, start=1):
                                output.write(f"{line_num}: {line.rstrip()}\n".encode('utf-8'))
                    except Exception as e:
                        output.write(f"(Error reading file: {str(e)})\n".encode('utf-8'))
                    
                    output.write(b"\n")
        
        # Add statistics at the end if requested
        if include_stats:
            output.write(generate_separator("PROCESSING STATISTICS").encode('utf-8'))
            output.write(f"Total files found: {stats['total_files']}\n".encode('utf-8'))
            output.write(f"Files processed: {stats['processed']}\n".encode('utf-8'))
            output.write(f"Files skipped: {stats['skipped']}\n".encode('utf-8'))
            output.write(f"Total size: {stats['total_size']:,} bytes ({stats['total_size'] / 1024:.1f} KB)\n".encode('utf-8'))
            output.write(b"\n")
        
        output.seek(0)
        return output
    
    finally:
        # Clean up temporary directory
        shutil.rmtree(temp_dir)

@app.route('/', methods=['GET'])
def upload_page():
    return render_template_string(HTML_TEMPLATE)

@app.route('/process', methods=['POST'])
def process_file():
    # Check if file was uploaded
    if 'zipfile' not in request.files:
        return "No file uploaded", 400
    
    file = request.files['zipfile']
    job_id = request.form.get('job_id')
    
    if file.filename == '':
        return "No file selected", 400
    
    if not file.filename.endswith('.zip'):
        return "Please upload a ZIP file", 400
    
    # Check options
    include_structure = 'include_structure' in request.form
    include_code = 'include_code' in request.form
    include_stats = 'include_stats' in request.form
    
    # At least one option must be selected
    if not include_structure and not include_code:
        return "Please select at least one option", 400
    
    # Get output filename from ZIP filename
    zip_basename = os.path.splitext(file.filename)[0]
    output_filename = f"{zip_basename}_source_code.txt"
    
    # Process the ZIP file
    try:
        output = process_zip_to_text(file, include_structure, include_code, include_stats, job_id)
        
        # Check if cancelled
        if output is None:
            return "Processing cancelled", 499
        
        return send_file(
            output,
            as_attachment=True,
            download_name=output_filename,
            mimetype='text/plain'
        )
    except Exception as e:
        return f"Error processing file: {str(e)}", 500

@app.route('/status/<job_id>', methods=['GET'])
def get_status(job_id):
    """Get processing status for a job."""
    status = processing_status.get(job_id, {})
    return jsonify(status)

@app.route('/cancel/<job_id>', methods=['POST'])
def cancel_job(job_id):
    """Cancel a processing job."""
    cancellation_flags[job_id] = True
    if job_id in processing_status:
        processing_status[job_id]['cancelled'] = True
    return jsonify({'status': 'cancelled'})

@app.route('/cleanup/<job_id>', methods=['POST'])
def cleanup_status(job_id):
    """Clean up status for completed job."""
    if job_id in processing_status:
        del processing_status[job_id]
    if job_id in cancellation_flags:
        del cancellation_flags[job_id]
    return jsonify({'status': 'ok'})

if __name__ == '__main__':
    print("=" * 60)
    print("🚀 Smart ZIP Processor Server Started")
    print("=" * 60)
    print("📁 Extracts ONLY source code files")
    print("🚫 Skips node_modules, dist, build, and other junk")
    print("=" * 60)
    print("🌐 Open: http://localhost:5000")
    print("=" * 60)
    app.run(debug=True, port=5000, threaded=True)