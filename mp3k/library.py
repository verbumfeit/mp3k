import json

from kivy.logger import Logger

from globals import Globals


class LibraryManager:
    def __init__(self):
        self.library = self.load_library()

    @staticmethod
    def load_library():
        with open('formatted_library.json') as outfile:
            library = json.load(outfile)
        return library

    def synchronize_library(self):
        library = self._get_gmusic_library()
        formatted_library = self._format_gmusic_library(library)
        with open('formatted_library.json', 'w') as outfile:
            json.dump(formatted_library, outfile)
        Logger.info('Library: Finished synchronizing')

    @staticmethod
    def _get_gmusic_library():
        return Globals.API.get_library()

    @staticmethod
    def _format_gmusic_library(library):
        formatted_library = {}
        for track in library:
            # Set album artist to default value if album artist is missing
            if 'albumArtist' in track:
                if track['albumArtist'] == '':
                    track['albumArtist'] = 'AlbumArtistMissing'
            else:
                track['albumArtist'] = 'AlbumArtistMissing'

            # Set album title to default value if album title is missing
            if 'album' in track:
                if track['album'] == '':
                    track['album'] = 'AlbumMissing'
            else:
                track['album'] = 'AlbumMissing'

            album_artist = track['albumArtist']
            album = track['album']

            # Add album artist to library
            if album_artist not in formatted_library:
                formatted_library[album_artist] = []
                Logger.debug("Library: Added '{}' to artists".format(album_artist))
            # Get album the track belongs to
            cur_album = next((item for item in formatted_library[album_artist] if item['title'] == album), None)
            # Add album to artist if it could not be found
            if not cur_album:
                formatted_library[album_artist].append({'tracks': [],
                                                        'title': track['album'],
                                                        'year': track['year'] if 'year' in track else ''})
                Logger.debug("Library: Added '{}' to albums".format(album))
                cur_album = formatted_library[album_artist][-1]
            # Add track to album
            cur_album['tracks'].append(track)

        Logger.info('Library: Finished formatting')
        return formatted_library

