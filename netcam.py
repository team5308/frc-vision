#!/usr/bin/python
import socket 
import cv2 #version 2.4
import numpy as np
from time import sleep
import argparse
import signal
import sys
DEFAULT_PORT = 3000 #port to connect over
CAM_PORT = 0#default camera to use capture
FPS = 24 #frames per second
HEADER_LEN = 16 #longest possible length of encoded string

class Server():
    """Netcam server class. Provides functionality for serving webcam video over network"""
    def __init__(self, hostname='localhost', port=DEFAULT_PORT):
        self.hostname = hostname
        self.port  = port
        self.sock = None
        self.client = None

    def create_and_bind_sock(self):
        """get a socket to serve from"""
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM) #init socket
        self.sock.bind((args.host, args.port)) #bind that socket

    def wait_for_connection(self):
        """wait for our one client to connect"""
        self.sock.listen(1) #we only want 1 connection
        print "Listening on %s:%d. Waiting for client to connect..." % (socket.gethostname(), args.port)#output our current server scheme
        #since we only want one connection it is ok to block until they connect
        (self.client, self.client_addr) = self.sock.accept()
        print "Received connection from %s" % (self.client_addr[0])#show where the connection is coming from

    def serve_forever(self):
        """get a capture object and server until we get an interrupt"""
        capture = cv2.VideoCapture(CAM_PORT) #get an object so we can grab some frames
        while True: #infinite loops are good for servers
            sleep(1.0/FPS)#control framerate
            ret, frame = capture.read()#get a frame from the camera
            if frame is not None:
                small_frame = cv2.resize(frame, None, fx=.5, fy=.5, interpolation=cv2.INTER_AREA)#shrink the frame so we use less bandwidth
                sendable_frame = cv2.imencode('.jpg', small_frame)[1].tostring()#econde the shrunken frame and convert it to a string
                self.client.send(str(len(sendable_frame)).ljust(HEADER_LEN)+sendable_frame)#send the length of the image and the iamge to the client

    def start(self):
        """bundles all of the tasks needed to initialize and serve the video"""
        self.create_and_bind_sock()
        self.wait_for_connection()
        self.serve_forever()

    def interrupt_handler(self, signum, frame):
        """handler for keyboard interrupts that allows us to gracefully exit
           rather than forcefully terminate with things like sockets still open"""
        print "Keyboard Interrupt...closing sockets and exiting"
        print self.client
        if self.client is not None:
           self.client.close()
        if self.sock is not None:
           self.sock.close()
        sys.exit(0)#quit with no errors
 
class Client():
    def __init__(self, remote_host='localhost', remote_port=DEFAULT_PORT):
        self.remote_host = remote_host
        self.remote_port = remote_port

    def connect(self):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM) #grab a socket
        self.sock.connect((self.remote_host, self.remote_port))
        
    def recv_msg(self, sock, count):
        """recieves an aribitrarily sized message over sock"""
        data = b'' #we need a place to store the data
        while len(data) < count: #make sure we grab all the data
            packet = self.sock.recv(count - len(data))#grab as much as we can
            if not packet: #if there isn't any data we have nothing to return
               return None
            data += packet #append new info
        return data

    def recv_loop(self):
        while True:
            msg_len = int(self.sock.recv(HEADER_LEN))#get the length of the image data
            frame_data = self.recv_msg(self.sock, msg_len)#grab the frame
            frame_arr = np.fromstring(frame_data, np.uint8)#convert it to np array
            frame = cv2.imdecode(frame_arr)#decode it into something we can display
            if frame != None:#error checking
                cv2.imshow('CLIENT', frame)
            if cv2.waitKey(1) & 0xFF == ord('q'):#allow user to quit the client program
                break

    def start(self):
        self.connect()
        self.recv_loop()

    def interrupt_handler(self, signum, frame):
        """handler for keyboard interrupts that allows us to gracefully exit
           rather than forcefully terminate with things like sockets still open"""
        print "Keyboard Interrupt...closing sockets and exiting"
        if self.sock is not None:
           self.sock.close()
        cv2.destroyAllWindows()#only really needed for client 
        sys.exit(0)#quit with no errors


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="serves video from camera over the network")#create a command line argument parser
    parser.add_argument('host_type', action='store', type=str, choices=['server', 'client'])#add option to pick server or client
    parser.add_argument('-i', '--host', action='store', dest='host', type=str, default='localhost')#add option to set host
    parser.add_argument('-p', '--port', action='store', dest='port', type=int, default=DEFAULT_PORT)#add option to set port
    args = parser.parse_args()#parse the args fromt he command line

    if args.host_type == 'server':
        server = Server(port=args.port)#get a server instance
        signal.signal(signal.SIGINT, server.interrupt_handler)#start the interrupt handler
        server.start()
    if args.host_type == 'client':
        client = Client(remote_host=args.host, remote_port=args.port)
        signal.signal(signal.SIGINT, client.interrupt_handler)
        client.start()
