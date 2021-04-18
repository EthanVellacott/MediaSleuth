#MediaSleuth - Quicktime Investigator


###Description: 

A tool to make media inspection easy. \
A simple barebones cross-platform desktop application to check the properties of a Quicktime movie. \
Simply drag and drop your files in, and it will assess them. \
It is formatted like a table for 1-1 export into a html table, which can pass your results forward to others easily. \
You can find additional properties and customize your display by right clicking the table header. 

###Things it can check for :
- Quickly identify basic media properties - eg. framerate, resolution, bitrate
- Detect slate and content duration
- Black frames at the start and end 
- Recognize slate text
- Audio specifications (Designed with Australian broadcast specifications in mind)

###Dependencies : 
Windows (preferred package manage Chocolatey) \
Mac (preferred package manage Brew) 

Requires:
- ffmpeg

Optional:
- tesseract (Required for text recognition)

###Roadmap : 
- Configurable column settings
- Configurable specifications  
- List properties
- Aspect ratio checking
- Blanking checking
- Ability to read terminal output from processes

###Getting started : 
The test_media directory contains both a "compliant" movie file and an "uncompliant" one. \
These will produce different results when you drag them into the application.

