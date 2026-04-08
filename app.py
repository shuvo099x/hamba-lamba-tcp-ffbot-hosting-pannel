from flask import Flask, request, jsonify, session, render_template_string
import os, json, time, zipfile, io, shutil
from datetime import timedelta

app = Flask(__name__)
app.secret_key = "lamcodex_secret_key_2024"
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(hours=24)

# Use /tmp for Vercel (temporary storage)
BASE_DIR = '/tmp/lamcodex'
UPLOAD_FOLDER = os.path.join(BASE_DIR, 'uploads')
DB_FILE = os.path.join(BASE_DIR, 'database.json')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

ADMIN_PASS = "5656"

def load_db():
    if not os.path.exists(DB_FILE):
        default = {"user_pw": "codex123", "users": {}, "apps": {}}
        with open(DB_FILE, "w") as f: json.dump(default, f)
        return default
    with open(DB_FILE, "r") as f:
        return json.load(f)

def save_db(data):
    with open(DB_FILE, "w") as f: json.dump(data, f, indent=4)

# HTML Login Page
LOGIN_PAGE = '''
<!DOCTYPE html>
<html>
<head>
    <title>Lam Codex Login</title>
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        body {
            margin: 0;
            padding: 0;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            font-family: 'Arial', sans-serif;
            height: 100vh;
            display: flex;
            justify-content: center;
            align-items: center;
        }
        .login-box {
            background: rgba(255,255,255,0.95);
            padding: 40px;
            border-radius: 10px;
            box-shadow: 0 15px 35px rgba(0,0,0,0.2);
            width: 350px;
            text-align: center;
        }
        h2 { color: #333; margin-bottom: 30px; }
        input, select {
            width: 100%;
            padding: 12px;
            margin: 10px 0;
            border: 1px solid #ddd;
            border-radius: 5px;
            font-size: 14px;
        }
        button {
            width: 100%;
            padding: 12px;
            background: #667eea;
            color: white;
            border: none;
            border-radius: 5px;
            font-size: 16px;
            cursor: pointer;
            margin-top: 20px;
        }
        button:hover { background: #5a67d8; }
    </style>
</head>
<body>
    <div class="login-box">
        <h2>🔐 LAM CODEX PANEL</h2>
        <form method="post">
            <select name="login_type">
                <option value="user">👤 User Login</option>
                <option value="admin">👑 Admin Login</option>
            </select>
            <input type="text" name="username" placeholder="Username" required>
            <input type="password" name="password" placeholder="Password" required>
            <button type="submit">Login</button>
        </form>
    </div>
</body>
</html>
'''

