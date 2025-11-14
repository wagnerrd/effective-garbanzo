"""Tests for RFID Reader module."""

import unittest
from unittest.mock import patch, MagicMock


class TestRFIDReader(unittest.TestCase):
    """Test RFID Reader functionality."""

    @patch('src.rfid_audio_player.rfid_reader.RFID')
    def setUp(self, mock_rfid_class):
        """Set up test fixtures."""
        # Mock the RFID hardware interface
        self.mock_rfid = MagicMock()
        mock_rfid_class.return_value = self.mock_rfid

        from src.rfid_audio_player import Reader
        self.reader = Reader()

    def test_initialization(self):
        """Test that Reader initializes correctly."""
        self.assertIsNotNone(self.reader.rfid)
        self.assertIsNone(self.reader.last_uid)

    def test_read_tag_returns_none_when_no_tag(self):
        """Test that read_tag returns None when no tag is present."""
        # Mock no tag detected
        self.mock_rfid.request.return_value = (True, None)  # Error

        uid, text = self.reader.read_tag()

        self.assertIsNone(uid)
        self.assertIsNone(text)

    def test_read_tag_detects_new_tag(self):
        """Test that read_tag detects a new tag."""
        # Mock successful tag detection
        self.mock_rfid.request.return_value = (False, None)
        self.mock_rfid.anticoll.return_value = (False, [1, 2, 3, 4, 5])
        self.mock_rfid.stop_crypto.return_value = None

        uid, text = self.reader.read_tag()

        # Should return UID (text may be None if NDEF reading is mocked to fail)
        self.assertIsNotNone(uid)
        self.assertEqual(uid, '12345')

    def test_read_tag_ignores_repeated_tag(self):
        """Test that the same tag is only reported once."""
        # Mock successful tag detection
        self.mock_rfid.request.return_value = (False, None)
        self.mock_rfid.anticoll.return_value = (False, [1, 2, 3, 4, 5])
        self.mock_rfid.stop_crypto.return_value = None

        # First read should return the UID
        uid1, text1 = self.reader.read_tag()
        self.assertIsNotNone(uid1)

        # Second read with same tag should return None (tag not new)
        uid2, text2 = self.reader.read_tag()
        self.assertIsNone(uid2)
        self.assertIsNone(text2)

    def test_read_tag_detects_tag_removal(self):
        """Test that tag removal is detected."""
        # First, detect a tag
        self.mock_rfid.request.return_value = (False, None)
        self.mock_rfid.anticoll.return_value = (False, [1, 2, 3, 4, 5])
        self.mock_rfid.stop_crypto.return_value = None

        self.reader.read_tag()
        self.assertEqual(self.reader.last_uid, '12345')

        # Now simulate tag removal
        self.mock_rfid.request.return_value = (True, None)  # Error (no tag)

        uid, text = self.reader.read_tag()

        # Should clear last_uid
        self.assertIsNone(self.reader.last_uid)
        self.assertIsNone(uid)

    def test_cleanup(self):
        """Test that cleanup is called on the RFID object."""
        self.reader.cleanup()
        self.mock_rfid.cleanup.assert_called_once()


class TestNDEFParsing(unittest.TestCase):
    """Test NDEF message parsing."""

    @patch('src.rfid_audio_player.rfid_reader.RFID')
    def setUp(self, mock_rfid_class):
        """Set up test fixtures."""
        self.mock_rfid = MagicMock()
        mock_rfid_class.return_value = self.mock_rfid

        from src.rfid_audio_player import Reader
        self.reader = Reader()

    def test_parse_text_record_with_valid_data(self):
        """Test parsing a valid NDEF text record."""
        # Simple NDEF Text Record: "Hi"
        # Header: 0xD1 (MB=1, ME=1, SR=1, TNF=1)
        # Type length: 0x01
        # Payload length: 0x03
        # Type: 'T' (0x54)
        # Payload: status byte (0x02 = UTF-8, 2-char lang code) + 'en' + 'Hi'
        message = bytes([
            0xD1,  # Header
            0x01,  # Type length
            0x05,  # Payload length
            0x54,  # Type 'T'
            0x02,  # Status (UTF-8, lang length 2)
            0x65, 0x6E,  # 'en'
            0x48, 0x69   # 'Hi'
        ])

        text = self.reader._parse_text_record(message)

        self.assertEqual(text, 'Hi')

    def test_parse_text_record_with_empty_message(self):
        """Test parsing an empty NDEF message."""
        text = self.reader._parse_text_record(bytes())
        self.assertIsNone(text)

    def test_parse_text_record_with_invalid_type(self):
        """Test parsing a non-text NDEF record."""
        # URI record instead of Text
        message = bytes([
            0xD1,  # Header
            0x01,  # Type length
            0x01,  # Payload length
            0x55,  # Type 'U' (URI, not Text)
            0x00   # Payload
        ])

        text = self.reader._parse_text_record(message)
        self.assertIsNone(text)


if __name__ == '__main__':
    unittest.main()
