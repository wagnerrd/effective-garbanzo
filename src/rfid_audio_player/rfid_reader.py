# rfid_reader.py
import time
from typing import List, Optional

from pirc522 import RFID

from .config import (
    PIN_RFID_RST,
    TAG_NDEF_START_PAGE,
    TAG_NDEF_PAGE_COUNT,
)


class Reader:
    """
    Thin wrapper around the pi-rc522 driver that handles UID polling and
    optionally extracts a text payload from the NFC NDEF message stored
    on the card.
    """

    def __init__(self):
        self.rfid: Optional[RFID] = None
        self.last_uid: Optional[str] = None

        try:
            self.rfid = RFID(pin_rst=PIN_RFID_RST, bus=0, device=0)
            time.sleep(0.1)  # Allow the RC522 to stabilise.
            print("RFID reader initialised (SPI bus 0, device 0)")
        except Exception as exc:
            print(f"Error initialising RFID reader: {exc}")
            print("Ensure SPI is enabled and the RC522 is wired correctly.")

    def read_tag(self) -> tuple[Optional[str], Optional[str]]:
        """
        Polls for a new RFID tag, returning its UID string the first time
        it is presented. Repeats are ignored until the card is removed.
        """
        if not self.rfid:
            return None, None

        uid_str = None
        uid_bytes: Optional[List[int]] = None

        (error, _) = self.rfid.request()
        if not error:
            (error, uid) = self.rfid.anticoll()
            if not error:
                uid_bytes = uid
                uid_str = "".join(map(str, uid))
                self.rfid.stop_crypto()

        if uid_str and uid_str != self.last_uid:
            self.last_uid = uid_str
            print(f"RFID: New tag detected with UID {uid_str}")

            text_payload = self._read_ndef_text(uid_bytes)

            return uid_str, text_payload

        if not uid_str:
            if self.last_uid is not None:
                print("RFID: Tag removed from reader")
            self.last_uid = None

        return None, None

    def _read_ndef_text(self, uid_bytes: Optional[List[int]]) -> Optional[str]:
        """
        Reads NDEF TLV bytes from the configured block range and attempts
        to extract the first Well-Known Text record.
        """
        if not self.rfid or not uid_bytes or TAG_NDEF_PAGE_COUNT <= 0:
            return None

        raw_bytes = self._read_pages(
            uid_bytes,
            TAG_NDEF_START_PAGE,
            TAG_NDEF_PAGE_COUNT
        )
        if not raw_bytes:
            return None

        tlv_idx = 0
        while tlv_idx < len(raw_bytes):
            tlv_type = raw_bytes[tlv_idx]
            tlv_idx += 1

            if tlv_type == 0x00:
                continue  # NULL TLV
            if tlv_type == 0xFE:
                break  # Terminator TLV
            if tlv_idx >= len(raw_bytes):
                break

            length = raw_bytes[tlv_idx]
            tlv_idx += 1
            if length == 0xFF:
                if tlv_idx + 1 >= len(raw_bytes):
                    break
                length = (raw_bytes[tlv_idx] << 8) + raw_bytes[tlv_idx + 1]
                tlv_idx += 2

            if tlv_type == 0x03:
                ndef_message = raw_bytes[tlv_idx:tlv_idx + length]
                return self._parse_text_record(ndef_message)

            tlv_idx += length

        return None

    def _read_pages(self, uid_bytes: List[int], start_page: int, page_count: int) -> Optional[bytes]:
        """
        Reads raw bytes from NTAG-style tags (4 bytes per page, read in
        16-byte chunks). No authentication required for default tags.
        """
        if page_count <= 0:
            return None

        payload = bytearray()
        current_page = start_page
        final_page = start_page + page_count

        while current_page < final_page:
            if self.rfid is None:
                return None
            error, data = self.rfid.read(current_page)
            if error:
                print(f"RFID: Error reading starting at page {current_page}.")
                return None

            payload.extend(data)
            current_page += 4  # read command returns 4 pages (16 bytes)

        return bytes(payload[:page_count * 4])

    def _parse_text_record(self, message: bytes) -> Optional[str]:
        """
        Parses the first Well Known 'T' record contained in the NDEF message.
        """
        if not message:
            return None

        try:
            idx = 0
            header = message[idx]
            idx += 1

            sr = (header & 0x10) != 0
            il = (header & 0x08) != 0

            type_length = message[idx]
            idx += 1

            if sr:
                payload_length = message[idx]
                idx += 1
            else:
                payload_length = int.from_bytes(message[idx:idx + 4], "big")
                idx += 4

            if il:
                id_length = message[idx]
                idx += 1
            else:
                id_length = 0

            record_type = message[idx:idx + type_length]
            idx += type_length
            idx += id_length

            payload = message[idx:idx + payload_length]

            if record_type.decode("ascii", errors="ignore") != "T" or not payload:
                return None

            status = payload[0]
            is_utf16 = (status & 0x80) != 0
            lang_length = status & 0x3F

            text_bytes = payload[1 + lang_length:]
            encoding = "utf-16" if is_utf16 else "utf-8"
            text = text_bytes.decode(encoding, errors="ignore").strip()
            return text or None
        except Exception as exc:
            print(f"RFID: Failed to parse NDEF text record: {exc}")
            return None

    def write_text_to_tag(self, text: str) -> tuple[bool, str]:
        """
        Writes an NDEF text record to the currently present tag.
        Returns (success, message) tuple.
        """
        if not self.rfid:
            return False, "RFID reader not initialized"

        if not text:
            return False, "Text payload cannot be empty"

        # First, detect the tag
        (error, _) = self.rfid.request()
        if error:
            return False, "No tag detected. Please place a tag on the reader."

        (error, uid) = self.rfid.anticoll()
        if error:
            return False, "Failed to read tag UID"

        try:
            # Create NDEF text record
            ndef_record = self._create_ndef_text_record(text)
            if not ndef_record:
                return False, "Failed to create NDEF record"

            # Wrap in TLV structure
            tlv_data = self._create_tlv_structure(ndef_record)

            # Write to tag
            success = self._write_pages(uid, TAG_NDEF_START_PAGE, tlv_data)

            self.rfid.stop_crypto()

            if success:
                print(f"RFID: Successfully wrote text '{text}' to tag")
                return True, f"Successfully wrote '{text}' to tag"
            else:
                return False, "Failed to write data to tag"

        except Exception as exc:
            print(f"RFID: Error writing to tag: {exc}")
            return False, f"Error writing to tag: {str(exc)}"

    def _create_ndef_text_record(self, text: str, language: str = "en") -> Optional[bytes]:
        """
        Creates an NDEF Well-Known Text record from the given text.
        """
        try:
            # Encode text as UTF-8
            text_bytes = text.encode("utf-8")

            # Status byte: UTF-8 (bit 7 = 0) + language code length
            status_byte = len(language) & 0x3F

            # Payload: status + language code + text
            payload = bytes([status_byte]) + language.encode("ascii") + text_bytes
            payload_length = len(payload)

            # Record header
            # MB=1 (Message Begin), ME=1 (Message End), CF=0, SR=1 (Short Record), IL=0, TNF=0x01 (Well-Known)
            header = 0xD1  # 11010001

            # Type length (1 byte for "T")
            type_length = 1

            # Build the NDEF record
            record = bytes([
                header,
                type_length,
                payload_length,
                ord('T')  # Type: Text
            ]) + payload

            return record

        except Exception as exc:
            print(f"RFID: Failed to create NDEF text record: {exc}")
            return None

    def _create_tlv_structure(self, ndef_message: bytes) -> bytes:
        """
        Wraps the NDEF message in a TLV (Type-Length-Value) structure.
        """
        ndef_length = len(ndef_message)

        # TLV: Type (0x03 = NDEF Message), Length, Value, Terminator (0xFE)
        if ndef_length < 255:
            # Short form
            tlv = bytes([0x03, ndef_length]) + ndef_message + bytes([0xFE])
        else:
            # Long form (3-byte length)
            tlv = bytes([0x03, 0xFF, (ndef_length >> 8) & 0xFF, ndef_length & 0xFF]) + ndef_message + bytes([0xFE])

        # Pad to multiple of 4 bytes (page size)
        padding_needed = (4 - (len(tlv) % 4)) % 4
        tlv += bytes([0x00] * padding_needed)

        return tlv

    def _write_pages(self, uid: List[int], start_page: int, data: bytes) -> bool:
        """
        Writes data to NTAG-style tags (4 bytes per page).
        """
        if not self.rfid:
            return False

        # Calculate how many pages we need
        pages_needed = (len(data) + 3) // 4  # Round up

        # Check if we have enough space
        if pages_needed > TAG_NDEF_PAGE_COUNT:
            print(f"RFID: Data too large ({len(data)} bytes, need {pages_needed} pages, only {TAG_NDEF_PAGE_COUNT} available)")
            return False

        # Write data page by page
        for i in range(pages_needed):
            page_num = start_page + i
            offset = i * 4
            page_data = list(data[offset:offset + 4])

            # Pad if necessary
            while len(page_data) < 4:
                page_data.append(0x00)

            # For NTAG tags, use util_write instead of write
            # util_write is for Mifare Ultralight/NTAG tags
            if hasattr(self.rfid, 'util_write'):
                error = self.rfid.util_write(page_num, page_data)
            else:
                error = self.rfid.write(page_num, page_data)

            if error:
                print(f"RFID: Error writing to page {page_num}")
                return False
            print(f"RFID: Successfully wrote page {page_num}")

        return True

    def cleanup(self):
        if self.rfid:
            self.rfid.cleanup()
            print("RFID reader resources cleaned up.")
