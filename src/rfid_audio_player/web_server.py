# web_server.py
from flask import Flask, jsonify, request, send_from_directory
import os
import threading
import pygame
from .config import MEDIA_PATH, SUPPORTED_EXTENSIONS

class WebServer:
    def __init__(self, audio_player, rfid_reader=None):
        """Initialize the Flask web server with a reference to the AudioPlayer and optional RFID Reader."""
        self.audio_player = audio_player
        self.rfid_reader = rfid_reader
        self.app = Flask(__name__, static_folder='static', static_url_path='')
        self._setup_routes()

    def _setup_routes(self):
        """Set up all Flask routes."""

        # Serve the main page
        @self.app.route('/')
        def index():
            return send_from_directory('static', 'index.html')

        # Get current player status
        @self.app.route('/api/status', methods=['GET'])
        def get_status():
            current_track = None
            if self.audio_player.current_playlist and self.audio_player.current_track_index >= 0:
                track_path = self.audio_player.current_playlist[self.audio_player.current_track_index]
                current_track = os.path.basename(track_path)

            return jsonify({
                'playing': self.audio_player.playing,
                'paused': self.audio_player.paused,
                'volume': int(pygame.mixer.music.get_volume() * 100),
                'current_track': current_track,
                'track_index': self.audio_player.current_track_index + 1 if self.audio_player.current_track_index >= 0 else 0,
                'total_tracks': len(self.audio_player.current_playlist)
            })

        # Toggle play/pause
        @self.app.route('/api/pause', methods=['POST'])
        def pause():
            self.audio_player.toggle_pause()
            return jsonify({'success': True, 'paused': self.audio_player.paused})

        # Next track
        @self.app.route('/api/next', methods=['POST'])
        def next_track():
            self.audio_player.next_track()
            return jsonify({'success': True})

        # Previous track
        @self.app.route('/api/prev', methods=['POST'])
        def prev_track():
            self.audio_player.prev_track()
            return jsonify({'success': True})

        # Set volume (0-100)
        @self.app.route('/api/volume', methods=['POST'])
        def set_volume():
            data = request.get_json()
            volume = data.get('volume', 50)
            volume = max(0, min(100, volume))  # Clamp between 0-100
            pygame.mixer.music.set_volume(volume / 100.0)
            return jsonify({'success': True, 'volume': volume})

        # Get list of media folders
        @self.app.route('/api/media/folders', methods=['GET'])
        def get_folders():
            folders = []
            if os.path.exists(MEDIA_PATH):
                for item in os.listdir(MEDIA_PATH):
                    folder_path = os.path.join(MEDIA_PATH, item)
                    if os.path.isdir(folder_path):
                        # Count audio files
                        audio_files = [
                            f for f in os.listdir(folder_path)
                            if any(f.endswith(ext) for ext in SUPPORTED_EXTENSIONS)
                        ]
                        folders.append({
                            'name': item,
                            'file_count': len(audio_files),
                        })
            return jsonify({'folders': folders})

        # Get files in a specific folder
        @self.app.route('/api/media/folders/<folder_name>/files', methods=['GET'])
        def get_files(folder_name):
            folder_path = os.path.join(MEDIA_PATH, folder_name)
            if not os.path.exists(folder_path) or not os.path.isdir(folder_path):
                return jsonify({'error': 'Folder not found'}), 404

            files = []
            for f in os.listdir(folder_path):
                if any(f.endswith(ext) for ext in SUPPORTED_EXTENSIONS):
                    file_path = os.path.join(folder_path, f)
                    file_size = os.path.getsize(file_path)
                    files.append({
                        'name': f,
                        'size': file_size,
                        'size_mb': round(file_size / (1024 * 1024), 2)
                    })

            return jsonify({'files': files})

        # Delete a file
        @self.app.route('/api/media/folders/<folder_name>/files/<filename>', methods=['DELETE'])
        def delete_file(folder_name, filename):
            file_path = os.path.join(MEDIA_PATH, folder_name, filename)
            if not os.path.exists(file_path):
                return jsonify({'error': 'File not found'}), 404

            try:
                os.remove(file_path)
                return jsonify({'success': True, 'message': f'Deleted {filename}'})
            except Exception as e:
                return jsonify({'error': str(e)}), 500

        # Upload a file
        @self.app.route('/api/media/folders/<folder_name>/upload', methods=['POST'])
        def upload_file(folder_name):
            folder_path = os.path.join(MEDIA_PATH, folder_name)
            if not os.path.exists(folder_path):
                os.makedirs(folder_path)

            if 'file' not in request.files:
                return jsonify({'error': 'No file provided'}), 400

            file = request.files['file']
            if file.filename is None or file.filename == '':
                return jsonify({'error': 'No file selected'}), 400

            # Check file extension
            if not any(file.filename.endswith(ext) for ext in SUPPORTED_EXTENSIONS):
                return jsonify({'error': f'Unsupported file type. Allowed: {", ".join(SUPPORTED_EXTENSIONS)}'}), 400

            try:
                file_path = os.path.join(folder_path, file.filename)
                file.save(file_path)
                return jsonify({'success': True, 'message': f'Uploaded {file.filename}'})
            except Exception as e:
                return jsonify({'error': str(e)}), 500

        # Create a new folder
        @self.app.route('/api/media/folders', methods=['POST'])
        def create_folder():
            data = request.get_json()
            folder_name = data.get('name', '').strip()

            if not folder_name:
                return jsonify({'error': 'Folder name is required'}), 400

            # Sanitize folder name
            folder_name = "".join(c for c in folder_name if c.isalnum() or c in (' ', '-', '_'))
            folder_path = os.path.join(MEDIA_PATH, folder_name)

            if os.path.exists(folder_path):
                return jsonify({'error': 'Folder already exists'}), 400

            try:
                os.makedirs(folder_path)
                return jsonify({'success': True, 'message': f'Created folder {folder_name}'})
            except Exception as e:
                return jsonify({'error': str(e)}), 500

        # Delete a folder
        @self.app.route('/api/media/folders/<folder_name>', methods=['DELETE'])
        def delete_folder(folder_name):
            folder_path = os.path.join(MEDIA_PATH, folder_name)
            if not os.path.exists(folder_path):
                return jsonify({'error': 'Folder not found'}), 404

            try:
                # Remove all files first
                for f in os.listdir(folder_path):
                    os.remove(os.path.join(folder_path, f))
                os.rmdir(folder_path)
                return jsonify({'success': True, 'message': f'Deleted folder {folder_name}'})
            except Exception as e:
                return jsonify({'error': str(e)}), 500

        # Write text to NFC tag
        @self.app.route('/api/nfc/write', methods=['POST'])
        def write_nfc():
            if self.rfid_reader is None:
                return jsonify({'error': 'RFID reader not available'}), 503

            data = request.get_json()
            text = data.get('text', '').strip()
            lang_code = data.get('lang_code', 'en')

            if not text:
                return jsonify({'error': 'Text is required'}), 400

            try:
                # Attempt to write to the tag
                success = self.rfid_reader.write_text(text, lang_code)
                if success:
                    return jsonify({'success': True, 'message': f'Successfully wrote "{text}" to NFC tag'})
                else:
                    return jsonify({'error': 'Failed to write to NFC tag. Make sure a tag is present.'}), 500
            except Exception as e:
                return jsonify({'error': f'Error writing to NFC tag: {str(e)}'}), 500

    def run(self, host='0.0.0.0', port=5000):
        """Run the Flask server in a separate thread."""
        def run_server():
            self.app.run(host=host, port=port, debug=False, threaded=True)

        server_thread = threading.Thread(target=run_server, daemon=True)
        server_thread.start()
        print(f"🌐 Web interface started at http://{host}:{port}")
        return server_thread
