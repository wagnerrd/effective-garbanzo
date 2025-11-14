# config.py

# GPIO Pin definitions (BCM)
PIN_PLAY_PAUSE = 5
PIN_VOL_UP = 6
PIN_VOL_DOWN = 12
PIN_NEXT = 16
PIN_PREV = 26

# RFID Reset Pin (physical)
PIN_RFID_RST = 22

# --- Audio Player Settings ---

# Path to your media parent directory
MEDIA_PATH = "media/"

# Supported audio file extensions
SUPPORTED_EXTENSIONS = ['.mp3', '.ogg', '.wav', '.m4a']

# Map RFID UIDs to sub-directory names
RFID_MEDIA_MAP = {
    '1364185516': 'Spiderman',  # Will play all songs in 'media/album-A/'
    '987123456': 'album-B',  # Will play all songs in 'media/album-B/'
}

# Initial volume (from 0.0 to 1.0)
DEFAULT_VOLUME = 0.5

# --- RFID Tag Text Settings ---

# Configure how we extract text from the tag. When TAG_TEXT_BLOCKS is empty
# we will read an NFC Forum NDEF text record from the configured block range.
TAG_TEXT_BLOCKS = []

# Block range (inclusive start, number of blocks) that stores the TLV/NDEF data.
# Most smartphone-written NTAG/MIFARE Classic tags put NDEF at block 4 onwards.
TAG_NDEF_START_BLOCK = 4
TAG_NDEF_BLOCK_COUNT = 16

# Authentication key used for MIFARE Classic blocks (default factory key).
TAG_AUTH_KEY = [0xFF] * 6

# Encoding to use when decoding direct block payloads.
TAG_TEXT_ENCODING = "utf-8"
