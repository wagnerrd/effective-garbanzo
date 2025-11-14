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
SUPPORTED_EXTENSIONS = ['.mp3', '.ogg', '.wav']

# Map RFID UIDs to sub-directory names
RFID_MEDIA_MAP = {
    '234876123': 'album-A',  # Will play all songs in 'media/album-A/'
    '987123456': 'album-B',  # Will play all songs in 'media/album-B/'
}

# Initial volume (from 0.0 to 1.0)
DEFAULT_VOLUME = 0.5