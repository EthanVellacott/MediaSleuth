"""
To support identifying similar portions of luminance and chromaticity across the clip

Use ffmpeg to create a single proxy image file, downscaling each frame such that it becomes 1 pixel
Then we can use PIL to quickly parse information about the proxy file, and make inferences about the parent clip
Especially useful for identifying black frames at the head and tail of a video
And contiguous portions that might constitute a slate, or video content

TODO a strip that checks the contrast from frame to frame (similar to the way ikeys work in h264)
    If this was a greyscale matte, when could query the luma to find the contrast of a given frame
    Completely black frames would be identical to the last frame - which would be a helpful check to perform
"""

# builtin

import os
import subprocess
import uuid
import math

# external

from PIL import Image, ImageFile

# internal

import ext.ffmpeg as ffmpeg
import ext.systools as systools

from mediasleuth.platform import ffmpeg_cmd, temp_directory


class PixelSingle:
    def __init__(self, frame_number, pixel_coords, pixel):
        self.frame_number = frame_number
        self.pixel_coords = pixel_coords
        self.pixel_data = pixel
        self.luma = ColourManagement.calculate_pixel_lum(pixel[0], pixel[1], pixel[2])


class PixelChunk:
    # Manages chunks of single pixels and easily lets you calculate info about them
    def __init__(self, parent, first_item):
        self.parent = parent
        self.singles = [first_item, ]

    def __add__(self, other):
        # return a new pixelchunk that combines this chunk with the other
        new_singles = self.singles + other.singles
        new_chunk = PixelChunk(self.parent, new_singles[0])
        new_chunk.singles = new_singles
        return new_chunk

    def __getitem__(self, key):
        return self.singles[key]

    def __len__(self):
        return len(self.singles)

    def print_self(self):
        return '{} - {} frames {} seconds'.format(self.avg_luma(), self.get_framecount(), self.get_duration_seconds())

    def append(self, item):
        self.singles.append(item)

    def get_framecount(self):
        return len(self)

    def get_duration_seconds(self):
        return float(len(self)) / self.parent.fps

    def avg_luma(self):
        luma_vals = [x.luma for x in self.singles]
        return sum(luma_vals) / len(self)


