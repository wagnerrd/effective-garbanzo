# web_server.py
from flask import Flask, jsonify, request, send_from_directory
import os
import threading
import pygame
import subprocess
import shutil
from .config import MEDIA_PATH, SUPPORTED_EXTENSIONS

class WebServer:
    def __init__(self, audio_player, rfid_reader=None):
        """Initialize the Flask web server with a reference to the AudioPlayer and optional RFID Reader."""
        self.audio_player = audio_player
        self.rfid_reader = rfid_reader
        # Get the absolute path to the static folder (project root/static)
        current_dir = os.path.dirname(os.path.abspath(__file__))
        project_root = os.path.dirname(os.path.dirname(current_dir))
        static_folder = os.path.join(project_root, 'static')
        self.app = Flask(__name__, static_folder=static_folder, static_url_path='')
        self._setup_routes()

    def _setup_routes(self):
        """Set up all Flask routes."""

        # Serve the main page
        @self.app.route('/')
        def index():
            return send_from_directory(self.app.static_folder, 'index.html')

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
                        audio_files = self._list_folder_audio_files(folder_path)
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
            for info in self._list_folder_audio_files(folder_path):
                files.append({
                    'name': info['display_name'],
                    'path': info['relative_path'],
                    'size': info['size'],
                    'size_mb': round(info['size'] / (1024 * 1024), 2)
                })

            return jsonify({'files': files})

        # Delete a file
        @self.app.route('/api/media/folders/<folder_name>/files/<path:filename>', methods=['DELETE'])
        def delete_file(folder_name, filename):
            file_path = os.path.join(MEDIA_PATH, folder_name, filename)
            file_path = os.path.realpath(file_path)
            folder_path = os.path.realpath(os.path.join(MEDIA_PATH, folder_name))
            if not file_path.startswith(folder_path):
                return jsonify({'error': 'Invalid file path'}), 400

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

        @self.app.route('/api/media/folders/<folder_name>/play', methods=['POST'])
        def play_folder(folder_name):
            folder_path = os.path.join(MEDIA_PATH, folder_name)
            if not os.path.exists(folder_path) or not os.path.isdir(folder_path):
                return jsonify({'error': 'Folder not found'}), 404

            success = self.audio_player.load_playlist(folder_name)
            if not success:
                return jsonify({'error': 'No playable audio files found in this folder'}), 400

            return jsonify({'success': True, 'message': f'Playing folder {folder_name}'})

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

        @self.app.route('/api/media/convert', methods=['POST'])
        def convert_media():
            result = self._convert_unsupported_files()
            status_code = 200 if result.get('success') else 500
            return jsonify(result), status_code

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

    def _convert_unsupported_files(self) -> dict:
        """
        Scans MEDIA_PATH for files that are not in SUPPORTED_EXTENSIONS.
        Converts them to high bitrate MP3 files using ffmpeg and stores
        them in a 'Converted' subfolder next to the source file.
        """
        if not os.path.exists(MEDIA_PATH):
            return {'success': True, 'message': 'Media directory does not exist yet.'}

        ffmpeg_path = shutil.which('ffmpeg')
        if not ffmpeg_path:
            return {
                'success': False,
                'error': 'ffmpeg executable not found. Install ffmpeg to convert audio files.'
            }

        converted = []
        errors = []

        for root, dirs, files in os.walk(MEDIA_PATH):
            # Skip any existing Converted subdirectories to avoid re-processing
            dirs[:] = [d for d in dirs if d.lower() != 'converted']

            for filename in files:
                ext = os.path.splitext(filename)[1].lower()
                if not ext or ext in SUPPORTED_EXTENSIONS:
                    continue

                source_path = os.path.join(root, filename)
                converted_dir = os.path.join(root, 'Converted')
                os.makedirs(converted_dir, exist_ok=True)
                target_name = os.path.splitext(filename)[0] + '.mp3'
                target_path = os.path.join(converted_dir, target_name)

                if os.path.exists(target_path):
                    converted.append({'source': source_path, 'target': target_path, 'skipped': True})
                    continue

                cmd = [
                    ffmpeg_path,
                    '-y',
                    '-i', source_path,
                    '-vn',
                    '-ar', '44100',
                    '-ac', '2',
                    '-b:a', '320k',
                    target_path
                ]

                try:
                    subprocess.run(
                        cmd,
                        check=True,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE
                    )
                    converted.append({'source': source_path, 'target': target_path, 'skipped': False})
                except subprocess.CalledProcessError as exc:
                    error_msg = exc.stderr.decode('utf-8', errors='ignore') if exc.stderr else str(exc)
                    errors.append({'file': source_path, 'error': error_msg.strip()})

        if not converted and not errors:
            return {'success': True, 'message': 'No unsupported files found.'}

        if errors:
            return {
                'success': False,
                'error': 'Some files could not be converted.',
                'converted_count': len([c for c in converted if not c.get('skipped')]),
                'skipped_count': len([c for c in converted if c.get('skipped')]),
                'errors': errors
            }

        converted_count = len([c for c in converted if not c.get('skipped')])
        skipped_count = len([c for c in converted if c.get('skipped')])
        message = f'Converted {converted_count} file(s).'
        if skipped_count:
            message += f' Skipped {skipped_count} existing file(s).'

        return {
            'success': True,
            'message': message,
            'converted_count': converted_count,
            'skipped_count': skipped_count
        }

    def _list_folder_audio_files(self, folder_path: str) -> list[dict]:
        """
        Returns metadata about supported audio files located in the folder
        or its nested 'Converted' directory.
        """
        files = []
        search_dirs = [folder_path]
        converted_dir = os.path.join(folder_path, 'Converted')
        if os.path.isdir(converted_dir):
            search_dirs.append(converted_dir)

        for directory in search_dirs:
            try:
                entries = os.listdir(directory)
            except FileNotFoundError:
                continue

            rel_dir = os.path.relpath(directory, folder_path)
            rel_dir = '' if rel_dir == '.' else rel_dir

            for entry in entries:
                if not any(entry.lower().endswith(ext) for ext in SUPPORTED_EXTENSIONS):
                    continue

                abs_path = os.path.join(directory, entry)
                if not os.path.isfile(abs_path):
                    continue

                relative_path = os.path.join(rel_dir, entry) if rel_dir else entry
                relative_path = relative_path.replace('\\', '/')

                files.append({
                    'absolute_path': abs_path,
                    'relative_path': relative_path,
                    'display_name': relative_path,
                    'size': os.path.getsize(abs_path),
                })

        return files

    def run(self, host='0.0.0.0', port=5000):
        """Run the Flask server in a separate thread."""
        def run_server():
            self.app.run(host=host, port=port, debug=False, threaded=True)

        server_thread = threading.Thread(target=run_server, daemon=True)
        server_thread.start()
        print(f"🌐 Web interface started at http://{host}:{port}")
        return server_thread
