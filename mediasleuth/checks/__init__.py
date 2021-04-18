"""
Each of these represents support for various checks on the media

Full support :

pixel_strip
The pixel strip is a way of summarizing the colour and luminance of a video over it's runtime
The PixelStrip class makes the working files, and provides an interface for that information

slate_reader
The slate reader is able to take the first frame of video, and read the text from it for easy validation
The SlateReader class makes the working files, and provides an interface for that information

Partial support :

audio
This provides various functions to query the volume and loudness of a file
All the processing occurs through the ffmpeg ext package

aspect
This provides some functions to find and format an aspect ratio
This is not implemented yet

"""