from kivy.logger import Logger

from mp3kapp import MP3kApp
from player import Player

if __name__ == '__main__':
    try:
        app = MP3kApp().run()
    except KeyboardInterrupt:
        Logger.info('User interruption..Shutting down')
        Player.kill_mplayer()
