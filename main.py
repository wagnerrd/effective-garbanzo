# main.py
import time
from audio_player import AudioPlayer
from rfid_reader import Reader
from button_handler import ButtonControls

if __name__ == "__main__":
    """
    Main application entry point.
    Initializes all components and runs the main loop.
    """
    
    # Initialize components
    player = None
    reader = None
    
    try:
        # 1. Initialize the core components
        player = AudioPlayer()
        reader = Reader()
        
        # 2. Initialize the button handler and pass it the player
        #    This automatically links all button events.
        buttons = ButtonControls(player) 

        print("\n---------------------------------")
        print(" PhonieBox Minimal is RUNNING")
        print(" Waiting for an RFID tag...")
        print(" (Press Ctrl+C to exit)")
        print("---------------------------------")

        # 3. Start the main application loop
        while True:
            # Check for a new RFID tag.
            # The reader.read_tag() method is smart and will
            # only return a UID once when a *new* tag is presented.
            uid = reader.read_tag()
            
            if uid:
                print(f"Main loop detected new UID: {uid}")
                player.load_playlist(uid)
            
            # Check if the current song has finished playing.
            # This is necessary for auto-playing the next track.
            player.check_for_song_end()

            # Poll every 100ms. This is idle time, preventing
            # the loop from using 100% CPU.
            time.sleep(0.1)

    except KeyboardInterrupt:
        print("\nShutting down... (Ctrl+C pressed)")
    
    finally:
        # 4. Clean up resources
        if player:
            player.quit()
        if reader:
            reader.cleanup()
        print("Goodbye.")