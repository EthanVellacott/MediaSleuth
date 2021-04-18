"""
This is purely concerned with initializing and displaying the MediaInspection

TODO focus this purely on the display of a MediaInspection item
 at the moment this handles the threading to initialize the "MediaInspection"
 I think the result should handle the threads, or there should be a separate object for that
"""

import threading
import os

from mediasleuth.mediainspection import MediaInspection


class MediaInspectionDisplayItem:
    def __init__(self, parent, filepath):
        self.parent = parent

        self.filepath = filepath
        self.parent_folder = os.path.basename(os.path.dirname(filepath))
        self.filename = os.path.basename(filepath)

        self.display_results = self.default_display_result()

        self.item = ''

        """
        spawn in a MediaInspection and start doing the processes in threads
        when a process is complete, update the display_results table, and push into the table
        """
        self.inspection = MediaInspection(parent.config, filepath)

        self.threads = []
        # do not start threads here or it'll ruin your day
        # the updating and the threads need all the dataview upstream of this to be in order, or it'll misbehave

    def default_display_result(self):
        return [
            self.filepath,
            self.parent_folder,
            self.filename,
            'loading...',
            'loading...',
            'loading...',
            'loading...',
            'loading...',
            'loading...',
            'loading...',
            'loading...',
            'loading...',
            'loading...',
            'loading...',
            'loading...',
            'loading...',
            'loading...',
            'loading...',
            'loading...',
            'loading...',
            'loading...',
            'loading...',
            'loading...',
            'loading...',
        ]

    def start_threads(self):
        """
        This kicks off threads that perform all of our checks
        The threads are nested such that dependant work happens one after the other
        eg audio check requires the content duration determined by pil whose assumptions depend on ffmpeg

        TODO better naming than thread1..5 - it's not very descriptive
        TODO better system than this for managing threads...
            It's highly possible to make quite a lot of threads at once with this system
            So we oughto look at pool management
        """
        t = self.thread1
        x = threading.Thread(target=t)
        x.start()
        self.threads.append(x)

    def thread1(self):
        self.inspection.do_ffmpeg_checks()
        self.update()

        # dependant threads
        t = self.thread2
        x = threading.Thread(target=t)
        x.start()
        self.threads.append(x)

    def thread2(self):
        self.inspection.do_pil_checks()
        self.update()

        # dependant threads
        for t in [self.thread3,
                  self.thread4,
                  self.thread5
                  ]:
            x = threading.Thread(target=t)
            x.start()
            self.threads.append(x)

    def thread3(self):
        self.inspection.do_pytesseract_checks()
        self.update()

    def thread4(self):
        self.inspection.do_op48_audio_check()
        self.update()

    def thread5(self):
        self.inspection.do_op59_audio_check()
        self.update()

    def __iter__(self):
        return self.display_results

    def update(self):
        """
        Update the UI table with new information
        Called intermittently by the threads
        """

        row = self.parent.get_row_by_file(self.filepath)

        # update results
        self.display_results = [
            self.filepath,
            self.parent_folder,
            self.filename,
            self.inspection.get_display('timecode_start'),
            self.inspection.get_display('content_start_timecode'),
            self.inspection.get_display('framecount'),
            self.inspection.get_display('full_duration'),
            self.inspection.get_display('content_duration'),
            self.inspection.get_display('slate'),
            self.inspection.get_display('black_at_tail'),
            self.inspection.get_display('slate_key_number'),
            self.inspection.get_display('op48_audio'),
            self.inspection.get_display('op59_audio'),
            self.inspection.get_display('audio_peak'),
            self.inspection.get_display('resolution'),
            self.inspection.get_display('fps'),
            self.inspection.get_display('video_bitrate'),
            self.inspection.get_display('video_codec'),
            self.inspection.get_display('audio_codec'),
            self.inspection.get_display('audio_bitrate'),
            self.inspection.get_display('audio_sample_rate'),
            self.inspection.get_display('slate_date'),
            self.inspection.get_display('slate_aspect'),
            self.inspection.get_display('slate_duration'),
        ]

        for col, v in enumerate(self.display_results):
            self.parent.dataview.SetValue(v, row, col)
