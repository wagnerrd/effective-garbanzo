# rfid_reader.py
import spidev
import time
from pirc522 import RFID
from config import (
    PIN_RFID_RST,
    TAG_TEXT_BLOCKS,
    TAG_AUTH_KEY,
    TAG_TEXT_ENCODING,
    TAG_NDEF_START_BLOCK,
    TAG_NDEF_BLOCK_COUNT
)

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

            # Attempt to read a plain-text payload from the configured data blocks.
            text_payload = self._read_text_payload(uid_bytes)
            if text_payload:
                print(f"RFID: Tag text payload -> \"{text_payload}\"")
            else:
                print("RFID: No text payload found (check text settings in config.py).")

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

    def _read_text_payload(self, uid_bytes):
        """
        Reads either a raw block payload or an NFC NDEF text record.
        """
        if not uid_bytes:
            return None

        if TAG_TEXT_BLOCKS:
            return self._read_raw_text_payload(uid_bytes)

        return self._read_ndef_text_payload(uid_bytes)

    def _read_raw_text_payload(self, uid_bytes):
        """
        Reads ASCII text stored directly in the provided blocks.
        """
        payload = self._read_blocks(uid_bytes, TAG_TEXT_BLOCKS)
        if not payload:
            return None

        decoded = payload.rstrip(b"\x00").decode(
            TAG_TEXT_ENCODING,
            errors="ignore"
        ).strip()

        return decoded or None

    def _read_ndef_text_payload(self, uid_bytes):
        """
        Reads a Well Known (T) text record from the NDEF message stored on the tag.
        """
        if TAG_NDEF_BLOCK_COUNT <= 0:
            return None

        block_range = list(range(
            TAG_NDEF_START_BLOCK,
            TAG_NDEF_START_BLOCK + TAG_NDEF_BLOCK_COUNT
        ))

        raw_bytes = self._read_blocks(uid_bytes, block_range)
        if not raw_bytes:
            return None

        # Parse TLV looking for the NDEF message (type 0x03).
        idx = 0
        while idx < len(raw_bytes):
            tlv_type = raw_bytes[idx]
            idx += 1

            if tlv_type == 0x00:
                # NULL TLV, skip
                continue
            if tlv_type == 0xFE:
                # Terminator TLV
                break
            if idx >= len(raw_bytes):
                break

            length = raw_bytes[idx]
            idx += 1

            if length == 0xFF:
                if idx + 1 >= len(raw_bytes):
                    break
                length = (raw_bytes[idx] << 8) + raw_bytes[idx + 1]
                idx += 2

            if tlv_type == 0x03:
                ndef_message = raw_bytes[idx:idx + length]
                return self._parse_ndef_text_record(ndef_message)

            idx += length

        return None

    def _read_blocks(self, uid_bytes, blocks):
        """
        Reads a list of blocks and returns their concatenated bytes.
        """
        if not blocks:
            return None

        payload = bytearray()

        try:
            self.rfid.select_tag(uid_bytes)
            if self.util:
                self.util.set_tag(uid_bytes)
                self.util.load_key(TAG_AUTH_KEY)

            for block in blocks:
                # Skip sector trailer blocks (every 4th block on MIFARE Classic 1K)
                if block >= 0 and (block + 1) % 4 == 0:
                    continue

                if self.util:
                    auth_error = self.util.auth(self.rfid.auth_a, block)
                    if auth_error:
                        print(f"RFID: Authentication failed for block {block}.")
                        return None

                (read_error, data) = self.rfid.read(block)
                if read_error:
                    print(f"RFID: Error reading block {block}.")
                    return None

                payload.extend(data)

            return bytes(payload)
        except Exception as e:
            print(f"RFID: Failed while reading blocks: {e}")
            return None
        finally:
            try:
                self.rfid.stop_crypto()
            except Exception:
                pass

    def _parse_ndef_text_record(self, ndef_message):
        """
        Extracts the text payload from the first NDEF Well Known Text record.
        """
        if not ndef_message:
            return None

        try:
            idx = 0
            header = ndef_message[idx]
            idx += 1
            sr = (header & 0x10) != 0  # Short Record flag
            il = (header & 0x08) != 0  # ID Length flag

            type_length = ndef_message[idx]
            idx += 1

            if sr:
                payload_length = ndef_message[idx]
                idx += 1
            else:
                payload_length = int.from_bytes(ndef_message[idx:idx + 4], "big")
                idx += 4

            if il:
                id_length = ndef_message[idx]
                idx += 1
            else:
                id_length = 0

            type_field = ndef_message[idx:idx + type_length]
            idx += type_length

            idx += id_length  # Skip ID field if present

            payload = ndef_message[idx:idx + payload_length]
            record_type = type_field.decode("ascii", errors="ignore")

            if record_type != "T" or not payload:
                return None

            status = payload[0]
            is_utf16 = (status & 0x80) != 0
            lang_length = status & 0x3F

            text_bytes = payload[1 + lang_length:]
            encoding = "utf-16" if is_utf16 else "utf-8"
            text = text_bytes.decode(encoding, errors="ignore").strip()

            return text or None
        except Exception as e:
            print(f"RFID: Failed to parse NDEF text record: {e}")
            return None

    def cleanup(self):
        """
        Cleans up the GPIO and SPI resources.
        """
        if self.rfid:
            self.rfid.cleanup()
            print("RFID Reader resources cleaned up.")
