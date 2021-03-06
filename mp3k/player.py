import os
import subprocess
import sys
import urllib.request
from queue import LifoQueue, Empty
from threading import Thread
from time import sleep

from kivy.clock import mainthread
from kivy.event import EventDispatcher
from kivy.logger import Logger
from kivy.properties import BooleanProperty, NumericProperty

from globals import Globals

ON_POSIX = 'posix' in sys.builtin_module_names


class Player(EventDispatcher):
    playing = BooleanProperty(False)  # if playback is paused, also controls state of play button
    progress_percent = NumericProperty(0)
    volume = NumericProperty(0)

    def __init__(self):
        self.streaming_quality = u'hi'
        self.current_track = None  # track dict
        self.playback_started = False  # if track was started
        self.player = None  # mplayer process
        self.output_watcher = None
        self.queue = LifoQueue()
        self._start_mplayer()
        self.volume = int(Globals.CONFIG.get('Player', 'volume'))
        self.set_volume(self.volume)

        # set mp3 path & name (replace \ with / because mplayer expects / as separator, even on Windows)
        Globals.MP3_PATH = Globals.get_valid_path('../res/stream{}.mp3'.format(Globals.MPLAYER_PID)).replace('\\', '/')
        open(Globals.MP3_PATH, 'w').close()  # Create/empty dummy mp3

        super().__init__()

    def set_streaming_quality(self, quality):
        if quality == 'High':
            self.streaming_quality = u'hi'
        elif quality == 'Medium':
            self.streaming_quality = u'med'
        elif quality == 'Low':
            self.streaming_quality = u'low'

        Logger.debug('Streaming: Set streaming quality to ' + self.streaming_quality)

    def set_volume(self, value):
        value = int(value)
        Logger.debug('Volume: ' + str(self.volume))
        self.volume = value
        self.send_cmd_to_mplayer('volume {} 1'.format(int(value)))
        Globals.CONFIG.set('Player', 'volume', int(value))
        Globals.CONFIG.write()

    @staticmethod
    def format_mplayer_cmd(cmd):
        cmd = '\n{}'.format(cmd)
        return cmd.encode()

    def send_cmd_to_mplayer(self, cmd, expected_tag=''):
        if self.player:
            try:
                Logger.trace('Sending to mplayer: ' + cmd)
                output = self._perform_command(cmd, expected_tag)
                return output
            except BrokenPipeError:
                Logger.exception('Pipe unavailable..')
                return False
        else:
            Logger.warning('Could not execute cmd. No player!')
            return False

    # http://stackoverflow.com/questions/15856922/python-send-command-to-mplayer-under-slave-mode
    def _perform_command(self, cmd, expected_tag):
        if self.player.returncode is None:
            print(cmd, flush=True, file=self.player.stdin)  # write cmd to mplayers stdin
            try:
                output = self.queue.get_nowait()  # get_nowait()  # get(timeout=0.05)
            except Empty:
                pass
            else:  # got line
                Logger.trace("Output: {}".format(output.rstrip()))
                split_output = output.split(expected_tag + '=', 1)
                if len(split_output) == 2 and split_output[0] == '':  # we have found it
                    value = split_output[1]
                    return value.rstrip()
                elif 'EOF code:' in output:
                    Logger.debug('Output: ' + output)
                    if '1' in output:  # regular exit code
                        Logger.debug('Reached end of file..')
                        return False
                    # EOF code: 4 is also possible (interrupted playback by loading a new file)
        else:
            Logger.debug('mplayer process finished..')
            self._start_mplayer()
            return False

    @staticmethod
    def enqueue_output(out, queue):
        for line in iter(out.readline, b''):
            if '=' in line or 'EOF code:' in line:
                queue.put(line)
        out.close()

    def play_track_from_id(self, track):
        # immediately display correct button label/icon and
        # prevent update_progress_interval from removing itself before song starts
        self.playing = True
        # get stream url
        mp3_url = Globals.API.get_stream_url(track['track_id'], self.streaming_quality)
        Logger.trace(mp3_url)
        # set current track
        self.current_track = track
        # start download
        Thread(target=self.download_and_play_track_thread, args=(mp3_url, Globals.MP3_PATH, Globals.BUFFER_ITERATIONS)).start()

    @mainthread
    def _play(self):
        self.send_cmd_to_mplayer('loadfile ' + Globals.MP3_PATH)

        self.playback_started = True
        self.playing = True

    def download_and_play_track_thread(self, url, location, buffer):
            bytestream = urllib.request.urlopen(url)
            mp3_file = open(location, 'wb')
            Logger.debug('Starting download..!')

            mp3_bytes = None
            iteration = 0
            playing = False
            while mp3_bytes is not b'':
                mp3_bytes = bytestream.read(40000)  # 40,000 bytes
                mp3_file.write(mp3_bytes)
                if iteration < buffer:
                    Logger.debug('Buffering..')
                    iteration = iteration + 1
                elif iteration == buffer:
                    Logger.debug('Buffering complete, playing now..')
                    self._play()
                    playing = True
                    iteration = iteration + 1

                    # if iteration == buffer + 1:
                    #    Logger.debug('Caught download in loop')
                    #    while True:
                    #        pass

            Logger.debug('Download completed!')
            if not playing:  # file was smaller than buffer
                Logger.debug('File was smaller than buffer, playing now..')
                self._play()
            mp3_file.close()
            bytestream.close()

    def playback_finished(self):
        Logger.info('Playback finished..')
        if not Globals.TESTING:
            Globals.API.increment_track_playcount(self.current_track['track_id'])
        self.playing = False
        self.playback_started = False
        self.progress_percent = 0

    def _start_mplayer(self):
        Logger.info('mplayer: Starting..')
        # start mplayer as slave in idle mode, keep it quiet but emit EOF when end of file is reached
        mplayer_path = Globals.CONFIG.get('mplayer', 'mplayer_path')
        cmd = [mplayer_path, '-slave', '-idle', '-quiet', '-msglevel', 'all=-1:global=6']
        self.player = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE, bufsize=1,
                                       universal_newlines=True, close_fds=ON_POSIX)  # TODO: Add exception handling

        Globals.MPLAYER_PID = self.player.pid

        Logger.debug('mplayer: Starting mplayer output reader..')
        # http://stackoverflow.com/questions/375427/non-blocking-read-on-a-subprocess-pipe-in-python
        self.output_watcher = Thread(target=self.enqueue_output, args=(self.player.stdout, self.queue))
        self.output_watcher.daemon = True  # thread dies with the program
        self.output_watcher.start()

        Logger.info('mplayer: Successfully started')

    def kill_mplayer(self):
        if Globals.MPLAYER_PID:
            Logger.debug('Killing mplayer process..')
            self.player.terminate()
            sleep(.1)
            Logger.debug('Removing mp3 file..')
            os.remove(Globals.MP3_PATH)

    def kill_output_watcher(self):
        self.output_watcher.join()

    def _cleanup_mplayer_process(self):
        Logger.debug('Cleaning up mplayer process')
        self.player.poll()  # remove defunct mplayer process
        Globals.MPLAYER_PID = None
        self.player = None

    def resume_current_track(self):
        if self.playback_started and not self.playing:  # pause track, it's playing
            Logger.info('Resuming Track')
            self.send_cmd_to_mplayer('pause')
            self.playing = True
        else:
            Logger.info('No track selected!')

    def pause_current_track(self):
        if self.playback_started and self.playing:
            Logger.info('Pausing Track')
            self.send_cmd_to_mplayer('pause')
            self.playing = False

    def skip_track_to(self, position):
        Logger.info('Skipping track to:' + str(position))
        if self.current_track:
            self.pause_current_track()
            self.send_cmd_to_mplayer('seek {} 1'.format(position))
            self.resume_current_track()
