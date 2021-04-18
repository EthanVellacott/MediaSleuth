"""
EKV 2019
- made portable
Single python file
Only builtin libraries

A simple wrapper for basic uses of ffmpeg / ffprobe
Intended to work crossplatform

NOTE: As it currently stands, this only gets information from ffprobe and ffmpeg calls
    It needs some more thought before it can be applied to creating media, that is if we even want it to

Reason being : ffmpeg is an incredibly robust tool, and supporting it in a meaningful way takes work
    If we need that there is always this - https://github.com/kkroening/ffmpeg-python
"""

import re
import json
import subprocess

"""
SINGLE VALUE METHODS
Basic one shot commands that get one piece of info, one time
These are not advisable, because they only return the value, not the stream - so use sparingly
"""


def resolution(file, delimiter=''):
    return Stream(file).video_resolution(delimiter=delimiter)


def bitrate(file):
    return Stream(file).video_bitrate()


def framecount(file):
    return Stream(file).video_framecount()


def duration(file):
    return Stream(file).duration()


def fps(file):
    x = Stream(file).video_fps()
    return round(x, 2)


def start_timecode(file):
    return Stream(file).video_start_timecode()


"""
FULL VALUE CLASSES
A class that gets all the info one time, stores it, and you can look at it all kinds of ways
These are preferable to the single value methods for most purposes 

TODO reconcile this 
Initially the goals was to have the Stream object be the big kahuna that holds all the cards
However, several diagnostic tasks require a completely different command to run, meaning that it basically CAN'T combine
    ie VolumeDetection, LoudnessDetection, CropDetection
part of me wants to try and route us back to that paradigm
alternatively make the underlying function call clearer, and more different in the class names
"""


class VolumeDetection:
    def __init__(self, file, ss_from=0, to=0):
        self.file = file

        from_cmd = ''
        if ss_from:
            from_cmd = '-ss {} '.format(ss_from)

        to_cmd = ''
        if to:
            to_cmd = '-to {} '.format(to)

        # todo test swapping quotes for windows
        # self._cmd = "{} {} -i '{}' -af 'volumedetect' -f null /dev/null 2>&1".format(from_cmd, to_cmd, file)
        self._cmd = '{} {} -i "{}" -af "volumedetect" -f null /dev/null 2>&1'.format(from_cmd, to_cmd, file)
        self.raw = ffmpeg(self._cmd)

        # todo testing the speed of getting all information possible
        self._n_samples =      self.get_analysed_value("n_samples")
        self._mean_volume =    self.get_analysed_value("mean_volume")
        self._max_volume =     self.get_analysed_value("max_volume")
        self._histogram_10db = self.get_analysed_value("histogram_10db")
        self._histogram_11db = self.get_analysed_value("histogram_11db")
        self._histogram_12db = self.get_analysed_value("histogram_12db")
        self._histogram_13db = self.get_analysed_value("histogram_13db")
        self._histogram_14db = self.get_analysed_value("histogram_14db")
        self._histogram_15db = self.get_analysed_value("histogram_15db")

    def get_analysed_value(self, target_value):
        """
        This provides a neat function call to get analysed values, and default failures if they can't be found
        """
        if not self.raw:
            print('Trying to get audio analysed value {} before ffmpeg return'.format(target_value))
            return ''

        search_result = re.search(target_value+r': (?P<data>.+)', self.raw)

        if not search_result:
            return ''

        return search_result.groups()[0]

    def max_volume(self):
        # TODO make this work if the  split fails
        return float(self._max_volume.split(' ')[0])

    def mean_volume(self):
        # TODO make this work if the split fails
        return float(self._mean_volume.split(' ')[0])


