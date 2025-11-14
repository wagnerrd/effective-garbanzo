"""Tests for Button Handler module."""

import unittest
from unittest.mock import patch, MagicMock


class TestButtonHandler(unittest.TestCase):
    """Test Button Handler functionality."""

    @patch('src.rfid_audio_player.button_handler.Button')
    def setUp(self, mock_button_class):
        """Set up test fixtures."""
        # Mock the Button class to avoid GPIO hardware dependencies
        self.mock_buttons = {}

        def create_mock_button(*args, **kwargs):
            mock = MagicMock()
            return mock

        mock_button_class.side_effect = create_mock_button

        # Mock the audio player
        self.mock_player = MagicMock()
        self.mock_player.toggle_pause = MagicMock()
        self.mock_player.volume_up = MagicMock()
        self.mock_player.volume_down = MagicMock()
        self.mock_player.next_track = MagicMock()
        self.mock_player.prev_track = MagicMock()

        from src.rfid_audio_player import ButtonControls
        self.buttons = ButtonControls(self.mock_player)

    def test_initialization(self):
        """Test that ButtonControls initializes correctly."""
        self.assertIsNotNone(self.buttons.audio_player)
        self.assertIsNotNone(self.buttons.btn_play_pause)
        self.assertIsNotNone(self.buttons.btn_vol_up)
        self.assertIsNotNone(self.buttons.btn_vol_down)
        self.assertIsNotNone(self.buttons.btn_next)
        self.assertIsNotNone(self.buttons.btn_prev)

    def test_play_pause_handler(self):
        """Test that play/pause button handler calls audio player."""
        # Simulate button press
        self.buttons._on_play_pause(None)

        # Verify audio player method was called
        self.mock_player.toggle_pause.assert_called_once()

    def test_volume_up_handler(self):
        """Test that volume up button handler calls audio player."""
        self.buttons._on_volume_up(None)
        self.mock_player.volume_up.assert_called_once()

    def test_volume_down_handler(self):
        """Test that volume down button handler calls audio player."""
        self.buttons._on_volume_down(None)
        self.mock_player.volume_down.assert_called_once()

    def test_next_track_handler(self):
        """Test that next track button handler calls audio player."""
        self.buttons._on_next_track(None)
        self.mock_player.next_track.assert_called_once()

    def test_prev_track_handler(self):
        """Test that previous track button handler calls audio player."""
        self.buttons._on_prev_track(None)
        self.mock_player.prev_track.assert_called_once()

    def test_error_handling_in_handlers(self):
        """Test that button handlers gracefully handle errors."""
        # Make audio player method raise an exception
        self.mock_player.toggle_pause.side_effect = Exception("Test error")

        # Handler should catch the exception and not crash
        try:
            self.buttons._on_play_pause(None)
        except Exception:
            self.fail("Button handler should catch exceptions")

    def test_cleanup(self):
        """Test that cleanup closes all buttons."""
        self.buttons.cleanup()

        # Verify all button close methods were called
        self.buttons.btn_play_pause.close.assert_called_once()
        self.buttons.btn_vol_up.close.assert_called_once()
        self.buttons.btn_vol_down.close.assert_called_once()
        self.buttons.btn_next.close.assert_called_once()
        self.buttons.btn_prev.close.assert_called_once()


if __name__ == '__main__':
    unittest.main()
