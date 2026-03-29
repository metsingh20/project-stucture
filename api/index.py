"""
Smart ZIP Project File Concatenator - Web Server
Extracts only important source code files, skipping dependencies and build artifacts.
Adapted for Vercel serverless deployment (synchronous processing, no threading).
"""

from flask import Flask, request, send_file, render_template_string, jsonify
import zipfile
import os
import tempfile
import shutil
from io import BytesIO

app = Flask(__name__)

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
            </div>
        </form>
        
        <div class="progress-container" id="progressContainer">
            <div class="progress-bar">
                <div class="progress-fill" id="progressFill">Processing...</div>
            </div>
            <div class="status-text" id="statusText">Processing your ZIP file, please wait...</div>
            <div class="timer" id="timer">Time elapsed: 0s</div>
        </div>
    </div>
    <p style="text-align: center;"><small>Output will be named based on your ZIP filename</small></p>

    <script>
        let startTime;
        let timerInterval;

        document.getElementById('uploadForm').onsubmit = async function(e) {
            e.preventDefault();
            
            const formData = new FormData(this);
            const submitBtn = document.getElementById('submitBtn');
            const progressContainer = document.getElementById('progressContainer');
            const progressFill = document.getElementById('progressFill');
            const statusText = document.getElementById('statusText');
            const timerDiv = document.getElementById('timer');
            
            const includeStructure = document.getElementById('include_structure').checked;
            const includeCode = document.getElementById('include_code').checked;
            
            if (!includeStructure && !includeCode) {
                alert('Please select at least one option (Folder structure or File contents)');
                return;
            }
            
            progressContainer.style.display = 'block';
            submitBtn.disabled = true;
            startTime = Date.now();
            
            timerInterval = setInterval(() => {
                const elapsed = ((Date.now() - startTime) / 1000).toFixed(1);
                timerDiv.textContent = `Time elapsed: ${elapsed}s`;
            }, 100);
            
            try {
                const response = await fetch('/process', {
                    method: 'POST',
                    body: formData
                });
                
                clearInterval(timerInterval);
                
                if (response.ok) {
                    progressFill.style.width = '100%';
                    progressFill.textContent = '100%';
                    
                    const elapsed = ((Date.now() - startTime) / 1000).toFixed(1);
                    statusText.textContent = `✓ Complete in ${elapsed}s — downloading...`;
                    timerDiv.textContent = `Total time: ${elapsed}s`;
                    
                    const contentDisposition = response.headers.get('Content-Disposition');
                    let filename = 'output.txt';
                    if (contentDisposition) {
                        const filenameMatch = contentDisposition.match(/filename="?(.+)"?/);
                        if (filenameMatch) filename = filenameMatch[1];
                    }
                    
                    const blob = await response.blob();
                    const url = window.URL.createObjectURL(blob);
                    const a = document.createElement('a');
                    a.href = url;
                    a.download = filename;
                    a.click();
                    
                    setTimeout(() => {
                        progressContainer.style.display = 'none';
                        progressFill.style.width = '0%';
                        progressFill.textContent = 'Processing...';
                        submitBtn.disabled = false;
                    }, 3000);
                } else {
                    const errorText = await response.text();
                    statusText.textContent = '✗ Error: ' + errorText;
                    submitBtn.disabled = false;
                }
            } catch (error) {
                clearInterval(timerInterval);
                statusText.textContent = '✗ Error: ' + error.message;
                submitBtn.disabled = false;
            }
        };
    </script>
