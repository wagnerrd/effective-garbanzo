# rfid_reader.py
import spidev
import time
from pirc522 import RFID
from config import PIN_RFID_RST

class Reader:
    def __init__(self):
        """
        Initializes the RFID reader using the Pi 5-compatible
        pirc522 library, which uses gpiozero for the reset pin.
        """
        self.rfid = None
        self.util = None
        self.last_uid = None
        
        try:
            # Initialize RFID reader with minimal parameters
            # pirc522 uses gpiozero internally and will handle pin allocation
            # Only specify the reset pin and SPI bus/device
            self.rfid = RFID(
                pin_rst=PIN_RFID_RST,
                bus=0,
                device=0
            )
            # Give the RFID module time to stabilize after initialization
            time.sleep(0.1)
            print("RFID Reader initialized successfully.")
            print(f"Using SPI bus 0, device 0, RST pin: {PIN_RFID_RST}")
            self.util = self.rfid.util()
            self.util.debug = False
        except Exception as e:
            print(f"Error initializing RFID reader: {e}")
            print("Have you enabled the SPI interface? (sudo raspi-config)")
            print("Check that the wiring is correct and the module has power.")

    def read_tag(self):
        """
        Polls for a new RFID tag.

        Returns:
            str: The tag UID if a *new* tag is detected.
            None: If no tag or the *same* tag is present.
        """
        if self.rfid is None:
            return None # Reader failed to init

        uid_str = None
        uid_bytes = None

        # 1. Request a tag
        # This is a non-blocking call
        (error, tag_type) = self.rfid.request()

        if not error:
            # 2. If a tag is present, get its UID
            (error, uid_list) = self.rfid.anticoll()

            if not error:
                # Convert the UID list [123, 45, 67, 89] to a string "123456789"
                uid_bytes = uid_list
                uid_str = "".join(map(str, uid_list))

                # CRITICAL: Stop crypto communication to ready the reader for next tag
                # Without this, the reader may get stuck and not detect new tags
                self.rfid.stop_crypto()

        # --- Logic to handle new vs. same tag ---

        if uid_str and uid_str != self.last_uid:
            # A *new* tag has been scanned
            self.last_uid = uid_str
            print(f"RFID: New tag detected with UID: {uid_str}")
            return uid_str
        elif not uid_str:
            # No tag is present, so reset the last_uid
            if self.last_uid is not None:
                print("RFID: Tag removed from reader")
            self.last_uid = None
            return None
        else:
            # The *same* tag is still on the reader, do nothing
            return None

    def cleanup(self):
        """
        Cleans up the GPIO and SPI resources.
        """
        if self.rfid:
            self.rfid.cleanup()
            print("RFID Reader resources cleaned up.")
