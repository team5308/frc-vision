import socket 
import cv2
import numpy as np
from time import sleep
PORT = 3000 #port to connect over
HOST = '172.24.2.76' #host IP to use
CAM_PORT = 0 #default camera to use capture
FPS = 24 #frames per second
HEADER_LEN = 16 #longest possible length of encoded string
sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM) #init socket
sock.bind((HOST, PORT)) #bind that socket
sock.listen(1) #listen (we only want 1 connection)
(client, addr) = s.accept() #wait for our very special client to connect

capture = cv2.VideoCapture(CAM_PORT) #get an object so we can grab some frames
while True: #infinite loops are good for servers
    sleep(1.0/FPS)#control framerate
    ret, frame = capture.read()#get a frame from the camera
    small_frame = cv2.resize(frame, None, fx=.5, fy=.5, interpolation=cv2.INTER_AREA)#shrink the frame so we use less bandwidth
    sendable_frame = cv2.imencode('.jpg', small_frame)[1].tostring()#econde the shrunken frame and convert it to a string
    client.send(str(len(sendable_frame)).ljust(HEADER_LEN)+sendable_frame)#send the length of the image and the iamge to the client

clientsock.close()#close the conneciton to the client
s.close()#close the socket on the host
