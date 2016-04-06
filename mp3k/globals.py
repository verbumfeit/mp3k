import os
import sys

from kivy.logger import Logger


class Globals:
    TESTING = False
    STARTED = False
    MPLAYER_PID = None
    MP3_PATH = None
    BUFFER_ITERATIONS = 1
    API = None
    CONFIG = None

    @staticmethod
    def get_valid_path(relative_path):
        system_path = relative_path.replace('/', os.sep)  # replace '/' separators with system separators
        absolute_path = os.path.realpath(sys.path[0] + os.sep + system_path)  # concat with path to script + separator
        Logger.debug('Globals: Constructed path ' + absolute_path)
        return absolute_path
