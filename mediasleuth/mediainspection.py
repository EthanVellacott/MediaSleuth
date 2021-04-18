# BUILTIN

import os
import uuid

# EXTERNAL

from timecode import Timecode
import pytesseract

# INTERNAL

from mediasleuth.checks.slate_reader import SlateReader
from mediasleuth.checks.pixel_strip import PixelStrip
from mediasleuth.checks.audio import *
from mediasleuth.properties import *

# CONSTANTS

VIDEO_CONTAINERS = [
    'mov',
    'mkv',
    'mp4',
    'flv',
    'mxf',
    'avi'
]


class MediaInspection:
    """
    The MediaInspection class manages all the processes, as well as being the reference point for the data

    I don't love that, and I think a better way to manage it would be:
        - There is an InspectionResult is an interface for the data
        - And a InspectionParameter object to contain the processes

    TODO just hold the info, and the standards are held in a separate configurable file
    """

    def __init__(self, config, path):
        self.config = config

        self.stream = ''

        self.basic_properties = {
            'path':              BasicProperty(path),
            'name':              BasicProperty(os.path.basename(path).split('.')[0]),
            'from_folder':       BasicProperty(os.path.basename(os.path.dirname(path))),
            'extension':         BasicProperty(path.split('.')[-1]),
            'timecode_start':    TimecodeProperty(),
            'full_duration':     TimeProperty(),
            'framecount':        BasicProperty(),
            'fps':               BasicProperty(),
            'resolution':        BasicProperty(),
            'audio_peak':        BasicProperty(),
            'video_bitrate':     BasicProperty(),
            'video_codec':       BasicProperty(),
            'audio_codec':       BasicProperty(),
            'audio_bitrate':     BasicProperty(),
            'audio_sample_rate': BasicProperty()
        }

        self.estimated_properties = {
            'content_start_timecode': TimecodeProperty(),
            'content_start_frame':    BasicProperty(),
            'content_end_frame':      BasicProperty(),
            'content_duration':       TimeProperty(),
            'black_at_tail':          TimeProperty(),
            'slate_agency':           BasicProperty(),
            'slate_aspect':           BasicProperty(),
            'slate_client':           BasicProperty(),
            'slate_date':             BasicProperty(),
            'slate_director':         BasicProperty(),
            'slate_duration':         BasicProperty(),
            'slate_key_number':       BasicProperty(),
            'slate_product':          BasicProperty(),
            'slate_productionco':     BasicProperty(),
            'slate_title':            BasicProperty(),
            'content_aspect_ratio':   NotImplementedProperty(),
            # 'blanking_summary':       ListProperty(),
            'blanking_summary':       NotImplementedProperty(),
            'has_duplicate_frames':   NotImplementedProperty()
        }

        self.criteria_properties = {
            'slate':                  BasicProperty(),
            'op48_audio':             ConditionsProperty(),
            'op59_audio':             ConditionsProperty()
        }

        # INFORMATION FOR CREATING PROXY FILES

        self.uuid = uuid.uuid1()
        self.proxy_frame_filetype = config["FFmpeg"]["proxy_filetype"]
        self.ffmpeg_log_level = config["FFmpeg"]["log_level"]

    #
    # Properties
    #

    def set_null_properties(self, *properties):
        for p in properties:
            self.set_value(p, None)

    def get_value(self, key):
        """
        Gets raw values
        First checks basic properties, then estimates, then criteria
        """
        if key in self.basic_properties.keys():
            return self.basic_properties[key].value()

        if key in self.estimated_properties.keys():
            return self.estimated_properties[key].value()

        if key in self.criteria_properties.keys():
            return self.criteria_properties[key].value()

        return None

    def set_value(self, key, data):
        """
        Sets raw values
        First checks basic properties, then estimates, then criteria
        """
        if key in self.basic_properties.keys():
            self.basic_properties[key].set(data)
            return

        if key in self.estimated_properties.keys():
            self.estimated_properties[key].set(data)
            return

        if key in self.criteria_properties.keys():
            self.criteria_properties[key].set(data)
            return

    def set_values(self, key_data_dict):
        """
        Sets many raw values at once
        """
        for key in key_data_dict:
            self.set_value(key, key_data_dict[key])

    def get_display(self, key):
        """
        Gets values formatted for display
        First checks basic properties, then estimates, then criteria
        """
        if key in self.basic_properties.keys():
            return self.basic_properties[key].display()

        if key in self.estimated_properties.keys():
            return self.estimated_properties[key].display()

        if key in self.criteria_properties.keys():
            return self.criteria_properties[key].display()

        print("Cannot find display value "+key)
        return None

    def uuid_filename(self, extension):
        return "{}.{}".format(self.uuid, extension)

    def do_ffmpeg_checks(self):
        # If an unsupported video format is detected, set relevant values to null and exit
        if self.get_value('extension') not in VIDEO_CONTAINERS:
            self.set_null_properties('fps',
                                     'timecode_start',
                                     'resolution',
                                     'video_bitrate',
                                     'video_codec',
                                     'audio_codec',
                                     'audio_bitrate',
                                     'audio_sample_rate',
                                     'framecount',
                                     'full_duration')
            return

        # do any checks that come direct out of ffmpeg
        self.stream = ffmpeg.Stream(self.get_value('path'))

        # todo this is a reasonable default value - but we have a double up of setting a default here and elsewhere
        timecode_start = self.stream.video_start_timecode()
        if not timecode_start:
            timecode_start = '00:00:00:00'

        # NOTE : we want to do this instead of ask the stream for duration
        #   because the duration listed in the stream can be unreliable
        full_duration = float(self.stream.video_framecount() / self.stream.video_fps())
        
        self.set_values({
            'timecode_start':    timecode_start,
            'fps':               self.stream.video_fps(),
            'resolution':        self.stream.video_resolution(delimiter='x'),
            'video_bitrate':     self.stream.video_bitrate(),
            'video_codec':       self.stream.video_codec(),
            'audio_codec':       self.stream.audio_codec(),
            'audio_bitrate':     self.stream.audio_bitrate(),
            'audio_sample_rate': self.stream.audio_sample_rate(),
            'framecount':        self.stream.video_framecount(),
            'full_duration':     full_duration
        })

    def do_pil_checks(self):
        """
        dependant on : do_ffmpeg_checks

        This performs all checks that are reliant on PIL as a tool for scrutinizing the media

        We use ffmpeg in PixelStrip to create a proxy image, that is helpful in determining chunks of similar video
        This is used in conjunction with information gained in prior ffmpeg queries, to make assumptions about content
        """

        # If an unsupported video format is detected, set relevant values to null and exit
        if self.get_value('extension') not in VIDEO_CONTAINERS:
            self.set_null_properties('slate',
                                     'black_at_tail',
                                     'content_start_frame',
                                     'content_end_frame',
                                     'content_duration',
                                     'content_start_timecode',
                                     'aspect_ratio')
            return

        # We reference these values a lot later
        fps = self.get_value('fps')
        timecode_start = self.get_value('timecode_start')
        # resolution = self.get_value('resolution')

        """
        This creates a proxy file image where each frame of video is scaled down to 1 pixel
        In the process, the luminance and chromaticity is averaged
        We are able to query this to make basic extrapolations about sections of black, or duplicate frames 
        """
        ps = PixelStrip(self.config, self.get_value('path'))

        """
        Get chunks according to a 1 luma tolerance of change 
        If we were to use a tolerance much lower the slate changes from frame to frame
        """
        similar_chunks = ps.get_luma_chunks(tolerance=1)

        """
        ### SLATE
        We assess whether or not there is a slate (and implicitly if there are 2 seconds of black afterwards)
        We use the pixel strip to achieve this
        """
        start_chunk = similar_chunks[0]
        slate_duration = start_chunk.get_duration_seconds()

        second_chunk = similar_chunks[1]
        start_black_duration = second_chunk.get_duration_seconds()

        if round(slate_duration, 0) == 8 and round(start_black_duration) == 2:
            self.set_value('slate', True)
        else:
            self.set_value('slate', False)

        """
        ### BLACK FRAMES
        We get the amount of black frames at the tail of the file
        We use the pixel strip to achieve this
        """
        end_chunk = similar_chunks[-1]
        end_black_duration = end_chunk.get_duration_seconds()

        if end_chunk[0].luma < 5:
            self.set_value('black_at_tail', end_black_duration)
        else:
            self.set_null_properties('black_at_tail')

        """
        ### CONTENT
        We determine when the content starts, and how long it is 
        We use the pixel strip to achieve this

        If there is a slate or black at the tail, the similar chunks will be offset
        Thus we check our previous values before continuing
        """
        start_offset = 0
        if self.get_value('slate'):
            start_offset = 2

        end_offset = -1
        if self.get_value('black_at_tail'):
            end_offset = -2

        start_content = similar_chunks[start_offset][0].frame_number
        self.set_value('content_start_frame', start_content)

        end_content = similar_chunks[len(similar_chunks) + end_offset][-1].frame_number
        self.set_value('content_end_frame', end_content)

        self.set_value('content_duration', (end_content - start_content + 1) / float(fps))

        content_start_timecode = Timecode(fps, timecode_start)
        content_start_timecode.frames += start_content
        self.set_value('content_start_timecode', content_start_timecode)

        """
        ### BLANKING
        Not implemented yet
        Here we are assess if the crop is consistent across the video
        
        TODO Finding a system that can reliably identify the crop is surprisingly difficult
         Namely because media can fade to black, and be dark or even black along the crop - which is a challenge
         Really the best a computer system can do here is provide parts of the video flagged for potential issues
        
        ### ASPECT
        Not implemented yet
        Here we assess the media aspect ratio 
        
        TODO getting the media ratio - that is quite easy
         However, to get the content ratio - that is much more challenging, as with the above
         In fact, it's entirely valid for the content ratio to change over the course of the media (sometimes)
         eg The Dark Knight, shot in both Anamorphic and IMAX, has crop changes when watching the theatrical version
        """
        return

    def do_pytesseract_checks(self):
        """
        dependant on : do_ffmpeg_checks, do_pil_checks

        This performs an OCR read on a slice of the first frame, intending to recognize media key numbers

        IMPORTANT : the text recognition isn't perfect, and the filenames often don't match exactly
                    this just checks "probably right", or "not good at all" for speeds sake
        """

        try:
            slate_reader = SlateReader(self.config, self.get_value('path'))
            slate_reader.output_head_frame()
            slate_reader.read_tesseract()

            self.set_values({
                'slate_key_number': slate_reader.slate_info['key'],
                'slate_date':       slate_reader.slate_info['date'],
                'slate_duration':   slate_reader.slate_info['duration'],
                'slate_aspect':     slate_reader.slate_info['aspect']
            })

        except pytesseract.pytesseract.TesseractNotFoundError as e:
            print("Tesseract is not installed, not reading slate text \n{}".format(e))
            self.set_null_properties('slate_key_number', 'slate_date', 'slate_duration', 'slate_aspect')

        except Exception as e:
            print("Something went wrong, not reading slate text \n{}".format(e))
            self.set_null_properties('slate_key_number', 'slate_date', 'slate_duration', 'slate_aspect')

    def do_op48_audio_check(self):
        """
        dependant on : do_ffmpeg_checks, do_pil_checks

        This checks for OP48 audio compliance
        - 12 frames of silence at the content head
        - 12 frames of silence at the content tail
        """

        # If an unsupported video format is detected, set relevant values to null and exit
        # TODO audio check acknowledges if the media is mute
        if self.get_value('extension') not in VIDEO_CONTAINERS:
            self.set_null_properties('op48_audio',
                                     'audio_peak')
            return

        result = "OP48"
        issues = []

        path = self.get_value('path')
        content_start_frame = self.get_value('content_start_frame')
        content_end_frame = self.get_value('content_end_frame')
        fps = self.get_value('fps')

        # check from max volume across whole clip
        ac = is_max_volume_less_than(path, -9)
        if not ac:
            issues.append("audio peaks above -9 dB")

        # TODO they want "silence" but nothing says how silent it needs to be
        #  these masters evidently have some level of wiggle room, so I'm going to guess
        #  because I've seen things pass looking like that
        tolerable_level_of_silence = -50
        frames_either_side = 12

        # check content first 12 frames for silence
        content_start_seconds = content_start_frame / fps
        content_start_seconds_plus = (content_start_frame + frames_either_side) / fps

        mv = get_max_volume_for_duration(path, content_start_seconds, content_start_seconds_plus)
        if mv >= tolerable_level_of_silence:
            issues.append("first frames not silent")

        # check content last 12 frames for silence
        content_end_seconds = content_end_frame / fps
        content_end_seconds_minus = (content_end_frame - frames_either_side) / fps

        # TODO get a lot a false negatives here - investigate further
        # above is the strictly correct math, but maybe this fixes it ?
        # content_end_seconds_minus += 0.01
        # content_end_seconds_minus += 0.5
        content_end_seconds_minus += (1 / fps)

        mv = get_max_volume_for_duration(path, content_end_seconds_minus, content_end_seconds)
        if mv >= tolerable_level_of_silence:
            issues.append("last frames not silent")

        if issues:
            result = "Not OP48 - {}".format(', '.join(issues))

        self.set_value('op48_audio', result)
        self.set_value('audio_peak', get_max_volume(path))

    def do_op59_audio_check(self):
        """
        dependant on : do_ffmpeg_checks, do_pil_checks

        This checks for OP59 audio compliance
        """

        # If an unsupported video format is detected, set relevant values to null and exit
        # TODO audio check acknowledges if the media is mute
        if self.get_value('extension') not in VIDEO_CONTAINERS:
            self.set_null_properties('op59_audio',
                                     'audio_peak')
            return

        result = "OP59"
        issues = []

        path = self.get_value('path')
        content_start_frame = self.get_value('content_start_frame')
        content_end_frame = self.get_value('content_end_frame')
        fps = self.get_value('fps')

        # they want "silence" but nothing says how silent it needs to be
        # these masters evidently have some level of wiggle room,
        # so I'm going to guess it's this because I've seen things pass looking like that
        tolerable_level_of_silence = -50
        frames_either_side = 12

        # todo is there a better time and place for this check?
        # check content first 12 frames for silence
        content_start_seconds = content_start_frame / fps
        content_start_seconds_plus = (content_start_frame + frames_either_side) / fps

        # check from max volume across whole clip
        ac = is_loudness_in_bounds(path, -25, -23)
        if not ac:
            issues.append("loudness outside -24 ±1 LKFS bounds")

        mv = get_max_volume_for_duration(path, content_start_seconds, content_start_seconds_plus)
        if mv >= tolerable_level_of_silence:
            issues.append("first frames not silent")

        # check content last 12 frames for silence
        content_end_seconds = content_end_frame / fps
        content_end_seconds_minus = (content_end_frame - frames_either_side) / fps

        # TODO get a lot a false negatives here - investigate further
        # above is the strictly correct math, but maybe this fixes it ?
        # content_end_seconds_minus += 0.01
        # content_end_seconds_minus += 0.5
        content_end_seconds_minus += (1 / fps)

        mv = get_max_volume_for_duration(path, content_end_seconds_minus, content_end_seconds)
        if mv >= tolerable_level_of_silence:
            issues.append("last frames not silent")

        if issues:
            result = "Not OP59 - {}".format(', '.join(issues))

        self.set_value('op59_audio', result)
