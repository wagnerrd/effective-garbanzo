# config.py

# GPIO Pin definitions (BCM)
PIN_PLAY_PAUSE = 27
PIN_VOL_UP = 22
PIN_VOL_DOWN = 23
PIN_NEXT = 16
PIN_PREV = 26

# RFID Reset Pin (physical)
PIN_RFID_RST = 22

# --- Audio Player Settings ---

# Path to your media parent directory
MEDIA_PATH = "media/"

# Supported audio file extensions
SUPPORTED_EXTENSIONS = ['.mp3', '.ogg', '.wav']

# Map RFID UIDs to sub-directory names
RFID_MEDIA_MAP = {
    '1364185516': 'Spiderman',  # Will play all songs in 'media/album-A/'
    '987123456': 'album-B',  # Will play all songs in 'media/album-B/'
}

# Initial volume (from 0.0 to 1.0)
DEFAULT_VOLUME = 0.5

# --- RFID Tag Writing Settings ---

# Starting block for NDEF data (block 4 is first user data block after manufacturer sector)
TAG_NDEF_START_BLOCK = 4

# Number of blocks to write (covers multiple sectors for larger payloads)
TAG_NDEF_BLOCK_COUNT = 16

# Default MIFARE authentication key (factory default is all 0xFF)
TAG_AUTH_KEY = [0xD3, 0xF7, 0xD3, 0xF7, 0xD3, 0xF7]
