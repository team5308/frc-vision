import socket 
import cv2
import numpy as np
from time import sleep
SERVER_IP = '172.24.2.76'
PORT = 3000 #port on which the server is listening
HEADER_LEN = 16 #length of message describing the length of the actual image data

sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM) #grab a socket
sock.connect((HOST, PORT)) #connect to that server

def recv_msg(sock, count):
    """recieves an aribitrarily sized message over sock"""
    data = b'' #we need a place to store the data
    while len(data) < count: #make sure we grab all the data
        packet = sock.recv(count - len(data))#grab as much as we can
        if not packet: #if there isn't any data we have nothing to return
           return None
        data += packet #append new info
    return data

while True:
    msg_len = int(sock.recv(HEADER_LEN))#get the length of the image data
    frame_data = recv_msg(sock, msg_len)#grab the frame
    frame_arr = np.fromstring(frame_data, np.uint8)#convert it to np array
    frame = cv2.imdecode(frame_arr, cv2.IMREAD_COLOR)#decode it into something we can display
    if frame != None:#error checking
        cv2.imshow('CLIENT', frame)
    if cv2.waitKey(1) & 0xFF == ord('q'):#allow user to quit the client program
        break

#some cleanup stuff
cv2.destroyAllWindows()
s.close()
