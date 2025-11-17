# audio_player.py
import pygame
from random import shuffle
import os
from .config import (
    MEDIA_PATH, SUPPORTED_EXTENSIONS,
    DEFAULT_VOLUME
)

class AudioPlayer:
    def __init__(self):
        """Initializes the pygame mixer."""
        try:
            pygame.mixer.init()
            pygame.mixer.music.set_volume(DEFAULT_VOLUME)
            print("AudioPlayer initialized.")
        except pygame.error as e:
            print(f"Error initializing pygame mixer: {e}")
            print("Do you have a valid audio output device connected (e.g., USB audio)?")

        # State variables
        self.current_playlist = []  # List of full file paths
        self.current_track_index = -1
        self.paused = False
        self.playing = False

    def load_playlist(self, key):
        """
        Loads a new playlist based on a key.
        Returns True on success so web requests can report errors.
        """
        existing_folders = os.listdir(MEDIA_PATH)
        if key not in existing_folders:
            print(f"Error: no folder named {key} in media directory.")
            return False

        folder_path = os.path.join(MEDIA_PATH, key)

        if not os.path.isdir(folder_path):
            print(f"Error: Directory not found: {folder_path}")
            return False

        # Scan the directory (and nested Converted folder if present) for supported audio files
        self.current_playlist = self._gather_audio_files(folder_path)
        shuffle(self.current_playlist)

        if not self.current_playlist:
            print(f"No audio files found in {folder_path}")
            return False
        
        print(f"Loaded {len(self.current_playlist)} tracks from '{key}'.")
        self.current_track_index = 0
        self._play_current_track()
        return True

    def _play_current_track(self):
        """Internal helper to load and play the current track."""
        if not self.current_playlist or self.current_track_index == -1:
            print("No playlist loaded.")
            return

        track_path = self.current_playlist[self.current_track_index]
        try:
            pygame.mixer.music.load(track_path)
            pygame.mixer.music.play()
            self.playing = True
            self.paused = False
            track_num = self.current_track_index + 1
            total_tracks = len(self.current_playlist)
            print(f"♪ Now Playing [{track_num}/{total_tracks}]: {os.path.basename(track_path)}")
        except pygame.error as e:
            print(f"❌ Error playing track {track_path}: {e}")

    def toggle_pause(self):
        """Toggles play/pause state."""
        if not self.playing:
            print("No music is currently playing. Please scan an RFID tag first.")
            return

        if self.paused:
            pygame.mixer.music.unpause()
            self.paused = False
            print("▶ Resumed playback.")
        else:
            pygame.mixer.music.pause()
            self.paused = True
            print("⏸ Paused.")

    def next_track(self):
        """Skips to the next track in the playlist, wrapping around."""
        if not self.current_playlist:
            print("No playlist loaded. Please scan an RFID tag first.")
            return

        # Increment index and wrap around if at the end
        self.current_track_index = (self.current_track_index + 1) % len(self.current_playlist)
        print(f"⏭ Next track ({self.current_track_index + 1}/{len(self.current_playlist)})")
        self._play_current_track()

    def prev_track(self):
        """Goes to the previous track, wrapping around."""
        if not self.current_playlist:
            print("No playlist loaded. Please scan an RFID tag first.")
            return

        # Decrement index and wrap around if at the beginning
        self.current_track_index = (self.current_track_index - 1) % len(self.current_playlist)
        print(f"⏮ Previous track ({self.current_track_index + 1}/{len(self.current_playlist)})")
        self._play_current_track()

    def volume_up(self):
        """Increases volume by 10%."""
        current_vol = pygame.mixer.music.get_volume()
        new_vol = min(current_vol + 0.1, 1.0) # Cap at 1.0
        pygame.mixer.music.set_volume(new_vol)
        vol_bar = "█" * int(new_vol * 10) + "░" * (10 - int(new_vol * 10))
        print(f"🔊 Volume: [{vol_bar}] {int(new_vol * 100)}%")

    def volume_down(self):
        """Decreases volume by 10%."""
        current_vol = pygame.mixer.music.get_volume()
        new_vol = max(current_vol - 0.1, 0.0) # Floor at 0.0
        pygame.mixer.music.set_volume(new_vol)
        vol_bar = "█" * int(new_vol * 10) + "░" * (10 - int(new_vol * 10))
        print(f"🔉 Volume: [{vol_bar}] {int(new_vol * 100)}%")

    def check_for_song_end(self):
        """
        To be called in the main loop. Checks if a song has
        finished and automatically plays the next one.
        """
        if self.playing and not self.paused:
            # get_busy() returns True if music is playing
            if not pygame.mixer.music.get_busy():
                # Check if we're at the last track
                is_last_track = (self.current_track_index == len(self.current_playlist) - 1)

                if is_last_track:
                    print("✓ Playlist finished.")
                    self.playing = False
                else:
                    print("Song finished, playing next.")
                    self.next_track()

    def stop(self):
        """Stops playback and clears the playlist."""
        pygame.mixer.music.stop()
        self.current_playlist = []
        self.current_track_index = -1
        self.playing = False
        self.paused = False

    def quit(self):
        """Shuts down the mixer."""
        pygame.mixer.quit()

    def _gather_audio_files(self, folder_path: str) -> list[str]:
        """
        Returns a list of supported audio file paths from the folder and
        its nested 'Converted' subfolder (if present).
        """
        files = []
        search_dirs = [folder_path]
        converted_dir = os.path.join(folder_path, 'Converted')
        if os.path.isdir(converted_dir):
            search_dirs.append(converted_dir)

        for directory in search_dirs:
            try:
                for entry in os.listdir(directory):
                    if any(entry.lower().endswith(ext) for ext in SUPPORTED_EXTENSIONS):
                        files.append(os.path.join(directory, entry))
            except FileNotFoundError:
                continue
        return files
