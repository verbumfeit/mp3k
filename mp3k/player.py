import os
import select
import signal
import subprocess
import urllib.request
from threading import Thread

from kivy.clock import mainthread
from kivy.event import EventDispatcher
from kivy.properties import BooleanProperty, NumericProperty, Logger

from globals import Globals


class Player(EventDispatcher):
    playing = BooleanProperty(False)  # if playback is paused, also controls state of play button
    progress_percent = NumericProperty(0)

    def __init__(self):
        self.streaming_quality = u'hi'
        self.current_track = None  # track dict
        self.playback_started = False  # if track was started
        self.player = None  # mplayer process
        super().__init__()

    def set_streaming_quality(self, quality):
        if quality == 'High':
            self.streaming_quality = u'hi'
        elif quality == 'Medium':
            self.streaming_quality = u'med'
        elif quality == 'Low':
            self.streaming_quality = u'low'

        Logger.debug('Streaming: Set streaming quality to ' + self.streaming_quality)

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
            while select.select([self.player.stdout], [], [], 0.05)[0]:  # give mplayer time to answer...
                output = self.player.stdout.readline()
                Logger.trace("Output: {}".format(output.rstrip()))
                split_output = output.split(expected_tag + '=', 1)
                if len(split_output) == 2 and split_output[0] == '':  # we have found it
                    value = split_output[1]
                    return value.rstrip()
                elif output.rstrip() == 'Exiting... (End of file)':
                    Logger.debug('Reached end of file..')
                    return False
        else:
            Logger.debug('mplayer process finished..')
            return False

    def play_track_from_id(self, track):
        # immediately display correct button label/icon and
        # prevent update_progress_interval from removing itself before song starts
        self.playing = True
        # get stream url
        mp3_url = Globals.API.get_stream_url(track['track_id'], self.streaming_quality)
        Logger.trace(mp3_url)
        # set download location
        mp3_path = '../res/stream.mp3'
        track['mp3_path'] = mp3_path
        # set current track
        self.current_track = track
        # start download
        Thread(target=self.download_and_play_track_thread, args=(mp3_url, mp3_path, Globals.BUFFER_ITERATIONS)).start()

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

    @mainthread
    def _play(self):
        # TODO: start mplayer in idle mode, so we don't have to kill an restart the process for each track
        cmd = ['mplayer', '-slave', '-quiet', self.current_track['mp3_path']]

        # kill mplayer process if a track is already running
        if self.player:
            self.pause_current_track()
            if self.player.returncode is None:  # if process doesn't have an exitcode it's still running
                Logger.debug('Killing old player..')
                self.player.kill()  # so kill it
                self._cleanup_mplayer_process()  # and remove the defunct process

        # http://stackoverflow.com/questions/35642313/writing-commands-to-mplayer-subprocess-with-python-3-in-windows
        self.player = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                       stderr=subprocess.PIPE, bufsize=1, universal_newlines=True)

        Globals.MPLAYER_PID = self.player.pid
        self.playback_started = True
        self.playing = True

    def playback_finished(self):
        Logger.info('Playback finished..')
        self.playing = False
        self.playback_started = False
        self.progress_percent = 0
        self._cleanup_mplayer_process()

    @staticmethod
    def kill_mplayer():
        if Globals.MPLAYER_PID:
            Logger.debug('Killing mplayer process..')
            os.kill(Globals.MPLAYER_PID, signal.SIGTERM)

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
