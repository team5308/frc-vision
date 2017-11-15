#!/usr/bin/python
import socket 
import cv2 #version 2.4
import numpy as np
from time import sleep
import argparse
import signal
import sys
import analyzer
from distutils.version import StrictVersion 
import cPickle
import Queue
from threading import Thread
DEFAULT_PORT = 3000 #port to connect over
CAM_NUMS = [1]#default camera to use capture
FPS = 24 #frames per second
HEADER_LEN = 16 #longest possible length of encoded string

##################################################
#command to properly adjust brightness run on tx1#
#v4l2-ctl -c exposure_auto=1 exposure_absolute=10#
##################################################

class Server():
    """Netcam server class. Provides functionality for serving webcam video over network"""
    def __init__(self, hostname='localhost', port=DEFAULT_PORT, cam_nums=CAM_NUMS):
        self.hostname = hostname
        self.port  = port
        self.cam_nums = cam_nums
        self.sock = None
        self.client = None
        self.captures = []
        self.frame_queue = Queue.Queue(FPS)#maxlen of Q, don't get more than 1 second behind

    def create_and_bind_sock(self):
        """get a socket to serve from, and star the network thread"""
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM) #init socket
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1) #forcibly bind socket
        self.sock.bind((self.hostname, self.port)) #bind that socket
        self.start_network_thread()#starts a new thread that handles sending data to client

    def wait_for_connection(self):
        """wait for our one client to connect"""
        self.sock.listen(1) #we only want 1 connection
        print "Listening on %s:%d. Waiting for client to connect..." % (self.hostname, self.port)#output our current server scheme
        #since we only want one connection it is ok to block until they connect
        (self.client, self.client_addr) = self.sock.accept()
        print "Received connection from %s" % (self.client_addr[0])#show where the connection is coming from

    def network_worker(self):
        """Logic for worker thread that takes items out of frame_queue and sends them over
        socket to the client"""
        print "Network worker running..."
        while True:
            frame_to_send = self.frame_queue.get()#this will block until an a frame is available
            pickled_frame = cPickle.dumps(frame_to_send)
            frame_header = str(len(pickled_frame)).ljust(HEADER_LEN)#padded length of message
            try:
                self.client.send(frame_header+pickled_frame)
            except socket.error:
                print "Connection closed by client."
                self.destroy()
            self.frame_queue.task_done()

    def start_network_thread(self):
        """starts up the thread that runs network_worker"""
        t = Thread(target=self.network_worker)
        t.daemon = True
        t.start()
        
    def start_captures(self):
        """start all of the video capture objects and store references to them in an instance variable"""
        for num in self.cam_nums:
            self.captures.append(cv2.VideoCapture(num))#append the VideoCapture to our list of captures
    
    def get_raw_frames(self):
        """pull a frame from all capture objects and return a list of the captured frames"""
        frames = []

        for capture in self.captures:
            ret, frame = capture.read()#get a frame from the camera
            frames.append(frame)

        return frames

    def process_frames(self, frames):
        """analyze all of the frames in frames and pack them into a single image to send over network"""
        processed_frames = []
        for frame in frames:
            if frame is not None:
                #analyze the frame, then shrink it so we use less bandwidth
                small_frame = cv2.resize(frame, #analyzer.analyze(frame), 
                                         (640, 360),
                                         interpolation=cv2.INTER_AREA)
                processed_frames.append(small_frame)
        if len(processed_frames) > 1:
            return np.concatenate(processed_frames, axis=1)
        return processed_frames[0]

    def queue_frame(self, frame):
        try: 
            self.frame_queue.put_nowait(frame)#queue the processed frame to be sent to the client
        except Queue.Full:
            pass
            #with self.frame_queue.mutex:
                #self.frame_queue.queue.clear()
    
    def send_frame(self, frame_to_send):
        pickled_frame = cPickle.dumps(frame_to_send)
        frame_header = str(len(pickled_frame)).ljust(HEADER_LEN)#padded length of message
        try:
            self.client.sendall(frame_header+pickled_frame)
        except socket.error:
            print "Connection closed by client."
            self.destroy()

    def serve_forever(self):
        """get a capture object and server until we get an interrupt"""
        self.start_captures()#loop through self.cam_nums and init capture objects for all those cams
        while True: #infinite loops are good for servers
            sleep(1.0/FPS)#control framerate
            frames = self.get_raw_frames()#grab all of the raw frames from the capture objects
            processed_frame = self.process_frames(frames)#do CV processing, put frames together in single frame
            #self.queue_frame(processed_frame)
            self.send_frame(processed_frame)

    def run(self):
        """bundles all of the tasks needed to initialize and serve the video"""
        self.create_and_bind_sock()
        self.wait_for_connection()
        self.serve_forever()

    def destroy(self, signum=None, frame=None):#three args are provided to comply with signal.signal interrupt handler
        """handler for keyboard interrupts or other events that 
           indicate the server should exit. Allows us to gracefully exit
           rather than forcefully terminate with things like sockets still open"""
        print "Cleaning up..."
        if self.client is not None:
           self.client.close()
        if self.sock is not None:
           self.sock.close()
        for capture in self.captures:
            if capture is not None:
                capture.release()
        print "Bye."
        exit()

