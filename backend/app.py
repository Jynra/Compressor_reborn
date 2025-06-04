# backend/app.py
from flask import Flask, request, jsonify, send_file, send_from_directory
from flask_cors import CORS
from werkzeug.utils import secure_filename
import os
import shutil
from pathlib import Path
import uuid
import json
from datetime import datetime
import threading
import time

# Importer notre compresseur
from file_compressor import FileCompressor

# Configuration pour servir les fichiers statiques React
app = Flask(__name__, 
           static_folder='../frontend/build',
           static_url_path='')
CORS(app)

# Configuration
app.config['MAX_CONTENT_LENGTH'] = 500 * 1024 * 1024  # 500MB max
app.config['UPLOAD_FOLDER'] = '/app/uploads'
app.config['COMPRESSED_FOLDER'] = '/app/compressed'

# Créer les dossiers nécessaires
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(app.config['COMPRESSED_FOLDER'], exist_ok=True)

# Stockage en mémoire des tâches (en production, utiliser Redis)
tasks = {}
task_results = {}

class CompressionTask:
    def __init__(self, task_id, files):
        self.task_id = task_id
        self.files = files
        self.status = 'pending'
        self.progress = 0
        self.total_files = len(files)
        self.processed_files = 0
        self.results = []
        self.error_message = None
        self.created_at = datetime.now()
        self.completed_at = None

def compress_files_async(task_id, files, settings):
    """Fonction de compression asynchrone"""
    task = tasks[task_id]
    task.status = 'processing'
    
    try:
        # Créer un dossier unique pour cette tâche
        task_folder = Path(app.config['COMPRESSED_FOLDER']) / task_id
        task_folder.mkdir(exist_ok=True)
        
        compressor = FileCompressor(str(task_folder))
        
        for i, file_info in enumerate(files):
            try:
                file_path = Path(file_info['path'])
                extension = file_path.suffix.lower()
                
                # Préparer les paramètres selon le type de fichier
                compression_params = {}
                
                if extension in compressor.image_extensions:
                    compression_params = {
                        'quality': settings.get('quality', 85),
                        'max_resolution': (
                            settings.get('max_width', 1920),
                            settings.get('max_height', 1080)
                        )
                    }
                elif extension in compressor.video_extensions:
                    compression_params = {
                        'bitrate': settings.get('video_bitrate', '1000k'),
                        'resolution': (
                            settings.get('max_width', 1280),
                            settings.get('max_height', 720)
                        )
                    }
                elif extension in compressor.audio_extensions:
                    compression_params = {
                        'bitrate': settings.get('audio_bitrate', '128k'),
                        'format': 'mp3'
                    }
                # Pour PDF, pas de paramètres spéciaux nécessaires
                
                # Compresser le fichier
                original_size = compressor.get_file_size(file_path)
                output_path = compressor.compress_file(file_path, **compression_params)
                
                if output_path and output_path.exists():
                    compressed_size = compressor.get_file_size(output_path)
                    compression_ratio = (1 - compressed_size / original_size) * 100 if original_size > 0 else 0
                    
                    result = {
                        'filename': file_info['filename'],
                        'original_size': original_size,
                        'compressed_size': compressed_size,
                        'compression_ratio': compression_ratio,
                        'output_path': str(output_path),
                        'status': 'success'
                    }
                else:
                    result = {
                        'filename': file_info['filename'],
                        'status': 'error',
                        'error': 'Compression failed'
                    }
                
                task.results.append(result)
                task.processed_files += 1
                task.progress = (task.processed_files / task.total_files) * 100
                
            except Exception as e:
                result = {
                    'filename': file_info['filename'],
                    'status': 'error',
                    'error': str(e)
                }
                task.results.append(result)
                task.processed_files += 1
                task.progress = (task.processed_files / task.total_files) * 100
        
        task.status = 'completed'
        task.completed_at = datetime.now()
        
    except Exception as e:
        task.status = 'error'
        task.error_message = str(e)
        task.completed_at = datetime.now()

@app.route('/')
def index():
    """Servir le frontend React"""
    return send_from_directory(app.static_folder, 'index.html')

@app.route('/static/<path:filename>')
def static_files(filename):
    """Servir les fichiers statiques React (CSS, JS, etc.)"""
    return send_from_directory(os.path.join(app.static_folder, 'static'), filename)

@app.route('/favicon.ico')
def favicon():
    """Servir le favicon"""
    return send_from_directory(app.static_folder, 'favicon.ico')

@app.route('/logo192.png')
def logo192():
    """Servir le logo PWA"""
    return send_from_directory(app.static_folder, 'logo192.png')

@app.route('/manifest.json')
def manifest():
    """Servir le manifeste PWA"""
    return send_from_directory(app.static_folder, 'manifest.json')

