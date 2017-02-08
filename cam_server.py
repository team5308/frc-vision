import socket 
import cv2
import numpy as np
from time import sleep
import cPickle as pickle
PORT = 3000
HOST = '172.24.2.76' 
CAM_PORT = 0
FPS = 24
s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.bind((HOST, PORT))
s.listen(1)
(clientsock, addr) = s.accept()

capture = cv2.VideoCapture(CAM_PORT)
while True:
    sleep(1.0/FPS)
    ret, frame = capture.read()
    width, height = frame.shape[:2]
    small_frame = cv2.resize(frame, None, fx=.5, fy=.5, interpolation=cv2.INTER_AREA)
    sendable_frame = cv2.imencode('.jpg', small_frame)[1].tostring()
    clientsock.send(str(len(sendable_frame)).ljust(16)+sendable_frame)

clientsock.close()
s.close()
