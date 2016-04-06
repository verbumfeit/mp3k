import random

from kivy.event import EventDispatcher
from kivy.properties import ListProperty, Logger


class Playlist(EventDispatcher):
    queue = ListProperty()
    shuffle = False
    repeat = False

    def _convert_track_to_queue_track(self, track):
        pass

    def add_track(self, track, position=False):
        Logger.info('Adding track to playlist: ' + track['title'])
        Logger.debug('Track type:' + str(type(track)))
        if position:
            self.queue.insert(position, track)
        else:
            self.queue.append(track)

        Logger.debug('Playlist length: ' + str(len(self.queue)))

    def add_track_and_set_current(self, track):
        self.add_track(track)
        self.set_current_track(len(self.queue) - 1)

    def remove_track(self, index):
        Logger.info('Removing track from playlist (Index: {})'.format(index))
        self.queue.pop(index)

    def move_track(self, old_index, new_index):
        track = self.queue.pop(old_index)
        self.queue.insert(new_index + 1, track)

    def get_previous_track(self):
        old_index, current_track = self.get_current_track()
        new_index = int(old_index) - 1

        if current_track:
            if new_index >= 0:
                idx, track = self.set_current_track(new_index)
                return track
            else:
                Logger.info('No previous track, playing first track of playlist')
                return None  # no previous tracks in playlist
        else:
            Logger.debug('Stopped playing because of error above')

    def get_start(self):
        if len(self.queue) > 0:
            idx, track = self.set_current_track(0)
            Logger.info('Starting playlist')
            return track
        else:
            Logger.info("Couldn't play, add tracks to playlist")
            return None

    def get_next_track(self):
        if self.shuffle:
            if len(self.queue) > 0:
                idx, track = self.set_current_track(random.randrange(0, len(self.queue)))  # return random index
                return track
            else:
                return None  # no tracks in playlist
        else:
            old_index, current_track = self.get_current_track()

            if current_track and old_index >= 0:   # -1 if track had no index property (error)(should be fixed / No track was playing
                new_index = int(old_index) + 1
                if new_index < len(self.queue):
                    idx, track = self.set_current_track(new_index)
                    return track
                else:
                    Logger.info('Reached end of playlist')
                    return None  # no more tracks in playlist
            else:
                Logger.debug('Stopped playing because of error above')
                return None

    def set_current_track(self, new_index):
        for track in self.queue:
            if 'playing' in track and track['playing']:
                track['playing'] = False
                break
        self.queue[new_index]['playing'] = True
        Logger.debug('set_current_track: Current track index set to ' + str(new_index))
        return new_index, self.queue[new_index]

    def get_current_track(self):
        for index, track in enumerate(self.queue):
            if 'playing' in track and track['playing']:
                # if 'index' in track:
                #     Logger.debug('get_current_track: Current track index is ' + str(track['index']))
                #     return track['index'], track
                # else:
                #     Logger.error('get_current_track: Current track has no index property')
                #     # TODO: Why does the track have no index? ListView problem of kivy?
                #     return -1, None

                Logger.debug('get_current_track: Current track index is ' + str(index))
                return index, track

        Logger.debug('No current track')
        return -1, None

    def clear(self):
        self.queue = []

    def get_queue(self):
        return self.queue
