"""Tests for AudioPlayer module."""

import unittest
from unittest.mock import patch, MagicMock, mock_open
import os


class TestAudioPlayer(unittest.TestCase):
    """Test AudioPlayer functionality."""

    @patch('src.rfid_audio_player.audio_player.pygame')
    def setUp(self, mock_pygame):
        """Set up test fixtures."""
        # Mock pygame to avoid hardware dependencies
        mock_pygame.mixer.init.return_value = None
        mock_pygame.mixer.music.set_volume.return_value = None
        mock_pygame.mixer.music.get_volume.return_value = 0.5

        from src.rfid_audio_player import AudioPlayer
        self.player = AudioPlayer()

    def test_initialization(self):
        """Test that AudioPlayer initializes with correct default state."""
        self.assertEqual(self.player.current_playlist, [])
        self.assertEqual(self.player.current_track_index, -1)
        self.assertFalse(self.player.paused)
        self.assertFalse(self.player.playing)

    @patch('src.rfid_audio_player.audio_player.os.path.isdir')
    @patch('src.rfid_audio_player.audio_player.os.listdir')
    @patch('src.rfid_audio_player.audio_player.pygame')
    def test_load_playlist(self, mock_pygame, mock_listdir, mock_isdir):
        """Test loading a playlist from a folder."""
        # Setup mocks
        mock_isdir.return_value = True
        mock_listdir.side_effect = [
            ['test_folder'],  # First call for MEDIA_PATH
            ['song1.mp3', 'song2.mp3', 'readme.txt']  # Second call for folder contents
        ]
        mock_pygame.mixer.music.load.return_value = None
        mock_pygame.mixer.music.play.return_value = None

        # Load playlist
        self.player.load_playlist('test_folder')

        # Verify playlist was loaded
        self.assertEqual(len(self.player.current_playlist), 2)
        self.assertTrue(self.player.playing)
        self.assertEqual(self.player.current_track_index, 0)

    @patch('src.rfid_audio_player.audio_player.pygame')
    def test_volume_up(self, mock_pygame):
        """Test volume up increases volume correctly."""
        mock_pygame.mixer.music.get_volume.return_value = 0.5
        mock_pygame.mixer.music.set_volume.return_value = None

        self.player.volume_up()

        # Verify set_volume was called with increased value
        mock_pygame.mixer.music.set_volume.assert_called()
        args = mock_pygame.mixer.music.set_volume.call_args[0]
        self.assertGreater(args[0], 0.5)

    @patch('src.rfid_audio_player.audio_player.pygame')
    def test_volume_down(self, mock_pygame):
        """Test volume down decreases volume correctly."""
        mock_pygame.mixer.music.get_volume.return_value = 0.5
        mock_pygame.mixer.music.set_volume.return_value = None

        self.player.volume_down()

        # Verify set_volume was called with decreased value
        mock_pygame.mixer.music.set_volume.assert_called()
        args = mock_pygame.mixer.music.set_volume.call_args[0]
        self.assertLess(args[0], 0.5)

    @patch('src.rfid_audio_player.audio_player.pygame')
    def test_volume_clamping(self, mock_pygame):
        """Test that volume is clamped between 0.0 and 1.0."""
        # Test upper bound
        mock_pygame.mixer.music.get_volume.return_value = 0.95
        self.player.volume_up()
        args = mock_pygame.mixer.music.set_volume.call_args[0]
        self.assertLessEqual(args[0], 1.0)

        # Test lower bound
        mock_pygame.mixer.music.get_volume.return_value = 0.05
        self.player.volume_down()
        args = mock_pygame.mixer.music.set_volume.call_args[0]
        self.assertGreaterEqual(args[0], 0.0)

    @patch('src.rfid_audio_player.audio_player.pygame')
    def test_toggle_pause(self, mock_pygame):
        """Test pause toggle functionality."""
        mock_pygame.mixer.music.pause.return_value = None
        mock_pygame.mixer.music.unpause.return_value = None

        # Set player to playing state
        self.player.playing = True
        self.player.paused = False

        # Pause
        self.player.toggle_pause()
        self.assertTrue(self.player.paused)
        mock_pygame.mixer.music.pause.assert_called_once()

        # Unpause
        self.player.toggle_pause()
        self.assertFalse(self.player.paused)
        mock_pygame.mixer.music.unpause.assert_called_once()


if __name__ == '__main__':
    unittest.main()
