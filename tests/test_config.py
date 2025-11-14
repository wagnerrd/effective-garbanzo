"""Tests for configuration module."""

import unittest
from src.rfid_audio_player import config


class TestConfig(unittest.TestCase):
    """Test configuration values are properly defined."""

    def test_gpio_pins_defined(self):
        """Test that all GPIO pins are defined."""
        self.assertIsInstance(config.PIN_PLAY_PAUSE, int)
        self.assertIsInstance(config.PIN_VOL_UP, int)
        self.assertIsInstance(config.PIN_VOL_DOWN, int)
        self.assertIsInstance(config.PIN_NEXT, int)
        self.assertIsInstance(config.PIN_PREV, int)
        self.assertIsInstance(config.PIN_RFID_RST, int)

    def test_gpio_pins_valid_range(self):
        """Test that GPIO pins are in valid BCM range (0-27 for most Pi models)."""
        pins = [
            config.PIN_PLAY_PAUSE,
            config.PIN_VOL_UP,
            config.PIN_VOL_DOWN,
            config.PIN_NEXT,
            config.PIN_PREV,
            config.PIN_RFID_RST,
        ]
        for pin in pins:
            self.assertGreaterEqual(pin, 0)
            self.assertLessEqual(pin, 27)

    def test_media_path_defined(self):
        """Test that media path is defined."""
        self.assertIsInstance(config.MEDIA_PATH, str)
        self.assertTrue(len(config.MEDIA_PATH) > 0)

    def test_supported_extensions(self):
        """Test that supported audio extensions are defined."""
        self.assertIsInstance(config.SUPPORTED_EXTENSIONS, list)
        self.assertTrue(len(config.SUPPORTED_EXTENSIONS) > 0)
        # All extensions should start with a dot
        for ext in config.SUPPORTED_EXTENSIONS:
            self.assertTrue(ext.startswith('.'))

    def test_default_volume_range(self):
        """Test that default volume is in valid range (0.0 to 1.0)."""
        self.assertIsInstance(config.DEFAULT_VOLUME, float)
        self.assertGreaterEqual(config.DEFAULT_VOLUME, 0.0)
        self.assertLessEqual(config.DEFAULT_VOLUME, 1.0)

    def test_rfid_tag_settings(self):
        """Test RFID tag writing settings are defined."""
        self.assertIsInstance(config.TAG_NDEF_START_PAGE, int)
        self.assertIsInstance(config.TAG_NDEF_PAGE_COUNT, int)
        self.assertGreater(config.TAG_NDEF_START_PAGE, 0)
        self.assertGreater(config.TAG_NDEF_PAGE_COUNT, 0)


if __name__ == '__main__':
    unittest.main()