# Main HTML Dashboard (embedded in Python)
DASHBOARD = '''
<!DOCTYPE html>
<html lang="bn">
<head>
    <title>Lam Codex Panel</title>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <script src="https://cdn.jsdelivr.net/npm/sweetalert2@11"></script>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            background: #000;
            color: #fff;
            font-family: 'Courier New', monospace;
            padding: 20px;
        }
        .header {
            background: rgba(0,255,255,0.1);
            padding: 15px;
            border-radius: 10px;
            margin-bottom: 20px;
            display: flex;
            justify-content: space-between;
            align-items: center;
            border: 1px solid #0ff;
        }
        .container { max-width: 800px; margin: 0 auto; }
        .upload-card {
            background: rgba(255,255,255,0.05);
            padding: 20px;
            border-radius: 10px;
            border: 2px dashed #0ff;
            margin-bottom: 20px;
            text-align: center;
        }
        .app-card {
            background: rgba(255,255,255,0.05);
            padding: 15px;
            border-radius: 10px;
            margin-bottom: 15px;
            border-left: 3px solid #0ff;
        }
        .button-group {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(100px, 1fr));
            gap: 10px;
            margin: 15px 0;
        }
        .btn {
            padding: 10px;
            border: none;
            border-radius: 5px;
            cursor: pointer;
            font-weight: bold;
            text-decoration: none;
            display: inline-block;
            text-align: center;
            font-size: 12px;
        }
        .btn-start { background: #00ff00; color: #000; }
        .btn-stop { background: #ff0000; color: #fff; }
        .btn-delete { background: #ff4444; color: #fff; }
        .btn-download { background: #0ff; color: #000; }
        .status { display: inline-block; padding: 3px 8px; border-radius: 5px; font-size: 11px; }
        .status-running { background: #00ff00; color: #000; }
        .status-offline { background: #ff0000; color: #fff; }
        pre {
            background: #111;
            padding: 10px;
            border-radius: 5px;
            overflow-x: auto;
            font-size: 10px;
            margin-top: 10px;
            max-height: 100px;
        }
        .social {
            text-align: center;
            margin-top: 30px;
            padding: 20px;
        }
        .social a {
            color: #0ff;
            margin: 0 10px;
            text-decoration: none;
            font-size: 20px;
        }
        input[type="file"] { display: none; }
        .file-label {
            background: #0ff;
            color: #000;
            padding: 10px 20px;
            border-radius: 5px;
            cursor: pointer;
            display: inline-block;
            margin: 10px 0;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h2>🔥 LAM CODEX PANEL</h2>
            <a href="/logout" style="color:#ff4444; text-decoration:none;">🚪 LOGOUT</a>
        </div>

        <div class="upload-card">
            <h3>📤 UPLOAD ZIP PROJECT</h3>
            <form id="uploadForm" enctype="multipart/form-data">
                <label class="file-label" for="fileInput">📁 Choose ZIP File</label>
                <input type="file" id="fileInput" name="file" accept=".zip" required>
                <button type="submit" class="btn btn-start" style="margin-top:10px;">🚀 DEPLOY</button>
            </form>
        </div>

        <div id="appsList"></div>

        <div class="social">
            <a href="https://t.me/lambhaicodex" target="_blank">📱 Telegram</a>
            <a href="https://www.youtube.com/@LamBhaiHK123" target="_blank">▶️ YouTube</a>
            <a href="https://instagram.com/jubayer550022" target="_blank">📷 Instagram</a>
        </div>
    </div>

    <script>
        async function loadApps() {
            const res = await fetch('/api/apps');
            const apps = await res.json();
            const container = document.getElementById('appsList');
            container.innerHTML = '';
            
            for (const app of apps) {
                container.innerHTML += `
                    <div class="app-card">
                        <div style="display:flex; justify-content:space-between; align-items:center;">
                            <strong>📦 ${app.name}</strong>
                            <span id="status-${app.name}" class="status status-offline">OFFLINE</span>
                        </div>
                        <div class="button-group">
                            <a href="/run/${app.name}" class="btn btn-start">▶ START</a>
                            <a href="/stop/${app.name}" class="btn btn-stop">⏹ STOP</a>
                            <a href="/restart/${app.name}" class="btn btn-start">🔄 RESTART</a>
                            <a href="/download/${app.name}" class="btn btn-download">📥 DOWNLOAD</a>
                            <button onclick="deleteApp('${app.name}')" class="btn btn-delete">🗑 DELETE</button>
                        </div>
                        <pre id="log-${app.name}">Loading logs...</pre>
                    </div>
                `;
            }
            
            // Update statuses
            const statusRes = await fetch('/api/status');
            const statuses = await statusRes.json();
            for (const [name, data] of Object.entries(statuses)) {
                const badge = document.getElementById(`status-${name}`);
                const logEl = document.getElementById(`log-${name}`);
                if (badge) {
                    badge.className = data.running ? 'status status-running' : 'status status-offline';
                    badge.innerText = data.running ? 'RUNNING' : 'OFFLINE';
                }
                if (logEl && data.log) logEl.innerText = data.log;
            }
        }
        
        async function deleteApp(name) {
            const result = await Swal.fire({
                title: 'Delete App?',
                text: `Delete ${name} permanently?`,
                icon: 'warning',
                showCancelButton: true
            });
            if (result.isConfirmed) {
                window.location.href = `/delete/${name}`;
            }
        }
        
        document.getElementById('uploadForm').onsubmit = async (e) => {
            e.preventDefault();
            const file = document.getElementById('fileInput').files[0];
            if (!file) return;
            
            const formData = new FormData();
            formData.append('file', file);
            
            const res = await fetch('/upload', { method: 'POST', body: formData });
            const data = await res.json();
            if (data.success) {
                Swal.fire('Success!', 'App deployed successfully', 'success');
                loadApps();
            } else {
                Swal.fire('Error!', data.error, 'error');
            }
        };
        
        loadApps();
        setInterval(loadApps, 5000);
    </script>
</body>
</html>
'''

@app.route('/', methods=['GET', 'POST'])
def home():
    if 'username' not in session:
        if request.method == 'POST':
            login_type = request.form.get('login_type')
            username = request.form.get('username')
            password = request.form.get('password')
            db = load_db()
            
            if login_type == 'admin' and username == 'admin' and password == ADMIN_PASS:
                session['username'] = 'admin'
                session['is_admin'] = True
                return render_template_string(DASHBOARD)
            elif login_type == 'user':
                if username not in db['users']:
                    db['users'][username] = db['user_pw']
                    save_db(db)
                if password == db['users'].get(username):
                    session['username'] = username
                    session['is_admin'] = False
                    return render_template_string(DASHBOARD)
            return render_template_string(LOGIN_PAGE)
        return render_template_string(LOGIN_PAGE)
    return render_template_string(DASHBOARD)

