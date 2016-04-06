import json
import os

from kivy.logger import Logger

from globals import Globals


class History:

    def __init__(self):
        self.history_path = Globals.get_valid_path('history.json')
        if os.path.isfile(self.history_path):
            self._history = self.load_history()
            self.playlist_history = self._history['playlist']
        else:
            self._history = {'playlist': []}
            self.playlist_history = self._history['playlist']

    def load_history(self):
        with open(self.history_path) as history_file:
            history = json.load(history_file)
            return history

    def save_to_history(self, category, content):
        if category == 'playlist':
            Logger.debug('History: Saving playlist')
            self.playlist_history = content

    def write_history(self):
        Logger.debug('History: Writing to history')
        self._history['playlist'] = self.playlist_history
        with open(self.history_path, 'w') as outfile:
            json.dump(self._history, outfile)