class Client():
    def __init__(self, remote_host='localhost', remote_port=DEFAULT_PORT):
        self.remote_host = remote_host
        self.remote_port = remote_port
        #handle different versions of opencv
        ocv3 = StrictVersion(cv2.__version__) >= StrictVersion('3.0.0') #are we using opencv3 or 2
        if ocv3:
            self.IMREAD_COLOR = cv2.IMREAD_COLOR
        else:
            self.IMREAD_COLOR = cv2.CV_LOAD_IMAGE_COLOR

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
        cv2.namedWindow('CLIENT', cv2.WINDOW_NORMAL)#make our window resizeable
        print "Press q to quit"
        while True:
            msg_len_str = self.sock.recv(HEADER_LEN)#get the length of the image data
            msg_len = 0
            if not self.transmission_ended(msg_len_str):#check for EOT
                msg_len = int(msg_len_str)
            else:#if EOT, we outta here
                print "Connection closed by server."
                self.destroy()
            frame_data = self.recv_msg(self.sock, msg_len)#grab the frame
            frame = cPickle.loads(frame_data)#np.fromstring(frame_data, np.uint8)#convert it to np array
            #frame = cv2.imdecode(frame_arr, self.IMREAD_COLOR)#decode it into something we can display
            if frame is not None:#error checking
                cv2.imshow('CLIENT', frame)
            if cv2.waitKey(1) & 0xFF == ord('q'):#allow user to quit the client program
                break
            if cv2.waitKey(1) & 0xFF == ord('s'):
                cv2.imwrite('savefile.jpg', frame)
        self.destroy()         

    def run(self):
        self.connect()
        self.recv_loop()

    def transmission_ended(self, data):
        """checks to see if there is empty data to handle appropriately"""
        if len(data) > 0: 
            return False
        else: 
            return True

    def destroy(self, signum=None, frame=None):
        """see Server.destroy"""
        print "Cleaning up..."
        if self.sock is not None:
           self.sock.close()
        cv2.destroyAllWindows()#only really needed for client 
        print "Bye."
        exit()

def start_server(args):
    server = Server(hostname=args.addr, port=args.port, cam_nums=args.cam_nums)#get a server instance
    signal.signal(signal.SIGINT, server.destroy)#start the interrupt handler
    server.run()

def start_client(args):
    client = Client(remote_host=args.addr, remote_port=args.port)
    signal.signal(signal.SIGINT, client.destroy)
    client.run()

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="serves video from camera over the network")#create a command line argument parser
    subparsers = parser.add_subparsers()

    server_parser = subparsers.add_parser('server')
    server_parser.add_argument('-c', '--cam-num', action='store', dest='cam_nums', type=int, default=CAM_NUMS)
    server_parser.set_defaults(func=start_server)#start server when server is chosen
    client_parser = subparsers.add_parser('client')
    client_parser.set_defaults(func=start_client)#start a client when they tell us to
    """Note: connection only works over exact host bound,
       i.e. running netcam server localhost and then trying to
       netcam client 127.0.0.1 will likely fail"""
    parser.add_argument('addr', action='store', type=str)#we need to know what host to bind. 
    parser.add_argument('-p', '--port', action='store', dest='port', type=int, default=DEFAULT_PORT)#add option to set port
    args = parser.parse_args()#parse the args fromt the command line
    args.func(args)#actually start the client/server
