# button_handler.py
from gpiozero import Button
from config import (
    PIN_PLAY_PAUSE,
    PIN_VOL_UP,
    PIN_VOL_DOWN,
    PIN_NEXT,
    PIN_PREV
)

class ButtonControls:
    """
    Manages all GPIO button inputs and links them to
    audio player actions.
    """
    def __init__(self, audio_player):
        """
        Initializes all buttons.
        
        Assumes buttons are wired between the GPIO pin and a GND pin.
        
        Args:
            audio_player: An instance of the AudioPlayer class.
        """
        # We pass the audio_player object in so we can link
        # its methods directly to the button press events.

        # Play/Pause Button
        self.btn_play_pause = Button(PIN_PLAY_PAUSE, pull_up=True, bounce_time=0.1)
        self.btn_play_pause.when_pressed = audio_player.toggle_pause

        # Volume Up Button
        self.btn_vol_up = Button(PIN_VOL_UP, pull_up=True, bounce_time=0.1)
        self.btn_vol_up.when_pressed = audio_player.volume_up

        # Volume Down Button
        self.btn_vol_down = Button(PIN_VOL_DOWN, pull_up=True, bounce_time=0.1)
        self.btn_vol_down.when_pressed = audio_player.volume_down
        
        # Next Track Button
        self.btn_next = Button(PIN_NEXT, pull_up=True, bounce_time=0.1)
        self.btn_next.when_pressed = audio_player.next_track
        
        # Previous Track Button
        self.btn_prev = Button(PIN_PREV, pull_up=True, bounce_time=0.1)
        self.btn_prev.when_pressed = audio_player.prev_track
        
        print("Button controls initialized and linked to audio player.")

        # Note: 'bounce_time=0.1' (100ms) is added to prevent
        # a single physical press from registering multiple times.