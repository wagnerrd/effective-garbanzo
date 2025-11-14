# rfid_reader.py
import spidev
import time
from pirc522 import RFID
from config import PIN_RFID_RST
import ndef

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

                # Read text payload from the tag
                self._read_text_payload(uid_list)

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

    def _read_text_payload(self, uid):
        """
        Reads and parses NDEF text payload from RFID tag.

        Args:
            uid: The UID list of the tag
        """
        # Default MIFARE key (factory default)
        default_key = [0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF]

        raw_data = bytearray()
        blocks_read = 0
        auth_failures = 0

        # Read blocks 1-3 from sector 0 (block 0 is manufacturer data, don't read it)
        # NDEF data often starts at block 1 or block 4
        error = self.rfid.card_auth(self.rfid.auth_a, 0, default_key, uid)
        if not error:
            for block_num in range(1, 4):  # Read blocks 1, 2, 3
                error, data = self.rfid.read(block_num)
                if not error and data:
                    raw_data.extend(data)
                    blocks_read += 1
        else:
            auth_failures += 1

        # Try to read from sectors 1-15
        # Each sector has 4 blocks, and the last block is the sector trailer (keys)
        for sector in range(1, 16):
            # Calculate the first block of this sector
            # Sectors 0-31: each has 4 blocks
            block_addr = sector * 4

            # Try to authenticate with key A
            error = self.rfid.card_auth(self.rfid.auth_a, block_addr, default_key, uid)

            if not error:
                # Read the first 3 blocks of this sector (skip the trailer block)
                for block_offset in range(3):
                    current_block = block_addr + block_offset
                    error, data = self.rfid.read(current_block)

                    if not error and data:
                        raw_data.extend(data)
                        blocks_read += 1
            else:
                auth_failures += 1

        print(f"RFID: Read {blocks_read} blocks from tag, {auth_failures} authentication failures")

        # Try to parse NDEF message from the raw data
        if raw_data:
            try:
                # NDEF messages typically start with 0x03 (NDEF Message TLV)
                # Find the NDEF message in the raw data
                ndef_start = -1
                for i in range(len(raw_data) - 1):
                    if raw_data[i] == 0x03:  # NDEF Message TLV
                        ndef_start = i
                        break

                if ndef_start >= 0:
                    # The byte after 0x03 is the length
                    ndef_length = raw_data[ndef_start + 1]
                    print(f"RFID: Found NDEF TLV at offset {ndef_start}, length: {ndef_length} bytes")

                    # Extract NDEF message data
                    ndef_data = raw_data[ndef_start + 2:ndef_start + 2 + ndef_length]

                    # Parse NDEF message
                    records = list(ndef.message_decoder(bytes(ndef_data)))
                    print(f"RFID: Decoded {len(records)} NDEF record(s)")

                    # Extract and print text records
                    text_found = False
                    for record in records:
                        if isinstance(record, ndef.TextRecord):
                            print(f"RFID: Text payload: {record.text}")
                            print(f"RFID: Text language: {record.language}")
                            text_found = True
                        elif hasattr(record, 'text'):
                            # Some NDEF implementations might use different record types
                            print(f"RFID: Text payload: {record.text}")
                            text_found = True
                        else:
                            print(f"RFID: Found non-text record: {type(record).__name__}")

                    if not text_found:
                        print(f"RFID: No text records found in NDEF message")
                else:
                    print("RFID: No NDEF TLV (0x03) marker found in tag data")
                    # Show first 64 bytes for debugging
                    preview = ' '.join(f'{b:02X}' for b in raw_data[:64])
                    print(f"RFID: First 64 bytes: {preview}")
            except Exception as e:
                print(f"RFID: Error parsing NDEF data: {e}")
                import traceback
                traceback.print_exc()
        else:
            print("RFID: No data could be read from tag (all blocks failed)")

    def cleanup(self):
        """
        Cleans up the GPIO and SPI resources.
        """
        if self.rfid:
            self.rfid.cleanup()
            print("RFID Reader resources cleaned up.")
