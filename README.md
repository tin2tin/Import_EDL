# Introduction
Imports Video and Audio into the sequencer using an EDL file.

# Usage
Instructions
This importer is different from others in that its not found in the import menu.

Navigate to the sequencer and select and EDL file from the → 'EDL Import' panel.
Press Refresh Reels (This should list the reels or show a warning if the EDL can't be read)
For each reel select a movie file to load.
Press Import Video Sequence (.edl) to perform the import.
The EDL should load, replacing the existing selection.

# Scanning for Media
To save time, there is an option to assign missing clip paths by scanning a path.

This is done running the Find Missing Reel Files operator. This performs a recursive, case-insensitive search for each reel which doesn't already point to a valid file.

Audio/Video files are matched against the reel name, If there is some text in the reels filepath field, the filename component is used as well as the reel name.

Partial matches are also checked, so the following resolutions are possible.

reel name tape_c --> /media/movie/Tape C.mov
reel name tape_c --> /media/movie/Tape C_001.AVI
reel name tape c --> /media/movie/my_tape_c.wav
If the reel name doesn't match the movie filename at all, you can type in some identifier in the filepath field before finding media, then this will be checked against when matching media.

# Configuration
Each reel has a filepath and offset, the offset is used as an internal offset for the video data (not effecting the placement on the timeline).

# Examples
TODO

# Compatibility
Tested with CMX EDL files, others may work too.
Supported
Video
Wipe
Fades
Time Scaling
'bw' edits (solid black)

# Audio
Fades

# Known Issues
The addon doesn't deal with codecs or container formats, the video files must be supported by blender.
