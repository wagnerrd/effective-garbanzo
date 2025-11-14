# main.py
import time
from src.rfid_audio_player import AudioPlayer, Reader, ButtonControls, WebServer

if __name__ == "__main__":
    """
    Main application entry point.
    Initializes all components and runs the main loop.
    """
    
    # Initialize components
    player = None
    reader = None
    buttons = None
    web_server = None

    try:
        # 1. Initialize the core components
        print("🎵 Initializing PhonieBox Minimal...")
        player = AudioPlayer()
        reader = Reader()

        # 2. Initialize the button handler and pass it the player
        #    This automatically links all button events.
        buttons = ButtonControls(player)

        # 3. Initialize and start the web server
        web_server = WebServer(player, reader)
        web_server.run(host='0.0.0.0', port=5000)

        print("\n" + "="*50)
        print("  🎵 PhonieBox Minimal is RUNNING 🎵")
        print("="*50)
        print("📡 Waiting for an RFID tag...")
        print("🎮 Button controls are active")
        print("🛑 Press Ctrl+C to exit")
        print("="*50 + "\n")

        # 4. Start the main application loop
        while True:
            # Check for a new RFID tag.
            # The reader.read_tag() method is smart and will
            # only return a UID once when a *new* tag is presented.
            uid, text = reader.read_tag()
            
            if uid:
                print(f"Main loop detected new UID: {uid}, text {text}")
                player.load_playlist(text)
            
            # Check if the current song has finished playing.
            # This is necessary for auto-playing the next track.
            player.check_for_song_end()

            # Poll every 100ms. This is idle time, preventing
            # the loop from using 100% CPU.
            time.sleep(0.5)

    except KeyboardInterrupt:
        print("\n\n🛑 Shutting down... (Ctrl+C pressed)")

    finally:
        # 5. Clean up resources
        print("\n🧹 Cleaning up resources...")
        if player:
            player.quit()
            print("  ✓ Audio player shut down")
        if reader:
            reader.cleanup()
            print("  ✓ RFID reader cleaned up")
        if buttons:
            buttons.cleanup()
        print("\n👋 Goodbye!")