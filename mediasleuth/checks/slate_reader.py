# builtin
import os
import re
import uuid
import subprocess
# from pprint import pprint

# external
from PIL import Image
import pytesseract

# internal
import ext.ffmpeg as ffmpeg
import ext.systools as systools

from mediasleuth.platform import ffmpeg_cmd, temp_directory


class SlateReader:
    """
    This class takes a file in, expected to be some kind of movie file
        Strips off the first frame
        Pulls information from that frame
        Reads the text on it
        Allows you to return that info

    If we wanted to bump up the usefulness, we could make something that can read text all throughout a video
        eg BurninsReader
    """

    def __init__(self, config, file):
        print(file)
        self.config = config
        self.file = file
        self.uuid = uuid.uuid1()

        self.proxy_frame_filetype = config["FFmpeg"]["proxy_filetype"]
        self.ffmpeg_log_level = config["FFmpeg"]["log_level"]

        self.head_frame_path = ''

        keys = self.config["Slate Reader"]["keys"]
        self.keys = [key.strip("'") for key in keys.split(',')]

        # after running read tesseract, this will contain a dictionary of the read info, referenced to the self.keys
        self.slate_info = {}

    def output_head_frame(self, edge_crop=80):
        """
        subprocess call to FFMPEG to get the first frame
        this version comes with no filtering
        edge crop lets you narrow off pesky unwanted info from the edge of frame

        TODO we might want to offer some flexible options here:
            a flat value, as is current
            different width and height values
            a bounding box
        """

        # make our temp directory, and filename
        head_frame_path = temp_directory("head_frame")
        systools.mkdir(head_frame_path)

        head_frame_filename = "{}.{}".format(self.uuid, self.proxy_frame_filetype)
        head_frame_path = os.path.join(head_frame_path, head_frame_filename)
        print("Outputting head frame for OCR read : {}".format(head_frame_path))

        # define our crop area
        # this is designed with a specific slate in mind - ideally this should be configurable
        resolution = ffmpeg.resolution(self.file)
        out_w = resolution[0] - (edge_crop * 2)
        out_h = resolution[1] - (edge_crop * 2)
        x, y = edge_crop, edge_crop

        """
        This grabs the first frame of the video as the 'slate'
        TODO configure which frame it grabs
        
        We also apply some effects in ffmpeg to enhance the readability in Tesseract:
            invert the colour, as tesseract gets a better read off of black text on white background 
            desaturate it, as colour is another factor that makes text harder to read
            adjust the gamma, brightness and contrast to a readability sweetspot
            apply a sharpening filter for more clarity  
            tips from : https://www.randombio.com/linuxsetup141.html (2019)
        
        Default is stored in a config for easy editing 
            negate, eq=saturation=0:brightness=0.01:gamma=0.2:contrast=1.2, unsharp=5:5:1.5:5:5:0.0
        TODO test some alternatives
            eq=saturation=0:brightness=0.1:gamma=0.1:contrast=1, unsharp=5:5:1.5:5:5:0.0
            eq=saturation=0:gamma=0.2:contrast=1.5
            eq=saturation=0:gamma=0.05:contrast=1.2
        """

        cmd = '{} -ss 0 {} -y -i "{}" -vf "crop={}:{}:{}:{}, {}" -t 0.01 "{}"'.format(
            ffmpeg_cmd(),
            self.ffmpeg_log_level,
            self.file,
            out_w, out_h, x, y,
            self.config["Slate Reader"]["slate_filter"],
            head_frame_path
        )

        print(cmd)
        subprocess.call(cmd, shell=True)

        # todo should confirm that the command ran correctly ?
        self.head_frame_path = head_frame_path

    def read_tesseract(self):
        print("Reading head frame tesseract text recognition : {}".format(self.head_frame_path))

        if not self.head_frame_path:
            print("Failed to locate frame for OCR read - something went wrong")
            return

        im = Image.open(self.head_frame_path)

        # This is definitely the goal heuristic -
        # CBB package this up so that it's not a direct part of the slate reader
        # really this can take any kind of sparse text across a page and put it into lines
        # the part that I think belongs here is the reading of keys, and splitting into key value pairs

        # 1. Do the pytesseract read
        d = pytesseract.image_to_data(im, output_type=pytesseract.Output.DICT)

        # 2. Take the text coordinates from the pytesseract read, and store them as bounding boxes
        text_coord = []
        for i, t in enumerate(d['text']):
            if not t:
                continue
            text_coord.append(TextBox(d['left'][i], d['top'][i], d['width'][i], d['height'][i], t))

        print("Individual text box content :\n {}".format([x[-1] for x in text_coord]))

        # 3. Find greater bounding boxes for any text boxes overlapping in the y-axis (that might constitute a line)
        # todo implement tolerances for x and y overlap
        # cbb is there ever a case that we might want to consider columns? hopefully not
        bounding_boxes = []
        for item in text_coord:
            overlaps_with = []

            for other in text_coord:
                if item == other:
                    continue

                if item.overlaps(other):
                    overlaps_with.append(other)

            bounding_boxes.append(get_greatest_bounding_box(overlaps_with+[item, ]))

        # filter them for uniqueness
        uniq_bounding_boxes = set(bounding_boxes)

        # 4. For each bounding box, collate the text of any overlapping boxes into a line
        lines = []
        for bounding_box in uniq_bounding_boxes:
            newline = ''
            for text_box in text_coord:
                if text_box.overlaps(bounding_box):
                    newtext = text_box.text
                    newline += ' {}'.format(newtext)
            lines.append(newline)

        # get only unique lines
        uniq_lines = set(lines)

        # 5. package our lines into self.slate_info based on matching the strings in self.keys
        slate_info = {}
        for key in self.keys:
            for line in uniq_lines:
                if key in line:
                    # use regex to find the key in the line
                    # this means we can't get a false positives from keys containing other keys
                    info = re.search(key+r' (?P<data>.+)', line)

                    # if not info then it's not a direct match to our key, so keep looking
                    if not info:
                        continue

                    slate_info[key] = info.group('data').strip()

                    # once we've found a line that matches our key, stop looking
                    break

        self.slate_info = slate_info


def get_greatest_bounding_box(boxes):
    """
    Considering all the boxes create and return a new box based on the greatest bounds of each
    """
    if not boxes:
        return None

    bx, by, bw, bh = boxes[0].x, boxes[0].y, boxes[0].w, boxes[0].h
    for b in boxes:
        bx = min(b.x, bx)
        by = min(b.y, by)
        bw = max(b.w, bw)
        bh = max(b.h, bh)

    return Box(bx, by, bw, bh)


class Box:
    def __init__(self, x, y, w, h):
        self.x = x
        self.y = y
        self.w = w
        self.h = h

    def __hash__(self):
        """
        For creating sets, identifies the object as unique
        """
        return hash((self.x, self.y, self.w, self.h))

    def __getitem__(self, key):
        return [self.x, self.y, self.w, self.h][key]

    def __eq__(self, other):
        """
        Detect if this box is equal to another one
        """
        if self.x == other.x and self.y == other.y and self.w == other.w and self.h == other.h:
            return True
        return False

    def overlaps(self, other):
        """
        Detect if this box overlaps another box

        """
        # y axis
        if other.y <= self.y <= other.y + other.h or other.y <= self.y + self.h <= other.y + other.h:
            return True
        # x axis
        # not needed... yet
        return False


class TextBox(Box):
    def __init__(self, x, y, w, h, t):
        Box.__init__(self, x, y, w, h)
        self.text = t

    def __getitem__(self, key):
        return [self.x, self.y, self.w, self.h, self.text][key]

