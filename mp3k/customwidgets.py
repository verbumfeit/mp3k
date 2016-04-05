from kivy.uix.anchorlayout import AnchorLayout
from kivy.uix.togglebutton import ToggleButton
from kivy.uix.gridlayout import GridLayout
from kivy.properties import BooleanProperty, NumericProperty, ListProperty, ObjectProperty, StringProperty
from kivy.uix.behaviors.button import ButtonBehavior
from kivy.uix.selectableview import SelectableView
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.slider import Slider
from kivy.uix.widget import Widget
from kivy.uix.image import AsyncImage, Image
from hoverbehavior import HoverBehavior
from kivy.logger import Logger
from math import sqrt
from inspect import ismethod
from globals import Globals


class LoginCredentials(AnchorLayout):
    def __init__(self, **kwargs):
        self.old_login = Globals.CONFIG.get('Google Play Music', 'login')
        super().__init__(**kwargs)


class LoginDevices(AnchorLayout):
    pass


class DeviceButton(ToggleButton):
    def __init__(self, device_id=None, **kwargs):
        self.device_id = device_id
        super().__init__(**kwargs)


class SongViewer(GridLayout):
    data_songs = ListProperty()

    @staticmethod
    def _args_converter(row_index, rec):
        _dict = {'track': rec, 'index': row_index, 'is_selected': False}
        return _dict


class AlbumViewer(GridLayout):
    data_albums = ListProperty()

    @staticmethod
    def _args_converter(row_index, rec):
        _dict = {'album': rec, 'index': row_index, 'is_selected': False}
        return _dict


class StationViewer(GridLayout):
    data_stations = ListProperty()

    @staticmethod
    def _args_converter(row_index, rec):
        _dict = {'station': rec, 'index': row_index, 'is_selected': False}
        return _dict


class PlaylistView(GridLayout):
    @staticmethod
    def _args_converter(row_index, rec):
        rec['index'] = row_index
        _dict = {'track': rec, 'index': row_index, 'is_selected': False}
        return _dict

    def get_track(self, index):
        return self.children[0].ids['container'].children[index]


class HoverSwitchImage:
    image = None

    def hover_image_enter(self, **kwargs):
        self.image.source_img = self.image.source  # store original cover
        self.image.source = kwargs['source_img_hover']  # set hover image

    def hover_image_leave(self, **kwargs):
        self.image.source = self.image.source_img  # restore original cover


class TrackListItem(ButtonBehavior, SelectableView, BoxLayout, HoverSwitchImage):
    index = NumericProperty()
    track = ObjectProperty()
    is_selected = BooleanProperty()


class AlbumListItem(ButtonBehavior, SelectableView, BoxLayout, HoverSwitchImage):
    index = NumericProperty()
    album = ObjectProperty()
    is_selected = BooleanProperty()


class StationListItem(ButtonBehavior, SelectableView, BoxLayout, HoverSwitchImage):
    index = NumericProperty()
    station = ObjectProperty()
    is_selected = BooleanProperty()


class StationPanelItem(ButtonBehavior, BoxLayout):
    station = ObjectProperty()

    def __init__(self, station):
        self.station = station
        super().__init__()

    def make_image_opaque(self, **kwargs):
        if self.station['description'] is not '':  # Make image opaque so the description shines through
            self.image.cover.color = [1, 1, 1, .1]

        self.image.play_icon.color = [1, 1, 1, 1]  # Show Play icon

    def make_image_solid(self, **kwargs):
        if self.station['description'] is not '':
            self.image.cover.color = [1, 1, 1, 1]  # Make image solid so the description is hidden

        self.image.play_icon.color = [1, 1, 1, 0]  # Hide Play icon


class PlaylistTrackListItem(ButtonBehavior, SelectableView, BoxLayout, HoverSwitchImage):
    index = NumericProperty()
    track = ObjectProperty()
    is_selected = BooleanProperty()

    def update_image(self, img_path):
        Logger.debug('Updating track image')
        self.image.source = img_path


class ScreenButtons(BoxLayout):
    pass


class ProgressSlider(Slider):
    def on_touch_down(self, touch):
        if self.collide_point(*touch.pos):
            self.parent.skip_callback(touch.pos)
        # return super(self.__class__, self).on_touch_down(touch)
        return super().on_touch_down(touch)


def collide_point(obj, x, y):
    radius = obj.center_x - obj.x
    distance = sqrt((x - obj.center_x) ** 2 + (y - obj.center_y) ** 2)
    return distance <= radius


class CircleButton(ButtonBehavior, Widget):
    def collide_point(self, x, y):
        return collide_point(self, x, y)


class ImageButton(ButtonBehavior, Image):
    # https://groups.google.com/forum/#!topic/kivy-users/DBHfH81LRo0
    def select(self):  # needed, cause a click on an element/widget inside a ListViewItem always calls select()
        pass

    def deselect(self):  # needed, cause a click on another element/widget inside a ListViewItem always calls deselect()
        pass


class HoverableAsyncImage(HoverBehavior, ButtonBehavior, AsyncImage):
    enter_func = None
    leave_func = None
    kwargs = {}

    def __init__(self, **kwargs):
        self.source_img = None
        super().__init__(**kwargs)

    def on_enter(self):
        if ismethod(self.enter_func):
            self.enter_func(**self.kwargs)

    def on_leave(self):
        if ismethod(self.leave_func):
            self.leave_func(**self.kwargs)

    # https://groups.google.com/forum/#!topic/kivy-users/DBHfH81LRo0
    def select(self):  # needed, cause a click on an element/widget inside a ListViewItem always calls select()
        pass

    def deselect(self):  # needed, cause a click on another element/widget inside a ListViewItem always calls deselect()
        pass
