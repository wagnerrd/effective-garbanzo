# audio_player.py
import pygame
import vlc
import os
from config import (
    MEDIA_PATH, SUPPORTED_EXTENSIONS,
    RFID_MEDIA_MAP, DEFAULT_VOLUME
)

class AudioPlayer:
    def __init__(self):
        """Initializes the pygame mixer and VLC player."""
        try:
            pygame.mixer.init()
            pygame.mixer.music.set_volume(DEFAULT_VOLUME)
            print("AudioPlayer initialized.")
        except pygame.error as e:
            print(f"Error initializing pygame mixer: {e}")
            print("Do you have a valid audio output device connected (e.g., USB audio)?")

        # Initialize VLC for .m4a files
        self.vlc_instance = vlc.Instance()
        self.vlc_player = self.vlc_instance.media_player_new()
        self.vlc_player.audio_set_volume(int(DEFAULT_VOLUME * 100))

        # State variables
        self.current_playlist = []  # List of full file paths
        self.current_track_index = -1
        self.paused = False
        self.playing = False
        self.using_vlc = False  # Track which player is active

    def load_playlist(self, rfid_uid):
        """
        Loads a new playlist based on an RFID UID.
        Stops current playback and starts playing the new list.
        """
        if rfid_uid not in RFID_MEDIA_MAP:
            print(f"Error: UID {rfid_uid} not found in RFID_MEDIA_MAP.")
            return

        folder_name = RFID_MEDIA_MAP[rfid_uid]
        folder_path = os.path.join(MEDIA_PATH, folder_name)

        if not os.path.isdir(folder_path):
            print(f"Error: Directory not found: {folder_path}")
            return

        # Scan the directory for supported audio files and sort them
        self.current_playlist = [
            os.path.join(folder_path, f)
            for f in sorted(os.listdir(folder_path))
            if any(f.endswith(ext) for ext in SUPPORTED_EXTENSIONS)
        ]

        if not self.current_playlist:
            print(f"No audio files found in {folder_path}")
            return
        
        print(f"Loaded {len(self.current_playlist)} tracks from '{folder_name}'.")
        self.current_track_index = 0
        self._play_current_track()

    def _play_current_track(self):
        """Internal helper to load and play the current track."""
        if not self.current_playlist or self.current_track_index == -1:
            print("No playlist loaded.")
            return

        track_path = self.current_playlist[self.current_track_index]
        track_num = self.current_track_index + 1
        total_tracks = len(self.current_playlist)

        # Use VLC for .m4a files, pygame for others
        if track_path.endswith('.m4a'):
            try:
                # Stop pygame if it was playing
                pygame.mixer.music.stop()

                # Use VLC for .m4a
                media = self.vlc_instance.media_new(track_path)
                self.vlc_player.set_media(media)
                self.vlc_player.play()
                self.using_vlc = True
                self.playing = True
                self.paused = False
                print(f"♪ Now Playing (VLC) [{track_num}/{total_tracks}]: {os.path.basename(track_path)}")
            except Exception as e:
                print(f"❌ Error playing track {track_path}: {e}")
        else:
            try:
                # Stop VLC if it was playing
                self.vlc_player.stop()

                # Use pygame for mp3, ogg, wav
                pygame.mixer.music.load(track_path)
                pygame.mixer.music.play()
                self.using_vlc = False
                self.playing = True
                self.paused = False
                print(f"♪ Now Playing [{track_num}/{total_tracks}]: {os.path.basename(track_path)}")
            except pygame.error as e:
                print(f"❌ Error playing track {track_path}: {e}")

    def toggle_pause(self):
        """Toggles play/pause state."""
        if not self.playing:
            print("No music is currently playing. Please scan an RFID tag first.")
            return

        if self.paused:
            if self.using_vlc:
                self.vlc_player.play()
            else:
                pygame.mixer.music.unpause()
            self.paused = False
            print("▶ Resumed playback.")
        else:
            if self.using_vlc:
                self.vlc_player.pause()
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
        if self.using_vlc:
            current_vol = self.vlc_player.audio_get_volume() / 100.0
            new_vol = min(current_vol + 0.1, 1.0)
            self.vlc_player.audio_set_volume(int(new_vol * 100))
        else:
            current_vol = pygame.mixer.music.get_volume()
            new_vol = min(current_vol + 0.1, 1.0)
            pygame.mixer.music.set_volume(new_vol)
        vol_bar = "█" * int(new_vol * 10) + "░" * (10 - int(new_vol * 10))
        print(f"🔊 Volume: [{vol_bar}] {int(new_vol * 100)}%")

    def volume_down(self):
        """Decreases volume by 10%."""
        if self.using_vlc:
            current_vol = self.vlc_player.audio_get_volume() / 100.0
            new_vol = max(current_vol - 0.1, 0.0)
            self.vlc_player.audio_set_volume(int(new_vol * 100))
        else:
            current_vol = pygame.mixer.music.get_volume()
            new_vol = max(current_vol - 0.1, 0.0)
            pygame.mixer.music.set_volume(new_vol)
        vol_bar = "█" * int(new_vol * 10) + "░" * (10 - int(new_vol * 10))
        print(f"🔉 Volume: [{vol_bar}] {int(new_vol * 100)}%")

    def check_for_song_end(self):
        """
        To be called in the main loop. Checks if a song has
        finished and automatically plays the next one.
        """
        if self.playing and not self.paused:
            # Check if music is still playing based on which player is active
            if self.using_vlc:
                is_playing = self.vlc_player.is_playing()
            else:
                is_playing = pygame.mixer.music.get_busy()

            if not is_playing:
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
        self.vlc_player.stop()
        self.current_playlist = []
        self.current_track_index = -1
        self.playing = False
        self.paused = False
        self.using_vlc = False

    def quit(self):
        """Shuts down the mixer."""
        pygame.mixer.quit()
        self.vlc_player.release()
        self.vlc_instance.release()