</body>
</html>
"""

# ============================================================================
# TERMINAL WIDTH
# ============================================================================

TERMINAL_WIDTH = 80

# ============================================================================
# SMART FILTERING CONFIGURATION
# ============================================================================

SKIP_FOLDERS = {
    'node_modules', 'vendor', 'venv', 'env', '.env', 'virtualenv',
    '__pycache__', '.pytest_cache', '.mypy_cache', '.git', '.svn', '.hg',
    'dist', 'build', 'out', '.next', '.nuxt', 'coverage', '.nyc_output',
    '.cache', '.vite', '.turbo', '.parcel-cache', 'tmp', 'temp', '.temp',
    '.idea', '.vscode', '.vs', 'bower_components', 'jspm_packages',
    '.sass-cache', '.gradle', 'target', 'Pods', '.flutter-plugins',
    '.dart_tool', '.pub-cache',
}

SOURCE_CODE_EXTENSIONS = {
    # JavaScript / TypeScript
    '.js', '.jsx', '.ts', '.tsx', '.mjs', '.cjs',
    # Python
    '.py', '.pyw',
    # Java / Kotlin / Scala
    '.java', '.kt', '.kts', '.scala',
    # C / C++ / C#
    '.c', '.h', '.cpp', '.hpp', '.cc', '.cxx', '.cs',
    # Go
    '.go',
    # Rust
    '.rs',
    # Ruby
    '.rb', '.rake', '.gemspec',
    # PHP
    '.php',
    # Swift
    '.swift',
    # CSS / Styles
    '.css', '.scss', '.sass', '.less', '.styl',
    # HTML / Templates
    '.html', '.htm', '.ejs', '.hbs', '.handlebars', '.mustache', '.pug', '.jade',
    # Config / Data
    '.json', '.yaml', '.yml', '.toml', '.xml', '.ini', '.conf', '.config',
    # Documentation
    '.md', '.mdx', '.txt', '.rst',
    # Shell
    '.sh', '.bash', '.zsh', '.fish',
    # SQL
    '.sql',
    # GraphQL
    '.graphql', '.gql',
    # Dockerfile
    '.dockerfile',
}

IMPORTANT_FILES = {
    'Makefile', 'Dockerfile', 'docker-compose.yml', 'docker-compose.yaml',
    'Procfile', 'Rakefile', 'Gemfile', 'Podfile', 'CMakeLists.txt',
    'README', 'LICENSE', 'CHANGELOG', '.gitignore', '.dockerignore',
    '.eslintrc', '.prettierrc', '.babelrc', '.env.example', '.env.sample',
    'requirements.txt', 'setup.py', 'pyproject.toml', 'Cargo.toml',
    'go.mod', 'go.sum',
}

CONFIG_PATTERNS = {
    'package.json', 'tsconfig', 'jsconfig', 'webpack.config', 'vite.config',
    'rollup.config', 'babel.config', 'jest.config', 'vitest.config',
    'tailwind.config', 'postcss.config', 'eslint.config', 'prettier.config',
    '.eslintrc', '.prettierrc', 'next.config', 'nuxt.config', 'svelte.config',
    'vue.config', 'angular.json',
}

SKIP_PATTERNS = {
    '.min.js', '.min.css', '.bundle.js', '.chunk.js', '.map', '.lock',
    'package-lock.json', 'yarn.lock', 'pnpm-lock.yaml', 'bun.lockb',
    'poetry.lock', 'Gemfile.lock', 'Cargo.lock', '.DS_Store', 'Thumbs.db',
    '.swp', '.swo',
}

BINARY_EXTENSIONS = {
    '.jpg', '.jpeg', '.png', '.gif', '.bmp', '.ico', '.svg', '.webp', '.tiff',
    '.mp4', '.avi', '.mov', '.wmv', '.flv', '.webm', '.mkv',
    '.mp3', '.wav', '.ogg', '.m4a', '.flac',
    '.ttf', '.otf', '.woff', '.woff2', '.eot',
    '.zip', '.tar', '.gz', '.rar', '.7z', '.bz2',
    '.exe', '.dll', '.so', '.dylib', '.bin', '.o', '.pyc', '.pyo',
    '.pdf', '.doc', '.docx', '.xls', '.xlsx', '.ppt', '.pptx',
    '.db', '.sqlite', '.sqlite3',
}


def should_skip_folder(folder_name):
    return folder_name.lower() in SKIP_FOLDERS or folder_name.startswith('.')


def should_include_file(filename):
    filename_lower = filename.lower()
    for pattern in SKIP_PATTERNS:
        if pattern in filename_lower:
            return False
    _, ext = os.path.splitext(filename_lower)
    if ext in BINARY_EXTENSIONS:
        return False
    if filename in IMPORTANT_FILES:
        return True
    for pattern in CONFIG_PATTERNS:
        if pattern in filename_lower:
            return True
    if ext in SOURCE_CODE_EXTENSIONS:
        return True
    return False


def is_text_file(filepath):
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            f.read(8192)
        return True
    except (UnicodeDecodeError, PermissionError):
        return False


def generate_separator(text):
    text_with_spaces = f" {text} "
    text_length = len(text_with_spaces)
    if text_length >= TERMINAL_WIDTH:
        return f"={'=' * TERMINAL_WIDTH}\n"
    remaining = TERMINAL_WIDTH - text_length
    left_padding = remaining // 2
    right_padding = remaining - left_padding
    return f"{'=' * left_padding}{text_with_spaces}{'=' * right_padding}\n"


def generate_tree_structure(temp_dir, stats=None):
    lines = []
    lines.append(generate_separator("FOLDER STRUCTURE"))

    def add_tree(directory, prefix=""):
        try:
            entries = sorted(os.listdir(directory))
            dirs = [e for e in entries
                    if os.path.isdir(os.path.join(directory, e))
                    and not should_skip_folder(e)]
            files = [e for e in entries
                     if os.path.isfile(os.path.join(directory, e))
                     and should_include_file(e)]
            all_entries = dirs + files
            for i, entry in enumerate(all_entries):
                path = os.path.join(directory, entry)
                is_last = (i == len(all_entries) - 1)
                connector = "└── " if is_last else "├── "
                if os.path.isdir(path):
                    lines.append(prefix + connector + entry + "/\n")
                else:
                    lines.append(prefix + connector + entry + "\n")
                if os.path.isdir(path):
                    extension = "    " if is_last else "│   "
                    add_tree(path, prefix + extension)
        except PermissionError:
            pass

    root_name = os.path.basename(temp_dir)
    lines.append(root_name + "/\n")
    add_tree(temp_dir)
    lines.append("\n")
    return "".join(lines)


def count_processable_files(temp_dir):
    count = 0
    for root, dirs, files in os.walk(temp_dir):
        dirs[:] = [d for d in dirs if not should_skip_folder(d)]
        for filename in files:
            if should_include_file(filename):
                filepath = os.path.join(root, filename)
                if is_text_file(filepath):
                    count += 1
    return count


def process_zip_to_text(zip_file, include_structure=True, include_code=True, include_stats=True):
    """Process ZIP file and return text output as BytesIO."""
    temp_dir = tempfile.mkdtemp()
    output = BytesIO()

    stats = {
        'processed': 0,
        'skipped': 0,
        'total_files': 0,
        'total_size': 0,
    }

    try:
        with zipfile.ZipFile(zip_file, 'r') as zip_ref:
            zip_ref.extractall(temp_dir)

        if include_structure:
            tree = generate_tree_structure(temp_dir, stats)
            output.write(tree.encode('utf-8'))

        if include_code:
            for root, dirs, files in os.walk(temp_dir):
                dirs[:] = [d for d in dirs if not should_skip_folder(d)]
                for filename in sorted(files):
                    filepath = os.path.join(root, filename)
                    stats['total_files'] += 1

                    if not should_include_file(filename):
                        stats['skipped'] += 1
                        continue

                    if not is_text_file(filepath):
                        stats['skipped'] += 1
                        continue

                    stats['processed'] += 1
                    rel_path = os.path.relpath(filepath, temp_dir)
                    output.write(generate_separator(rel_path).encode('utf-8'))

                    try:
                        file_size = os.path.getsize(filepath)
                        stats['total_size'] += file_size
                        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                            for line_num, line in enumerate(f, start=1):
                                output.write(f"{line_num}: {line.rstrip()}\n".encode('utf-8'))
                    except Exception as e:
                        output.write(f"(Error reading file: {str(e)})\n".encode('utf-8'))

                    output.write(b"\n")

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
        shutil.rmtree(temp_dir)


# ============================================================================
# ROUTES
# ============================================================================

@app.route('/', methods=['GET'])
def upload_page():
    return render_template_string(HTML_TEMPLATE)


@app.route('/process', methods=['POST'])
def process_file():
    if 'zipfile' not in request.files:
        return "No file uploaded", 400

    file = request.files['zipfile']

    if file.filename == '':
        return "No file selected", 400

    if not file.filename.endswith('.zip'):
        return "Please upload a ZIP file", 400

    include_structure = 'include_structure' in request.form
    include_code = 'include_code' in request.form
    include_stats = 'include_stats' in request.form

    if not include_structure and not include_code:
        return "Please select at least one option", 400

    zip_basename = os.path.splitext(file.filename)[0]
    output_filename = f"{zip_basename}_source_code.txt"

    try:
        output = process_zip_to_text(file, include_structure, include_code, include_stats)
        return send_file(
            output,
            as_attachment=True,
            download_name=output_filename,
            mimetype='text/plain'
        )
    except Exception as e:
        return f"Error processing file: {str(e)}", 500