class LoudnessDetection:
    def __init__(self, file, ss_from=0, to=0):
        self.file = file

        from_cmd = ''
        if ss_from:
            from_cmd = '-ss {} '.format(ss_from)

        to_cmd = ''
        if to:
            to_cmd = '-to {} '.format(to)

        # todo test swapping quotes for windows
        # self._cmd = "-nostats {} {} -i '{}' -filter_complex ebur128 -f null /dev/null".format(from_cmd, to_cmd, file)
        self._cmd = '-nostats {} {} -i "{}" -filter_complex ebur128 -f null /dev/null 2>&1'.format(from_cmd,
                                                                                                   to_cmd,
                                                                                                   file)
        self.raw = ffmpeg(self._cmd)

        """
        This is a little bit borked because the ffmpeg call prints out an integrated loudness value progressively,
        and we only want the last one.
        
        Other values we might be interested in : 
        integrated loudness threshold
        loudness range lra
        loudness range threshold
        loudness range low
        loudness range high
        """
        # TODO There might be a more elegant, or smarter way to do this - investigate
        integrated_loudness_values = [x.group() for x in re.finditer(r'I: (?P<data>.+)', self.raw)]
        try:
            self._integrated_loudness = integrated_loudness_values[-1]
            print("Loudness : {}".format(self._integrated_loudness))
        except Exception as e:
            print('Could not read loudness information - something has gone wrong \n{}'.format(e))
            self._integrated_loudness = None

    def integrated_loudness(self):
        # TODO make this neater
        try:
            return float(self._integrated_loudness.split(' ')[-2].strip())
        except Exception as e:
            print('Malformed loudness information : {}'.format(e))
            return 0


class CropDetection:
    """
    This is an experimental function - I'm not very confident that this will provide consistent useful results
    """
    def __init__(self, file, ss_from=0, to=0):
        self.file = file

        from_cmd = ''
        if ss_from:
            from_cmd = '-ss {} '.format(ss_from)

        to_cmd = ''
        if to:
            to_cmd = '-to {} '.format(to)

        self._crop_value = '72:16:0'
        """
        FYI
        cropdetect=limit:round:reset
        
        limit
                Set higher black value threshold, 
                which can be optionally specified from nothing (0) to everything (255). 
                An intensity value greater to the set value is considered non-black. Default value is 24.
        
        round
                Set the value for which the width/height should be divisible by. 
                The offset is automatically adjusted to center the video.
                Use 2 to get only even dimensions (needed for 4:2:2 video). 
                16 is best when encoding to most video codecs. Default value is 16.
        
        reset_count, reset
                Set the counter that determines after how many frames cropdetect will reset 
                    the previously detected largest video area and start over to detect the current optimal crop area. 
                Default value is 0.
                
                This can be useful when channel logos distort the video area. 
                0 indicates never reset and return the largest area encountered during playback.
        
        So the default is:
            24:16:0
        Personally, I've found that 24 it not gracious enough for us 
        Try : 
            72:16:0
        
        """
        # todo test swapping quotes for windows
        # self._cmd = "{} {} -i '{}' -vf 'cropdetect={}' -f null /dev/null".format(from_cmd,
        self._cmd = '{} {} -i "{}" -vf "cropdetect={}" -f null /dev/null 2>&1'.format(from_cmd,
                                                                                      to_cmd,
                                                                                      file,
                                                                                      self._crop_value)
        self.raw = ffmpeg(self._cmd)

        all_crop_infos = re.findall(r'crop=.*', self.raw)
        self._crop_infos = [CropInfo(x) for x in all_crop_infos]

    def crop_info(self, index=''):
        if index and index in self._crop_infos.keys():
            return self._crop_infos[index]
        return self._crop_infos


class CropInfo:
    def __init__(self, input_string):
        self.raw = input_string
        self.width, self.height, self.x, self.y = re.findall(r'\d+', input_string)


