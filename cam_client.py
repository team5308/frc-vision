import socket 
import cv2
import numpy as np
from time import sleep
HOST = '172.24.2.76'
PORT = 3000
HEADER_LEN = 16
s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.connect((HOST, PORT))

def recv_msg(sock):
    """recieves 2 messages over conn, the first of which describes
       the length of the following message. returns the second message"""
    msg_len = int(sock.recv(HEADER_LEN))
    print msg_len
    return sock.recv(msg_len)

while True:
    stringData = recv_msg(s)
    data = np.fromstring(stringData, dtype='uint8')

    decoded_img = cv2.imdecode(data, 1)
    cv2.imshow('CLIENT', decoded_img)
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cv2.destroyAllWindows()
s.close()