class PixelStrip:
    def __init__(self, config, movie_filepath):
        # make a pixel strip and then pack the data into a queryable format here
        # fun
        # profit
        self.config = config
        self.movie_filepath = movie_filepath

        self.fps = 0
        self.framecount = 0
        self.get_info_from_movie()

        self.pixel_strip_path = temp_directory("pixel_strip")
        self.uuid = uuid.uuid1()

        self.tile_default_size = config["Pixel Strip"]["proxy_image_resolution"]
        self.proxy_frame_filetype = config["FFmpeg"]["proxy_filetype"]
        self.ffmpeg_log_level = config["FFmpeg"]["log_level"]

        self.create_pixel_strip(movie_filepath)

        # todo why this? commenting out for now, but I expect that it was to mitigate some kind of crash
        # time.sleep(1)

        # todo this throws errors on inspection
        #  but I also don't want to waste the effort instatiating a null image here
        self.image = ''
        self.width = 0
        self.height = 0
        self.read_image_from_pixel_strip()

        self.single_pixels = []
        self.get_single_pixels()

    def get_info_from_movie(self):
        s = ffmpeg.Stream(self.movie_filepath)
        self.fps = s.video_fps()
        self.framecount = s.video_framecount()

    def create_pixel_strip(self, movie_filepath):
        systools.mkdir(self.pixel_strip_path)

        pixel_strip_filepath = os.path.join(self.pixel_strip_path, "{}.{}".format(self.uuid, self.proxy_frame_filetype))

        cmd = '{} {} -y -i "{}" -frames 1 -vf "scale=1:1,tile={}x{}" "{}"'.format(ffmpeg_cmd(),
                                                                                  self.ffmpeg_log_level,
                                                                                  movie_filepath,
                                                                                  self.tile_default_size,
                                                                                  self.tile_default_size,
                                                                                  pixel_strip_filepath)
        print(cmd)

        subprocess.call(cmd, shell=True)

    def read_image_from_pixel_strip(self):
        ImageFile.LOAD_TRUNCATED_IMAGES = True

        pixel_strip_filepath = os.path.join(self.pixel_strip_path, "{}.{}".format(self.uuid, self.proxy_frame_filetype))

        self.image = Image.open(pixel_strip_filepath)
        self.width, self.height = self.image.size

    def get_single_pixels(self):
        self.single_pixels = []
        for y in range(self.height):
            for x in range(self.width):

                frame_number = x + (y * 512)
                if frame_number >= self.framecount:
                    continue

                coords = (x, y)
                pixel = self.image.getpixel(coords)

                new_pixel_single = PixelSingle(frame_number, coords, pixel)

                self.single_pixels.append(new_pixel_single)

    def get_luma_chunks(self, tolerance=0):
        # returns chunks of pixelsingles sorted by matching luma
        # you can provide a tolerance to group near matches

        chunks = []
        chunk_index = 0
        last_luma = 0
        tolerance = abs(tolerance)

        for p in self.single_pixels:
            if not last_luma:
                last_luma = p.luma
                # new_chunk = [p, ]
                new_chunk = PixelChunk(self, p)
                chunks.append(new_chunk)
                continue

            luma_min = last_luma - tolerance
            luma_max = last_luma + tolerance

            if luma_max >= p.luma >= luma_min:
                chunks[chunk_index].append(p)
                continue
            else:
                last_luma = p.luma
                # new_chunk = [p, ]
                new_chunk = PixelChunk(self, p)
                chunks.append(new_chunk)
                chunk_index += 1

        return chunks

    def normalize_chunks(self, chunks, count=1, seconds=0):
        """
        Group chunks by timing, eg no chunk can be smaller than a certain count
            so we could stipulate a minimum 1 second or 24 frames
            the orphaned chunks would just be appended to the previous chunk
        Functionally this just helps readability when debugging

        Not a fully finished idea
        Questions like :
            - where do the too-small chunks go? just appended to the last chunk?
            - will that result in bloat, or crashes, or cascades if we change the former chunk?
        """

        if seconds:
            count = seconds * self.fps

        new_chunks = []
        staged_chunk = ''

        for c in chunks:
            # if it's bigger than the limit just add it to the pile without staging
            if len(c) >= count:

                if staged_chunk:
                    # also add the last staged chunk in front
                    # and clear the last staged chunk
                    new_chunks.append(staged_chunk)
                    staged_chunk = None

                # print "Adding ad hoc chunk to list: ", c.print_self()
                new_chunks.append(c)
                continue

            # otherwise go through the rigomarole to assess it
            if not staged_chunk:
                # print "Staging chunk : ", c.print_self()
                staged_chunk = c
                continue

            if len(c) < count:
                # print "Appending chunk : ", c.print_self()
                staged_chunk += c
            else:
                # print "Adding staged chunk to list: ", staged_chunk.print_self()
                new_chunks.append(staged_chunk)
                # print "Staging chunk : ", c.print_self()
                staged_chunk = c

        # can't forget the final staged chunk
        # print "Adding staged chunk to list: ", staged_chunk.print_self()
        new_chunks.append(staged_chunk)

        return new_chunks

    def describe_luma_chunks(self, tolerance=0):
        """
        Print a description of luma chunks to the console
        """
        chunks = self.get_luma_chunks(tolerance=tolerance)
        for c in chunks:
            print(c[0].luma, ' ', len(c), ' frames ', c.get_duration_seconds(), ' seconds')
        return chunks

    def describe_normalized_luma_chunks(self, tolerance=0, count=24, seconds=0):
        """
        Print a description of normalized luma chunks to the console

        Not yet implemented
        """
        chunks = self.get_luma_chunks(tolerance=tolerance)
        chunks = self.normalize_chunks(chunks, count=count)
        for c in chunks:
            print(c.avg_luma(), ' ', len(c), ' frames ', c.get_duration_seconds(), ' seconds')
        return chunks


class ColourManagement:
    @staticmethod
    def calculate_pixel_lum(r, g, b, method=0):
        # From : 2019_08_06
        # https: // stackoverflow.com / questions / 596216 / formula - to - determine - brightness - of - rgb - color

        if method == 0:
            # Luminance(standard for certain colour spaces):
            # https://en.wikipedia.org/wiki/Relative_luminance
            return 0.2126 * r + 0.7152 * g + 0.0722 * b
        elif method == 1:
            # Luminance(perceived option 1):
            # https://www.w3.org/TR/AERT/#color-contrast (2019)
            return 0.299 * r + 0.587 * g + 0.114 * b
        elif method == 2:
            # Luminance(perceived option 2, slower to calculate):
            # http://alienryderflex.com/hsp.html (2019)
            # return sqrt(0.241 * r ^ 2 + 0.691 * r ^ 2 + 0.068 * b ^ 2)
            return math.sqrt(0.299 * r ^ 2 + 0.587 * r ^ 2 + 0.114 * b ^ 2)

    @staticmethod
    def calculate_pixel_avg(r, g, b):
        return (r+g+b) / 3
