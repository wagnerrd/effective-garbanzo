#!/usr/bin/env python3
"""
Test script for writing "Hello world" to an RFID tag.
Demonstrates the write_text method with verbose debugging output.
"""

import sys
import time
from pathlib import Path

# Add parent directory to path to import rfid_audio_player module
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.rfid_audio_player.rfid_reader import Reader


def main():
    """
    Main function to write 'Hello world' to an RFID tag.
    """
    print("=" * 60)
    print("RFID Tag Write Test Script")
    print("=" * 60)
    print()
    print("This script will write 'Hello world' to an RFID tag.")
    print("Verbose debugging information will be printed throughout.")
    print()

    # Initialize the RFID reader
    print("Step 1: Initializing RFID reader...")
    print("-" * 60)
    reader = Reader()
    print()

    if not reader.rfid:
        print("ERROR: Failed to initialize RFID reader!")
        print("Please ensure:")
        print("  - SPI is enabled on your Raspberry Pi")
        print("  - RC522 module is correctly wired")
        print("  - You have necessary permissions (may need sudo)")
        sys.exit(1)

    print("Step 2: Preparing to write text...")
    print("-" * 60)
    text_to_write = "Hello world"
    print(f"Text to write: '{text_to_write}'")
    print(f"Text length: {len(text_to_write)} characters")
    print(f"Text (UTF-8 bytes): {text_to_write.encode('utf-8').hex()}")
    print()

    print("Step 3: Place tag on reader now...")
    print("-" * 60)
    print("Waiting for tag to be placed on reader...")
    print("(Press Ctrl+C to cancel)")
    print()

    try:
        # Attempt to write the text
        print("Step 4: Writing to tag...")
        print("-" * 60)
        success = reader.write_text(text_to_write)
        print()

        if success:
            print("=" * 60)
            print("SUCCESS! Text written to tag successfully!")
            print("=" * 60)
            print()
            print("Step 5: Verifying write by reading back...")
            print("-" * 60)

            # Wait a moment for the tag to be ready
            time.sleep(0.5)

            # Try to read back the text
            print("Attempting to read the tag...")
            uid, text = reader.read_tag()

            if text:
                print(f"Read back text: '{text}'")
                if text == text_to_write:
                    print("VERIFICATION PASSED: Read text matches written text!")
                else:
                    print("WARNING: Read text does not match written text")
                    print(f"  Expected: '{text_to_write}'")
                    print(f"  Got:      '{text}'")
            else:
                print("WARNING: Could not read text from tag")
                print("(Remove and re-present the tag to trigger a read)")

        else:
            print("=" * 60)
            print("FAILED: Could not write text to tag")
            print("=" * 60)
            print()
            print("Troubleshooting tips:")
            print("  - Ensure tag is positioned correctly on reader")
            print("  - Try a different tag (must be NTAG215 or compatible)")
            print("  - Check that the tag is not write-protected")
            print("  - Verify wiring and SPI connection")
            sys.exit(1)

    except KeyboardInterrupt:
        print()
        print("Operation cancelled by user")
        sys.exit(0)
    except Exception as exc:
        print()
        print("=" * 60)
        print(f"ERROR: Unexpected exception occurred: {exc}")
        print("=" * 60)
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        print()
        print("Step 6: Cleaning up...")
        print("-" * 60)
        reader.cleanup()
        print()
        print("Done!")


if __name__ == "__main__":
    main()