@app.route('/api/apps')
def list_apps():
    if 'username' not in session: return jsonify([])
    user_dir = os.path.join(UPLOAD_FOLDER, session['username'])
    os.makedirs(user_dir, exist_ok=True)
    apps = []
    for item in os.listdir(user_dir):
        if os.path.isdir(os.path.join(user_dir, item)):
            apps.append({'name': item})
    return jsonify(apps)

@app.route('/api/status')
def get_status():
    if 'username' not in session: return jsonify({})
    user_dir = os.path.join(UPLOAD_FOLDER, session['username'])
    statuses = {}
    db = load_db()
    
    for item in os.listdir(user_dir):
        app_path = os.path.join(user_dir, item, 'extracted')
        log_path = os.path.join(user_dir, item, 'logs.txt')
        log_content = ''
        if os.path.exists(log_path):
            with open(log_path, 'r') as f:
                log_content = f.read()[-1000:]
        
        # Check if app was "started" (simulated for Vercel)
        app_key = f"{session['username']}_{item}"
        statuses[item] = {
            'running': db.get('apps', {}).get(app_key, False),
            'log': log_content or 'App deployed. Note: Vercel has limitations for background processes.'
        }
    return jsonify(statuses)

@app.route('/upload', methods=['POST'])
def upload_zip():
    if 'username' not in session: return jsonify({'success': False, 'error': 'Not logged in'})
    
    if 'file' not in request.files:
        return jsonify({'success': False, 'error': 'No file'})
    
    file = request.files['file']
    if file.filename == '' or not file.filename.endswith('.zip'):
        return jsonify({'success': False, 'error': 'Invalid file'})
    
    app_name = file.filename.rsplit('.', 1)[0]
    user_dir = os.path.join(UPLOAD_FOLDER, session['username'], app_name)
    os.makedirs(user_dir, exist_ok=True)
    
    zip_path = os.path.join(user_dir, file.filename)
    file.save(zip_path)
    
    extract_dir = os.path.join(user_dir, 'extracted')
    with zipfile.ZipFile(zip_path, 'r') as zip_ref:
        zip_ref.extractall(extract_dir)
    
    os.remove(zip_path)
    return jsonify({'success': True})

@app.route('/run/<name>')
def run_app(name):
    if 'username' not in session: return redirect('/')
    
    db = load_db()
    app_key = f"{session['username']}_{name}"
    if 'apps' not in db: db['apps'] = {}
    
    # Simulate running (Vercel can't actually run background processes)
    db['apps'][app_key] = True
    
    # Create log entry
    log_path = os.path.join(UPLOAD_FOLDER, session['username'], name, 'logs.txt')
    with open(log_path, 'a') as f:
        f.write(f"[{time.ctime()}] App started (simulated mode for Vercel)\n")
    
    save_db(db)
    return redirect('/')

@app.route('/stop/<name>')
def stop_app(name):
    if 'username' not in session: return redirect('/')
    
    db = load_db()
    app_key = f"{session['username']}_{name}"
    if 'apps' in db:
        db['apps'][app_key] = False
    
    log_path = os.path.join(UPLOAD_FOLDER, session['username'], name, 'logs.txt')
    with open(log_path, 'a') as f:
        f.write(f"[{time.ctime()}] App stopped\n")
    
    save_db(db)
    return redirect('/')

@app.route('/restart/<name>')
def restart_app(name):
    stop_app(name)
    return run_app(name)

@app.route('/download/<name>')
def download_app(name):
    if 'username' not in session: return redirect('/')
    
    app_dir = os.path.join(UPLOAD_FOLDER, session['username'], name, 'extracted')
    if not os.path.exists(app_dir):
        return "App not found", 404
    
    memory_file = io.BytesIO()
    with zipfile.ZipFile(memory_file, 'w', zipfile.ZIP_DEFLATED) as zf:
        for root, dirs, files in os.walk(app_dir):
            for file in files:
                file_path = os.path.join(root, file)
                arcname = os.path.relpath(file_path, app_dir)
                zf.write(file_path, arcname)
    
    memory_file.seek(0)
    return send_file(memory_file, download_name=f"{name}.zip", as_attachment=True)

@app.route('/delete/<name>')
def delete_app(name):
    if 'username' not in session: return redirect('/')
    
    app_dir = os.path.join(UPLOAD_FOLDER, session['username'], name)
    if os.path.exists(app_dir):
        shutil.rmtree(app_dir)
    
    db = load_db()
    app_key = f"{session['username']}_{name}"
    if 'apps' in db and app_key in db['apps']:
        del db['apps'][app_key]
        save_db(db)
    
    return redirect('/')

@app.route('/logout')
def logout():
    session.clear()
    return redirect('/')

# For Vercel serverless
from flask import send_file

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)

# This is for Vercel
app.debug = False
