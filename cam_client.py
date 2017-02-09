import socket 
import cv2
import numpy as np
import cPickle as pickle
from time import sleep
HOST = '172.24.2.76'
PORT = 3000
RECV_SIZE = 691200 

s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.connect((HOST, PORT))

def recv_msg(sock, count):
    data = b''
    while len(data) < count:
        packet = sock.recv(count - len(data))
        if not packet:
           return None
        data += packet
    return data

while True:
    msg_len = int(s.recv(16))
    frame_data = recv_msg(s, msg_len)
    frame_arr = np.fromstring(frame_data, np.uint8)
    frame = cv2.imdecode(frame_arr, cv2.IMREAD_COLOR) 
    if frame != None:
        cv2.imshow('CLIENT', frame)
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cv2.destroyAllWindows()
s.close()
