from gmusicapi import Mobileclient
from gmusicapi.exceptions import AlreadyLoggedIn
from kivy import Logger


class GoogleMusicApi:
    def __init__(self):
        self._api = Mobileclient()

    def login(self, username, password, device_id):
        try:
            return self._api.login(username, password, device_id)
        except AlreadyLoggedIn:
            Logger.debug('API: Already logged in')
            return True

    def logout(self):
        return self._api.logout()

    def get_stream_url(self, track_id, quality):
        return self._api.get_stream_url(song_id=track_id, quality=quality)

    def get_library(self):
        return self._api.get_all_songs()

    def get_album_info(self, album_id):
        return self._api.get_album_info(album_id)

    def search(self, query, max_results=25):
        # TODO: make number of results configurable / add to settings
        try:
            return self._api.search_all_access(query, max_results)
            # TODO: remove when gmusicapi 9.0.1 is stable
        except AttributeError:  # develop version of gmusicapi is installed
            return self._api.search(query, max_results)

    def get_station_tracks(self, title, seed, num_tracks=25, recently_played_ids=None):
        # TODO: make number of results configurable / add to settings
        # TODO: check for existing stations, so we don't always create new ones (maybe not necessary: stations created with same seed have the same id
        seed_type = seed['type']
        seed = seed['seed']
        station_id = ''
        Logger.debug('Station: Creating station (Title: {}, Seed: {}, Type:{}'.format(title, seed, seed_type))
        if seed_type == 'track':
            station_id = self.create_station(title, track_id=seed)
        elif seed_type == 'artist':
            station_id = self.create_station(title, artist_id=seed)
        elif seed_type == 'album':
            station_id = self.create_station(title, album_id=seed)
        elif seed_type == 'genre':
            station_id = self.create_station(title, genre_id=seed)
        elif seed_type == 'curated':
            Logger.debug("Station: CuratedStationId seed, don't know what to do :(")
        else:
            Logger.error("Station: Unknown seed, don't know what to do :(")

        if station_id:
            Logger.debug('Station: ID is ' + station_id)
            station_tracks = self._api.get_station_tracks(station_id, num_tracks, recently_played_ids)
            Logger.debug('Station: Station has {} tracks'.format(len(station_tracks)))
            return station_tracks
        else:
            Logger.warning("Station: Could not retrieve station ID")
            return []

    def get_feeling_lucky_station_tracks(self, num_tracks=25, recently_played_ids=None):
        # TODO: make number of results configurable / add to settings
        return self._api.get_station_tracks('IFL', num_tracks, recently_played_ids)

    def create_station(self, name, track_id=None, artist_id=None, album_id=None, genre_id=None, playlist_token=None):
        return self._api.create_station(name, track_id=track_id, artist_id=artist_id, album_id=album_id,
                                        genre_id=genre_id, playlist_token=playlist_token)