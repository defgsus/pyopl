import sys

from examples.tracker.ui.app import TrackerApp


def test_player():
    import time
    from examples.tracker.audio import Player
    from examples.tracker.data import Song
    player = Player(Song(), debug=True)
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
        TrackerApp().run()
    else:
        test_player()
