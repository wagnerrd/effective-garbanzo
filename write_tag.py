import time
from typing import List, Tuple

from pirc522 import RFID

from config import (
    PIN_RFID_RST,
    TAG_NDEF_START_PAGE,
    TAG_NDEF_PAGE_COUNT,
)

PAGE_SIZE = 4  # NTAG pages contain 4 bytes


def build_text_ndef_tlv(text: str, language: str = "en") -> bytes:
    """Builds a minimal NFC Forum NDEF text record TLV payload."""
    text_bytes = text.encode("utf-8")
    lang_bytes = language.encode("ascii")

    status = len(lang_bytes) & 0x3F  # UTF-8, language length in lower 6 bits
    payload = bytes([status]) + lang_bytes + text_bytes

    ndef_record = bytes([
        0xD1,  # MB=1, ME=1, SR=1, TNF=0x01 (Well Known)
        0x01,  # Type length
        len(payload),  # Payload length (SR so single byte)
        0x54,  # 'T' type
    ]) + payload

    return bytes([0x03, len(ndef_record)]) + ndef_record + bytes([0xFE])


def build_page_payloads(text: str) -> List[Tuple[int, bytes]]:
    """
    Generates (page_number, 4-byte data) tuples spanning the configured NDEF range.
    """
    tlv = build_text_ndef_tlv(text)
    total_bytes = TAG_NDEF_PAGE_COUNT * PAGE_SIZE
    buffer = bytearray(total_bytes)
    buffer[:len(tlv)] = tlv

    payloads = []
    offset = 0
    for page in range(TAG_NDEF_START_PAGE, TAG_NDEF_START_PAGE + TAG_NDEF_PAGE_COUNT):
        chunk = buffer[offset:offset + PAGE_SIZE]
        if len(chunk) < PAGE_SIZE:
            chunk = chunk + bytes(PAGE_SIZE - len(chunk))
        payloads.append((page, bytes(chunk)))
        offset += PAGE_SIZE

    return payloads


def _write_page(rfid: RFID, page: int, data: bytes) -> bool:
    """
    Issues the NTAG WRITE (0xA2) command for a single 4-byte page.
    Returns True on success.
    """
    frame = [0xA2, page] + list(data[:PAGE_SIZE])
    crc = rfid.calculate_crc(frame)
    frame.extend(crc)
    error, back_data, back_length = rfid.card_write(rfid.mode_transrec, frame)
    if error:
        return False
    return back_length == 4 and (back_data[0] & 0x0F) == 0x0A


def write_text_to_tag(text: str):
    """Waits for a tag and programs it with the provided text."""
    rfid = RFID(pin_rst=PIN_RFID_RST, bus=0, device=0)
    page_payloads = build_page_payloads(text)

    print("=" * 60)
    print("RFID Text Writer")
    print("Place a tag on the reader to write the word 'Awesome'.")
    print("Press Ctrl+C to exit without writing.")
    print("=" * 60)

    try:
        while True:
            (error, _) = rfid.request()
            if error:
                time.sleep(0.1)
                continue

            (error, uid) = rfid.anticoll()
            if error:
                time.sleep(0.1)
                continue

            print(f"Tag detected UID: {''.join(map(str, uid))}")
            success = True

            for page, data in page_payloads:
                if not _write_page(rfid, page, data):
                    print(f"Write failed for page {page}.")
                    success = False
                    break

            if success:
                print("✓ Tag programmed with text: 'Awesome'")
            else:
                print("✗ Failed to program the tag.")
            break

    except KeyboardInterrupt:
        print("\nOperation cancelled.")
    finally:
        rfid.cleanup()


if __name__ == "__main__":
    write_text_to_tag("Awesome")
