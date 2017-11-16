#!/usr/bin/python
import cv2 #version 2.4
import numpy as np
from time import sleep
import argparse
import analyzer
from distutils.version import StrictVersion 
import Queue
from threading import Thread
import flask
DEFAULT_PORT = 5800 #ports 5800 through 5810 are designated for team use in FMS whitepaper
CAM_NUMS = [0]#default camera to use capture
FPS = 24 #frames per second
IMG_SIZE = (320,180) #(width, height) in pixels 

#####################################################
# command to properly adjust brightness run on tx1  #
#v4l2-ctl -c exposure_auto=1 -c exposure_absolute=10#
#####################################################

frame_q = Queue.Queue(FPS) #store our processed frames that are ready to transmit
captures = [] #list of VideoCapture objects that refer to the cameras we have opened

def start_captures(cam_nums):
    """start all of the video capture objects and store references to them in an instance variable"""
    captures = []
    for num in cam_nums:
        captures.append(cv2.VideoCapture(num))#append the VideoCapture to our list of captures
    return captures

def get_raw_frames(captures):
    """pull a frame from all capture objects and return a list of the captured frames"""
    frames = []

    for capture in captures:
        ret, frame = capture.read()#get a frame from the camera
        frames.append(frame)

    return frames

def process_frames(frames):
    """analyze all of the frames in frames and pack them into a single image to send over network"""
    processed_frames = []
    for frame in frames:
        if frame is not None:
            #analyze the frame, then shrink it so we use less bandwidth
            small_frame = cv2.resize(frame,#analyzer.analyze(frame), 
                                     IMG_SIZE,
                                     interpolation=cv2.INTER_AREA)
            processed_frames.append(small_frame)
    #if we have more than one capture open, we will get more than one frame, so we stitch the images
    #together by concatenating their representations as numpy arrays, then encode to JPG. The 
    #concatenation axis determines horizontal or vertical stacking. 1 for horizontal, 0 for vertical.
    if len(processed_frames) > 1:
        retval, buf = cv2.imencode('.jpeg', np.concatenate(processed_frames, axis=1))
    else:
        retval, buf = cv2.imencode('.jpeg', processed_frames[0])
    return buf

def queue_frame(frame, q):
    try: 
        q.put_nowait(frame)#queue the processed frame to be sent to the client
    #may need to be more proactive about managing the queue if bandwidth issues lead to frame dropping
    except Queue.Full:
        pass

def capture_forever():
    """get a capture object and serve until we get an interrupt"""
    while True: #infinite loops are good for servers
        #sleep(1.0/FPS)#control framerate
        frames = get_raw_frames(captures)#grab all of the raw frames from the capture objects
        processed_frame = process_frames(frames)#do CV processing, put frames together in single frame
        queue_frame(processed_frame, frame_q)#queue the frame for MJPG stream

app = flask.Flask('netcam')#create Flask app

def mjpg_gen():
    """a generator that infinitely yields MJPG frames"""
    while True:
        frame = frame_q.get().tostring()
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')

@app.route('/feed') 
def mjpg_feed():
    """route for actual MJPG feed"""
    return flask.Response(mjpg_gen(), mimetype='multipart/x-mixed-replace; boundary=frame')

if __name__ == '__main__':
    #start capture thread
    captures = start_captures(CAM_NUMS)
    cap_thread = Thread(target=capture_forever)
    cap_thread.daemon = True
    cap_thread.start()
    #run the flask app to start the server
    app.run(host='172.24.4.74', debug=True)
