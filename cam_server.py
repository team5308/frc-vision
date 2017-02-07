import socket 
import cv2
import numpy as np
from time import sleep
PORT = 3000
HOST = '172.24.2.76' 
CAM_PORT = 0
s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.bind((HOST, PORT))
s.listen(1)
(clientsock, addr) = s.accept()

capture = cv2.VideoCapture(CAM_PORT)
while True:
    ret, frame = capture.read()
    result, encoded = cv2.imencode('.jpg', frame)
    data = np.array(encoded)
    stringData = data.tostring()
    clientsock.sendall(str(len(stringData)).ljust(16))
    clientsock.sendall(stringData)
    sleep(.042)
    
clientsock.close()
s.close()
