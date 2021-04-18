"""
To support checking the audio properties of the media

Currently:
    volume maximum
    durations of silence
    loudness values

TBD
    number of tracks

For reference :
    https://lokomotion.com.au/tv-commercial-broadcast-standards/ (2019)
    permitted maximum level peak program meter (PPM) -9dBFS assuming peak levels are infrequent and less than 10ms
    12 frames of complete silence at the head and tail within the duration of the TVC
    Also 12 frames of silence in the vision at head and tail - eg from 01:00:00:00 to 01:00:00:12 should be silent

    All the above is baked into the MediaInspection
"""

import ext.ffmpeg as ffmpeg


def get_max_volume(file):
    return ffmpeg.VolumeDetection(file).max_volume()


def is_max_volume_less_than(file, volume_max=-9):
    a = ffmpeg.VolumeDetection(file)

    if a.max_volume() < volume_max:
        return True
    return False


def get_max_volume_for_duration(file, seconds_from, seconds_to):
    checked_duration = ffmpeg.VolumeDetection(file, seconds_from, seconds_to)
    return checked_duration.max_volume()


def check_duration_for_silence(file, seconds_from, seconds_to):
    checked_duration = ffmpeg.VolumeDetection(file, seconds_from, seconds_to)

    silence = -91
    if checked_duration.max_volume() <= silence:
        return True
    return False


def is_loudness_in_bounds(file, lower_bound=-24, upper_bound=-22):
    checked_duration = ffmpeg.LoudnessDetection(file)

    if lower_bound < checked_duration.integrated_loudness() < upper_bound:
        return True
    return False
