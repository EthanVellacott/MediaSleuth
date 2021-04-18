"""
To support checking the aspect ratio of the media
"""

# todo this is from pre-python3.9, confirm there are no issues
# from fractions import gcd
from math import gcd


def get_aspect_ratio(width, height):
    common_factor = gcd(width, height)
    aspect_x = width / common_factor
    aspect_y = height / common_factor
    if aspect_x > 10 and aspect_y > 10:
        aspect_x = round(float(width) / float(height), 2)
        aspect_y = 1
    return aspect_x, aspect_y


def get_descriptive_aspect_ratio(width, height):
    aspect_ratio = '{}:{}'.format(*get_aspect_ratio(width, height))
    aspect_result = aspect_ratio

    # Based on these values:
    # https://www.digitalrebellion.com/webapps/aspectcalc (2019)
    popular_ratios = {
        '1:1': 'Square',
        '1.33:1': '4:3 video',
        '1.37:1': 'Academy ratio',
        '1.43:1': 'IMAX',
        '1.5:1': '3:2 video',
        '1.56:1': '14:9',
        '1.66:1': 'Super 16',
        '1.78:1': '16:9 widescreen video',
        '1.85:1': '35mm standard',
        '2.2:1': '70mm standard',
        '2.35:1': '35mm anamorphic pre-1970',
        '2.39:1': '35mm anamorphic post-1970',
        '4:3': 'Video',
        '3:2': 'Video',
        '14:9': 'Widescreen video',
        '16:9': 'Widescreen video',
    }

    # if there is a matching popular ratio, return it
    for r in popular_ratios:
        if r in aspect_ratio:
            aspect_result += ' - {}'.format(popular_ratios[r])
            return aspect_result

    # otherwise, just return the ratio by itself
    return aspect_result