class Stream:
    def __init__(self, file):
        self.file = file

        # todo test reversing the quotes here for windows compliance
        # self._cmd = "-v quiet -print_format json -show_format -show_streams '{}'".format(file)
        self._cmd = '-v quiet -print_format json -show_format -show_streams "{}"'.format(file)

        self.raw = ffprobe(self._cmd)

        try:
            self.json_dump = json.loads(self.raw)
        except Exception as e:
            print('Could not parse command output as .json - is ffmpeg installed? \n{}'.format(e))

        try:
            self.streams = self.json_dump['streams']
            self.format = self.json_dump['format']
        except Exception as e:
            print('Could not parse .json to default parameters - something is wrong.\n{}'.format(e))

        print(self.streams)

    # stream access
    def format_info(self, key):
        if not self.format:
            return
        if key not in self.format.keys():
            return
        return self.format[key]

    def video_stream(self):
        if not self.video_streams():
            return
        return self.video_streams()[0]

    def video_streams(self):
        return [x for x in self.streams if x['codec_type'] == 'video']

    def data_stream(self):
        if not self.data_streams():
            return
        return self.data_streams()[0]

    def data_streams(self):
        return [x for x in self.streams if x['codec_type'] == 'data']

    def audio_stream(self):
        if not self.audio_stream():
            return
        return self.audio_stream()[0]

    def audio_streams(self):
        return [x for x in self.streams if x['codec_type'] == 'audio']

    # video stream info
    def video_codec(self, stream_index=0):
        return self.video_streams()[stream_index]['codec_long_name']

    def video_width(self, stream_index=0):
        return self.video_streams()[stream_index]['width']

    def video_height(self, stream_index=0):
        return self.video_streams()[stream_index]['height']

    def video_resolution(self, stream_index=0, delimiter=''):
        x = (self.video_width(stream_index), self.video_height(stream_index))
        if delimiter:
            x = delimiter.join([str(n) for n in x])
        return x

    def video_bitrate(self, stream_index=0):
        return self.video_streams()[stream_index]['bit_rate']

    def video_framecount(self, stream_index=0):
        return int(self.video_streams()[stream_index]['nb_frames'])

    def video_fps(self, stream_index=0):
        # not all video files carry info this way
        a, b = self.video_streams()[stream_index]['avg_frame_rate'].split('/')

        if not a and not b:
            a, b = self.video_streams()[stream_index]['r_frame_rate'].split('/')

        return float(a)/float(b)

    def video_start_timecode(self, stream_index=0):
        # todo here we return an empty string if we can't find a timecode,
        #  but on the other end we set a default '00:00:00:00'
        #  I think I ought to decide which is best and make that the return
        # not all video files carry timecode data, so just don't return anything
        if 'timecode' not in self.video_streams()[stream_index]['tags']:
            return ''
        return self.video_streams()[stream_index]['tags']['timecode']

    # audio stream info
    def audio_codec(self, stream_index=0):
        return self.audio_streams()[stream_index]['codec_long_name']

    def audio_sample_rate(self, stream_index=0):
        return self.audio_streams()[stream_index]['sample_rate']

    def audio_bitrate(self, stream_index=0):
        return self.audio_streams()[stream_index]['bits_per_sample']

    # format info
    def duration(self):
        return float(self.format_info('duration'))


"""
# the commands

testing out a theory about /usr/local/bin
^ past me, would've been really helpful to describe the theory in practice here

I've now removed any reference to /usr/local/bin - just using the command serves cross platform usages better 
"""


def ffmpeg(*args):
    cmd = 'ffmpeg {}'.format(*args)
    print(cmd)
    return run_ffcmd(cmd)


def ffprobe(args):
    cmd = 'ffprobe {}'.format(args)
    print(cmd)
    return run_ffcmd(cmd)


def run_ffcmd(cmd):
    p = subprocess.Popen(cmd,
                         stdin=subprocess.PIPE,
                         stdout=subprocess.PIPE,
                         stderr=subprocess.PIPE,
                         shell=True)
    out, err = p.communicate()

    return out.decode('ASCII')



