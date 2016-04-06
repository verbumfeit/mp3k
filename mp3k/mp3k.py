import json

from gmusicapi import CallFailure
from kivy.app import App
from kivy.clock import Clock
from kivy.core.window import Window
from kivy.logger import Logger
from kivy.properties import NumericProperty
from kivy.uix.popup import Popup
from kivy.uix.screenmanager import ScreenManager, Screen
from kivy.uix.scrollview import ScrollView
from kivy.uix.stacklayout import StackLayout
from kivy.uix.widget import Widget
from kivy.utils import QueryDict, interpolate

from customwidgets import SongViewer, AlbumViewer, StationPanelItem, LoginCredentials, LoginDevices, DeviceButton
from formatter import Formatter
from globals import Globals
from gmusic import GoogleMusicApi
from history import History
from library import LibraryManager
from player import Player
from playlist import Playlist


# trace, debug, info, warning, error and critical.


class MP3k(Widget):
    playlist_width = NumericProperty()

    def __init__(self, **kwargs):
        Globals.CONFIG = App.get_running_app().config
        Globals.TESTING = Globals.CONFIG.get('Development', 'test_mode')

        self.playlist_width = int(Globals.CONFIG.get('Playlist', 'playlist_width'))

        Globals.API = GoogleMusicApi()
        self.login_failed_popup = None
        self.google_music_api_login()

        self.formatter = Formatter()

        self.player = Player()
        self.player.set_streaming_quality(Globals.CONFIG.get('Google Play Music', 'quality').split(':')[0])

        self.playlist = Playlist()

        self.librarymanager = LibraryManager()
        # self.librarymanager.load_library()

        self.history = History()
        self.playlist.queue = self.history.playlist_history

        self.updating_progress = False
        self.playlist_hidden = False

        super().__init__(**kwargs)
        self.player.bind(playing=self.update_play_button_state)
        self.player.bind(progress_percent=self.update_progress_slider)

        # Add search result views
        # Songs
        self.songlist = SongViewer()

        # Stations
        # self.stationlist = StationViewer()
        self.stationscroll = ScrollView(size_hint=(1, 1))
        self.stationscroll.do_scroll_x = False
        self.stationlist = StackLayout(size_hint_y=None, spacing=10)
        self.stationlist.bind(minimum_height=self.stationlist.setter('height'))
        self.stationscroll.add_widget(self.stationlist)

        # Albums
        self.albumlist = AlbumViewer()
        # Create and init screen manager
        self.sm = ScreenManager()
        self.init_screens()

        # Listen for Keyboard events
        self._keyboard = Window.request_keyboard(None, self, 'text')
        self._keyboard.bind(on_key_down=self._pressed_key)
        self.searchbar.focus = True

    def google_music_api_login(self):
        if Globals.API.login(Globals.CONFIG.get('Google Play Music', 'login'),
                             Globals.CONFIG.get('Google Play Music', 'password'),
                             Globals.CONFIG.get('Google Play Music', 'device_id')):
            Logger.debug('Google Music: Login successful')
            if self.login_failed_popup:
                self.login_failed_popup.dismiss()
                self.login_failed_popup = None
        else:
            Logger.warning("Google Music: Login Failed")
            if not self.login_failed_popup:
                popup = Popup(title='Google Play Music™ login', content=LoginCredentials(), auto_dismiss=False,
                              size_hint=(1, 1))
                self.login_failed_popup = popup

            if Globals.STARTED:  # login failed after configuration change
                self.login_failed_popup.open()  # open popup because MP3k is completely rendered
                App.get_running_app().close_settings()

            else:  # login failed on start
                pass  # wait with popup until MP3k is completely rendered (MP3kApp opens the popup in on_start())

    def try_login_step_1(self, instance, google_login, google_password):
        # Credentials login without device ID
        if Globals.API.login(google_login, google_password, ''):
            # login successful
            Globals.CONFIG.set('Google Play Music', 'login', google_login)
            Globals.CONFIG.set('Google Play Music', 'password', google_password)
            Globals.CONFIG.write()

            self.show_device_login()

        else:
            instance.login_failed_label.color = (1, 0, 0, 1)

    def try_login_step_2(self, button_container):
        # look for selected device
        for button in button_container.children:
            if button.state == 'down':  # got it
                Globals.CONFIG.set('Google Play Music', 'device_id', button.device_id)
                Globals.CONFIG.write()  # set device id in config

                if Globals.API.relogin(Globals.CONFIG.get('Google Play Music', 'login'),  # re-login with valid device_id
                                       Globals.CONFIG.get('Google Play Music', 'password'),
                                       Globals.CONFIG.get('Google Play Music', 'device_id')):
                    self.login_failed_popup.dismiss()
                    break
        else:
            Logger.error('LOGIN: You have to select a device!')

    def show_device_login(self):
        self.login_failed_popup.dismiss()
        self.login_failed_popup = Popup(title='Google Play Music™ login', content=self.build_devices_login(),
                                        auto_dismiss=False,
                                        size_hint=(1, 1))
        self.login_failed_popup.open()

    @staticmethod
    def build_devices_login():
        devices = Globals.API.get_registered_mobile_devices()  # get registered mobile devices
        login_devices = LoginDevices()

        # add buttons for devices
        for device in devices:
            btn = DeviceButton(text='{} (ID: {})'.format(device['name'], device['id']), device_id=device['id'],
                               size_hint_y=None, height=30, group='devices')
            login_devices.device_button_container.add_widget(btn)

        return login_devices

    def init_screens(self):

        # Create screens
        screen_songs = Screen(name='Songs', size_hint=(1, 1))
        screen_stations = Screen(name='Stations', size_hint=(1, 1))
        screen_albums = Screen(name='Albums', size_hint=(1, 1))

        # Add content to screens
        screen_songs.add_widget(self.songlist)
        # screen_stations.add_widget(self.stationlist)
        screen_stations.add_widget(self.stationscroll)
        screen_albums.add_widget(self.albumlist)

        # Add screens
        self.sm.add_widget(screen_songs)
        self.sm.add_widget(screen_stations)
        self.sm.add_widget(screen_albums)

        # Add screen manager and playlist
        self.screenmanagercontainer.add_widget(self.sm)

    def _pressed_key(self, keyboard, keycode, text, modifiers):
        if not self.searchbar.focus:
            if keycode[1] == 'spacebar' or keycode[0] == 1073742085:
                Logger.debug('Keyboard: Pressed spacebar/play-pause-media-key')
                self.playbutton_callback()
            elif keycode[0] == 1073742083:  # 'previous track' media key
                Logger.debug("Keyboard: Pressed 'previous track' media key")
                self.previousbutton_callback()
            elif keycode[0] == 1073742082:  # 'next track' media key
                Logger.debug("Keyboard: Pressed 'next track' media key")
                self.nextbutton_callback()
            #else:
            #    print(keycode)

    def update_play_button_state(self, instance, value):
        if value:
            self.playbutton.icon = '../res/icons/glyphicons-175-pause_white.png'
        else:
            self.playbutton.icon = '../res/icons/glyphicons-174-play_white.png'

    def update_progress_slider(self, instance, value):
        self.progress_slider.value = value

    def update_playlist_position(self, window, width, height):
        self.playlist_view.pos_hint = {'x': .3, 'y': 90.0 / height}

    def update_playlist_view(self, instance, value):
        print('Updating playlist..')
        print('data_queue before: ' + str(len(self.playlist_view.data_queue)))
        # self.playlist_view.data_queue = self.playlist.queue  # ListView should be updated if we do it like this..
        self.playlist_view.children[0].adapter.data.clear()  # ..but it isn't, so we do this
        self.playlist_view.children[0].adapter.data.extend(self.playlist.queue)  # and then this
        # self.playlist_view.content.listview.adapter.data = self.playlist.queue  # never do this, it replaces the
        # ObservableList and breaks kivy functionality
        print('data_queue after: ' + str(len(self.playlist_view.data_queue)))

    def _update_progress_interval(self, delta_time):
        if not self.updating_progress:
            self.updating_progress = True

            if self.player.current_track and self.player.playback_started and self.player.playing:
                # time_played_ms = pygame.mixer.music.get_pos()
                # duration_ms = int(self.musicmanager.current_track['duration_ms'])
                # progress = time_played_ms / (duration_ms / 100)

                progress_percent = self.player.send_cmd_to_mplayer('get_percent_pos', 'ANS_PERCENT_POSITION')
                if progress_percent is not False and progress_percent is not None:
                    old_progress_percent = self.player.progress_percent
                    self.player.progress_percent = interpolate(old_progress_percent, int(progress_percent))
                    Logger.trace('Progress: ' + str(self.player.progress_percent))
                elif progress_percent is False:
                    Logger.debug('_update_progress_interval: Received ' + str(progress_percent) + ' as progress')
                    self.player.playback_finished()
                    self.play_next_track()
                else:
                    Logger.debug('_update_progress_interval: Received ' + str(progress_percent) + ' as progress')

            # remove schedule if no track selected
            elif not self.player.playback_started and not self.player.playing:
                Logger.debug('No song playing, removing slider update interval..')
                self.updating_progress = False
                return False

            self.updating_progress = False

    def on_config_changed(self, section, key, value):
        Logger.debug('Config: Config changed')

        if key == 'playlist_width':
            self.playlist_width = int(value)

        elif section == 'Google Play Music':
            Globals.API.logout()
            self.google_music_api_login()

        elif section == 'Development':
            if key == 'test_mode':
                Globals.TESTING = True if value == '1' else False

    def fix_scrolling_workaround(self):
        self.playlist_view.listview._reset_spopulate()

    def playbutton_state(self):
        Logger.debug('Playbuttonstate: ' + self.playbutton.state)
        return 'down' if self.player.playing else 'normal'

    def mark_playing_track(self):
        # track_item = self.playlist_view.get_track(0)
        # track_item.update_image('../res/icons/equalizer.gif')
        playing_text = '{} - {}'.format(self.player.current_track['title'],
                                        self.player.current_track['artist'])

        self.playinglabel.text = playing_text
        App.get_running_app().title = playing_text

    def restart_track(self):
        Logger.info('Restarting track..')
        self.play_track(self.player.current_track)

    def play_previous_track(self):
        Logger.info('Playing previous track')
        track = self.playlist.get_previous_track()
        if track:
            self.play_track(track)

    def play_next_track(self):
        Logger.info('Playing next track')
        track = self.playlist.get_next_track()
        if track:
            self.play_track(track)
        else:
            App.get_running_app().title = 'MusicPlayer 3000 for Google Play Music™'

    def switch_screen_callback(self, screen_title):
        self.sm.current = screen_title

    def play_callback(self, track, index):
        Logger.debug('Playing from songlist (left): Index ' + str(index))
        self.playlist.add_track_and_set_current(track)
        self.fix_scrolling_workaround()
        self.play_track(track)

    def play_album_callback(self, album_id):
        index = len(self.playlist.queue)
        self.add_album_to_playlist_callback(album_id)
        idx, track = self.playlist.set_current_track(index)
        self.play_track(track)

    def play_from_playlist_callback(self, track, index):
        Logger.debug('Playing from playlist (right): Index ' + str(index))
        self.playlist.set_current_track(index)
        self.play_track(track)

    def play_track(self, track):
        Logger.info('Playing track: ' + track['title'])
        self.player.play_track_from_id(track)
        self.mark_playing_track()
        # self.set_playing_icon()
        # unschedule possible previous intervals
        Clock.unschedule(self._update_progress_interval)
        # start interval for updating the progress slider
        Clock.schedule_interval(self._update_progress_interval, .1)

    def set_playing_icon(self):
        index, current_track = self.playlist.get_current_track()
        # self.playlist_view.children[0].adapter.data[index]

    def playbutton_callback(self):
        if self.player.current_track:  # we have a track selected
            if self.player.playback_started and self.player.playing:  # pause track
                self.player.pause_current_track()
            elif self.player.playback_started and not self.player.playing:  # resume track
                self.player.resume_current_track()
            else:  # playback has finished, restart track
                self.restart_track()
        else:  # No track selected but maybe we have elements in the playlist
            Logger.debug('No current track set!')
            track = self.playlist.get_start()
            if track:
                self.play_track(track)
            else:  # do nothing if no track selected
                #self.librarymanager.synchronize_library()
                pass

    def nextbutton_callback(self):
        if self.player.current_track:  # we have a track selected
            self.play_next_track()
        else:  # No track selected but maybe we have some in the playlist
            Logger.debug('No current track set!')
            track = self.playlist.get_start()
            if track:
                self.play_track(track)
            else:  # do nothing if no track selected
                pass

    def previousbutton_callback(self):
        if self.player.current_track:  # we have a track selected
            self.play_previous_track()
        else:  # No track selected but maybe we have some in the playlist
            Logger.debug('No current track set!')
            track = self.playlist.get_start()
            if track:
                self.play_track(track)
            else:  # do nothing if no track selected
                pass

    def shufflebutton_callback(self):
        if self.playlist.shuffle:
            Logger.info("I won't shuffle anymore..")
            self.playlist.shuffle = False
            self.shufflebutton.source = self.shufflebutton.source_img_alt
        else:
            Logger.info("Everyday I'm shuffling..")
            self.playlist.shuffle = True
            self.shufflebutton.source = self.shufflebutton.source_img

    def skip_callback(self, touch_pos):
        width = self.progress_slider.width
        touch_pos_x = touch_pos[0]
        position = touch_pos_x / (width / 100)
        if self.player.current_track:  # we need a track to skip into
            if not self.player.playback_started:  # song is not playing, restart song
                self.restart_track()
            self.player.skip_track_to(position)  # skip to position
        else:
            # self.progress_slider.value = 0  # keep slider position at 0
            # TODO: Look into slider implementation to keep slider at 0
            pass

    def add_to_playlist_callback(self, track):
        self.playlist.add_track(QueryDict(track))
        self.fix_scrolling_workaround()

    def remove_from_playlist_callback(self, index):
        self.playlist.remove_track(index)

    def add_album_to_playlist_callback(self, album_id):
        album = Globals.API.get_album_info(album_id)
        album_tracks = album['tracks']
        if album_tracks:
            album_tracks = self.formatter.format_tracks_list(album_tracks)
            for track in album_tracks:
                self.playlist.add_track(QueryDict(track))
            self.fix_scrolling_workaround()

    def play_station_callback(self, title, seed):
        tracks = Globals.API.get_station_tracks(title, seed)
        if tracks:
            tracks = self.formatter.format_tracks_list(tracks)
            self.playlist.clear()
            for track in tracks:
                self.playlist.add_track(track)
            self.fix_scrolling_workaround()
            # self.playlist.set_current_track(0)
            #self.playbutton_callback()
            track = self.playlist.get_start()
            if track:
                self.play_track(track)
            else:  # do nothing if no track selected
                pass

    def playlist_button_callback(self):
        if self.playlist_hidden:
            self.playlist_container.width = self.playlist_width
            self.playlist_hidden = False
        else:
            self.playlist_container.width = 0
            self.playlist_hidden = True

    def clear_playlist_callback(self):
        Logger.info('Clearing playlist')
        self.playlist.clear()
        # self.playlist.set_current_track(0)

    def search(self, text):
        if len(text) >= 3:
            try:
                search_results = Globals.API.search(text)
                # with open('search_test.json', 'w') as outfile:
                #    json.dump(search_results, outfile)

                self.display_search_results(search_results)
            except CallFailure:
                Logger.warning("Search: No All Access for this account!")
                # TODO: Show login popup
                # TODO: Remove try..except block when gmusicapi 9.0.1 is stable
        else:
            with open('search_test.json') as outfile:
                search_results = json.load(outfile)
                self.display_search_results(search_results)

    def display_search_results(self, search_results):
        Logger.info("Displaying results..")

        Logger.debug("Displaying song results")
        tracks = []
        for entry in search_results['song_hits']:
            tracks.append(entry['track'])
        # songs_sorted = sorted(songs, key=self.get_song_key)
        tracks_formatted = self.formatter.format_tracks_list(tracks)
        # self.ids['list_songs'].data_songs = tracks_formatted
        self.songlist.data_songs = tracks_formatted

        Logger.debug("Displaying station results")
        stations = []
        for entry in search_results['station_hits']:
            stations.append(entry['station'])
        stations_formatted = self.formatter.format_stations_list(stations)

        # add station list items
        # self.stationlist.data_stations = stations_formatted

        # add station panels
        self.stationlist.clear_widgets()
        for station in stations_formatted:
            self.stationlist.add_widget(StationPanelItem(station))

        Logger.debug("Displaying album results")
        albums = []
        for entry in search_results['album_hits']:
            albums.append(entry['album'])
        albums_formatted = self.formatter.format_albums_list(albums)
        self.albumlist.data_albums = albums_formatted
