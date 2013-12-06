FaekCast
========

Capture Banshee (Or any other application including Audio out of system) and create a HTTP MPEG stream to cast it to ChromeCast using Chromium browser extension on Linux box (with PulseAudio and Jack using ASLA).

Note: This is just a prototype for demonstration and the perfomance is not at all production ready. Use icecast2 + darkice to stream your audio out for production quality output (Approx. 10 second lag).

Dependencies:
-------------

Jack C library
Py-Jack (Python bindings for Jack)
Numpy
Scipy
Pydub (Audio transcoding module for Python, non realtime)

Starting the stream:
--------------------

1. Edit the file (with sudo previlleges): /etc/pulse/default.pa
Add the following lines (remove them when you shutdown the jack server):
```
# Make JACK work
### Load audio drivers statically
load-module module-jack-sink
load-module module-jack-source
```
2. pulseaudio --kill
3. pasuspender -- jackd -d alsa

Stopping the stream:
--------------------

1. Ctrl+C (To kill the jackd process)
2. Remove the lines added in step 1 of startup from the file.
3. pulseaudio --start
4. killall indicator-sound-service

TODO:
-----

1. Automate start/stop and installation of application (including dependencies).
2. Add a GUI.
3. Port the application to C and transcode audio in realtime (to boost performance).
