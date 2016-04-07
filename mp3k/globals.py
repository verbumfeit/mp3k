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
        # concat path to script + separator + relative path and make a real path (no .. and system specific separators)
        absolute_path = os.path.realpath(sys.path[0] + os.sep + relative_path)
        Logger.debug('Globals: Constructed path ' + absolute_path)
        return absolute_path
