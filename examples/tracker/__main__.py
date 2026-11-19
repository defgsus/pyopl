import sys

from examples.tracker.ui.app import TrackerApp
from examples.tracker.data import Song
from examples.tracker.test1 import create_song

def test_player():
    import time
    from examples.tracker.audio import Player
    song = create_song()
    player = Player(song, debug=True)
    player.start_audio()
    try:
        player.play()
        time.sleep(10000)
    except KeyboardInterrupt:
        pass
    finally:
        player.stop_audio()


if __name__ == "__main__":
    if len(sys.argv) <= 1:
        #song = Song()
        #song.make_demo_song()
        song = create_song()
        TrackerApp(song).run()
    else:
        test_player()
