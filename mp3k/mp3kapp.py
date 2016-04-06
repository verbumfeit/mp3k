from kivy.app import App
from kivy.uix.settings import SettingsWithSidebar

from globals import Globals
from mp3k import MP3k


class MP3kApp(App):

    def build(self):
        self.title = 'MusicPlayer 3000 for Google Play Music™'
        self.icon = '../res/icons/headphones_icon.png'
        self.settings_cls = SettingsWithSidebar
        return MP3k()

    def on_start(self):
        Globals.STARTED = True
        # Open login popup if login failed on start
        if self.root.login_failed_popup:
            self.root.login_failed_popup.open()

    def on_stop(self):
        # Save history
        self.root.history.save_to_history('playlist', self.root.playlist.get_queue())
        self.root.history.write_history()

        # Kill mplayer
        self.root.player.kill_mplayer()

    def build_config(self, config):
        config.setdefaults('Google Play Music', {
            'login': '',
            'password': '',
            'device_id': '',
            'quality': 'High: 320',
        })
        config.setdefaults('Playlist', {
            'playlist_width': 400
        })
        config.setdefaults('Player', {
            'volume': 75
        })

    def on_config_change(self, config, section, key, value):
        self.root.on_config_changed(section, key, value)

    def build_settings(self, settings):
        settings.add_json_panel('MusicPlayer 3000', self.config, 'settings.json')
