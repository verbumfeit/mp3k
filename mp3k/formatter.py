from kivy.logger import Logger


class Formatter:

    def format_albums_list(self, albums):
        albums_formatted = []
        for index, album in enumerate(albums):
            albums_formatted.append({
                'title': album['name'],
                'album_id': album['albumId'],
                'album_image_url': album['albumArtRef'],
                'year': album['year'],
                'album_artist': album['albumArtist'],
                'artist': album['artist'],
                'artist_id': album['artistId'][0],
            })
        return albums_formatted

    def format_stations_list(self, stations):
        stations_formatted = []
        for index, station in enumerate(stations):
            seed = self.get_station_seed(station['seed'])
            stations_formatted.append({
                'title': station['name'],
                'description': station['description'] if 'description' in station else self.generate_station_description(
                    seed['type']),
                'seed': seed,
                'image_url_square': self.get_station_image_url(station),
            # image will be composed if station is curated, otherwise it's the artist/track image
                'image_url_wide': station['compositeArtRef'][1]['url'] if 'compositeArtRef' in station
                else ''
            })
        return stations_formatted

    @staticmethod
    def generate_station_description(seed_type):
        return 'Radio is based on ' + seed_type

    @staticmethod
    def get_station_image_url(station):
        if 'compositeArtRef' in station:  # station is curated
            return station['compositeArtRef'][0]['url']
        elif 'imageUrls' in station:
            return station['imageUrls'][0]['url']  # station is seeded from artist/track
        else:
            return '../res/icons/glyphicons-33-wifi-alt_white.png'  # no image

    @staticmethod
    def get_station_seed(seed):
        if 'curatedStationId' in seed:
            return {'seed': seed['curatedStationId'], 'type': 'curated'}
        elif 'artistId' in seed:
            return {'seed': seed['artistId'], 'type': 'artist'}
        elif 'trackId' in seed:
            return {'seed': seed['trackId'], 'type': 'track'}
        elif 'genreId' in seed:
            return {'seed': seed['genreId'], 'type': 'genre'}
        elif 'albumId' in seed:
            return {'seed': seed['albumId'], 'type': 'album'}
        # elif 'trackLockerId' in seed:
        #    return {'seed': seed['trackLockerId', 'type': 'tracklocker']}
        else:
            Logger.warning('Listformatter: Failed to find seed ID for station (seed: {})'.format(str(seed)))
            return {'seed': '', 'type': 'unknownType'}

    def format_tracks_list(self, tracks):
        tracks_formatted = []
        for index, track in enumerate(tracks):
            tracks_formatted.append({
                'title': track['title'],
                'track_id': track['nid'],
                'track_number': track['trackNumber'],
                'artist': track['artist'],
                'artist_id': track['artistId'][0] if 'artistId' in track else '',
                'album': track['album'],
                'album_id': track['albumId'] if 'albumId' in track else '',
                'album_artist': track['albumArtist'] if 'albumArtist' in track else '',
                'album_image_url': track['albumArtRef'][0]['url'] if 'albumArtRef' in track else '',
                'genre': track['genre'] if 'genre' in track else '',
                'year': track['year'] if 'year' in track else '',
                'duration': self.milliseconds_to_duration(track['durationMillis']),
                'duration_ms': track['durationMillis'],
                'play_count': track['playCount'] if 'playCount' in track else ''
            })
        return tracks_formatted

    @staticmethod
    def get_song_key(song):
        if 'best_result' in song:
            Logger.trace('Best match: ' + song['track']['title'])
            return 0 if song['best_result'] else 1
        return 0

    @staticmethod
    def milliseconds_to_duration(milliseconds):
        milliseconds = int(milliseconds)
        seconds_total = int(milliseconds / 1000)
        minutes = int(seconds_total / 60)
        seconds = seconds_total % 60
        if seconds < 10: seconds = '0' + str(seconds)
        return '{0}:{1}'.format(minutes, seconds)