@app.route('/<path:path>')
def serve_react_routes(path):
    """Servir les routes React (SPA routing)"""
    # Si le fichier existe, le servir
    if os.path.exists(os.path.join(app.static_folder, path)):
        return send_from_directory(app.static_folder, path)
    # Sinon, servir index.html pour les routes React
    return send_from_directory(app.static_folder, 'index.html')

@app.route('/api/upload', methods=['POST'])
def upload_files():
    """Upload des fichiers"""
    if 'files' not in request.files:
        return jsonify({'error': 'No files provided'}), 400
    
    files = request.files.getlist('files')
    if not files or files[0].filename == '':
        return jsonify({'error': 'No files selected'}), 400
    
    # Créer un ID de tâche unique
    task_id = str(uuid.uuid4())
    uploaded_files = []
    
    try:
        # Sauvegarder les fichiers uploadés
        for file in files:
            if file.filename:
                filename = secure_filename(file.filename)
                # Ajouter un timestamp pour éviter les collisions
                unique_filename = f"{int(time.time())}_{filename}"
                file_path = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)
                file.save(file_path)
                
                uploaded_files.append({
                    'filename': filename,
                    'path': file_path,
                    'size': os.path.getsize(file_path)
                })
        
        # Créer la tâche
        task = CompressionTask(task_id, uploaded_files)
        tasks[task_id] = task
        
        return jsonify({
            'task_id': task_id,
            'files_count': len(uploaded_files),
            'total_size': sum(f['size'] for f in uploaded_files)
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/compress', methods=['POST'])
def start_compression():
    """Démarrer la compression"""
    data = request.get_json()
    task_id = data.get('task_id')
    settings = data.get('settings', {})
    
    if not task_id or task_id not in tasks:
        return jsonify({'error': 'Invalid task ID'}), 400
    
    task = tasks[task_id]
    if task.status != 'pending':
        return jsonify({'error': 'Task already processed'}), 400
    
    # Démarrer la compression en arrière-plan
    thread = threading.Thread(
        target=compress_files_async,
        args=(task_id, task.files, settings)
    )
    thread.daemon = True
    thread.start()
    
    return jsonify({'message': 'Compression started', 'task_id': task_id})

@app.route('/api/status/<task_id>')
def get_status(task_id):
    """Obtenir le statut de la tâche"""
    if task_id not in tasks:
        return jsonify({'error': 'Task not found'}), 404
    
    task = tasks[task_id]
    return jsonify({
        'task_id': task_id,
        'status': task.status,
        'progress': task.progress,
        'processed_files': task.processed_files,
        'total_files': task.total_files,
        'results': task.results,
        'error_message': task.error_message,
        'created_at': task.created_at.isoformat() if task.created_at else None,
        'completed_at': task.completed_at.isoformat() if task.completed_at else None
    })

@app.route('/api/download/<task_id>')
def download_compressed(task_id):
    """Télécharger les fichiers compressés (ZIP)"""
    if task_id not in tasks:
        return jsonify({'error': 'Task not found'}), 404
    
    task = tasks[task_id]
    if task.status != 'completed':
        return jsonify({'error': 'Task not completed'}), 400
    
    try:
        # Créer un ZIP avec tous les fichiers compressés
        task_folder = Path(app.config['COMPRESSED_FOLDER']) / task_id
        zip_path = task_folder.parent / f"{task_id}_compressed.zip"
        
        shutil.make_archive(str(zip_path.with_suffix('')), 'zip', str(task_folder))
        
        return send_file(
            str(zip_path),
            as_attachment=True,
            download_name=f"compressed_files_{task_id[:8]}.zip"
        )
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/cleanup/<task_id>', methods=['DELETE'])
def cleanup_task(task_id):
    """Nettoyer les fichiers d'une tâche"""
    if task_id not in tasks:
        return jsonify({'error': 'Task not found'}), 404
    
    try:
        task = tasks[task_id]
        
        # Supprimer les fichiers uploadés
        for file_info in task.files:
            if os.path.exists(file_info['path']):
                os.remove(file_info['path'])
        
        # Supprimer le dossier de sortie
        task_folder = Path(app.config['COMPRESSED_FOLDER']) / task_id
        if task_folder.exists():
            shutil.rmtree(task_folder)
        
        # Supprimer le ZIP s'il existe
        zip_path = task_folder.parent / f"{task_id}_compressed.zip"
        if zip_path.exists():
            zip_path.unlink()
        
        # Supprimer la tâche de la mémoire
        del tasks[task_id]
        
        return jsonify({'message': 'Task cleaned up successfully'})
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/supported-formats')
def get_supported_formats():
    """Retourner les formats supportés"""
    return jsonify({
        'images': ['.jpg', '.jpeg', '.png', '.webp', '.bmp', '.tiff', '.heic', '.heif'],
        'videos': ['.mp4', '.avi', '.mov', '.mkv', '.wmv', '.flv'],
        'audio': ['.mp3', '.wav', '.flac', '.aac', '.ogg', '.m4a'],
        'documents': ['.pdf']
    })

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)