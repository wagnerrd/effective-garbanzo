#!/usr/bin/env python3
"""
Diagnostic script for WS2812/NeoPixel rings.

Cycles through a rainbow animation so you can verify wiring, power,
and pixel integrity. Uses the LED settings from config.py.
"""

import argparse
import sys
import time
from pathlib import Path

# Ensure project root is on sys.path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from rpi_ws281x import PixelStrip, Color
from src.rfid_audio_player.config import LED_PIN, LED_COUNT, LED_BRIGHTNESS

LED_FREQ_HZ = 800000
LED_DMA = 10
LED_INVERT = False
LED_CHANNEL = 0


def color_wheel(pos: int) -> Color:
    """Generate rainbow colors across 0-255 positions."""
    pos = pos % 256
    if pos < 85:
        return Color(pos * 3, 255 - pos * 3, 0)
    if pos < 170:
        pos -= 85
        return Color(255 - pos * 3, 0, pos * 3)
    pos -= 170
    return Color(0, pos * 3, 255 - pos * 3)


def rainbow_cycle(strip: PixelStrip, wait_ms: int = 20, iterations: int = 3) -> None:
    """Display rainbow colors that uniformly spread across pixels."""
    for j in range(256 * iterations):
        for i in range(strip.numPixels()):
            strip.setPixelColor(i, color_wheel((i * 256 // strip.numPixels()) + j))
        strip.show()
        time.sleep(wait_ms / 1000.0)


def pulse_each_color(strip: PixelStrip, hold_s: float = 0.5) -> None:
    """Light solid red, green, blue, and white for quick verification."""
    colors = [
        ("Red", Color(255, 0, 0)),
        ("Green", Color(0, 255, 0)),
        ("Blue", Color(0, 0, 255)),
        ("White", Color(255, 255, 255)),
    ]
    for name, color in colors:
        print(f"Showing {name}")
        for i in range(strip.numPixels()):
            strip.setPixelColor(i, color)
        strip.show()
        time.sleep(hold_s)


def parse_args():
    parser = argparse.ArgumentParser(description="WS2812 diagnostic animation")
    parser.add_argument(
        "--iterations",
        type=int,
        default=3,
        help="Number of rainbow cycles to run (default: 3)"
    )
    parser.add_argument(
        "--brightness",
        type=float,
        default=LED_BRIGHTNESS,
        help="Brightness between 0.0 and 1.0 (default from config.py)"
    )
    parser.add_argument(
        "--led-count",
        type=int,
        default=LED_COUNT,
        help="Number of LEDs in the ring (default from config.py)"
    )
    parser.add_argument(
        "--pin",
        type=int,
        default=LED_PIN,
        help="BCM pin connected to DIN (default from config.py)"
    )
    return parser.parse_args()


def main():
    args = parse_args()
    brightness = int(max(0.0, min(1.0, args.brightness)) * 255)
    strip = PixelStrip(
        args.led_count,
        args.pin,
        LED_FREQ_HZ,
        LED_DMA,
        LED_INVERT,
        brightness,
        LED_CHANNEL
    )

    strip.begin()
    print(f"Running diagnostic on GPIO{args.pin} with {args.led_count} LEDs...")

    try:
        pulse_each_color(strip)
        rainbow_cycle(strip, iterations=args.iterations)
    except KeyboardInterrupt:
        print("\nInterrupted. Turning LEDs off.")
    finally:
        for i in range(strip.numPixels()):
            strip.setPixelColor(i, Color(0, 0, 0))
        strip.show()


if __name__ == "__main__":
    main()
