import cv2
import numpy as np
from distutils.version import StrictVersion 

FOCAL_LENGTH = 567.22818181818
HORIZONTAL_FOV = 59.72083623
HORIZONTAL_PIXELS_TO_DEGREES = HORIZONTAL_FOV/640 
TAPE_WIDTH_ACTUAL = 5 #cm

def cv_const(simple_name):
    ocv3 = StrictVersion(cv2.__version__) >= StrictVersion('3.0.0') #are we using opencv3 or 2
    return getattr(cv2 if ocv3 else cv2.cv, ("" if ocv3 else "CV_") + simple_name)

def analyze(frame):
    """returns analyzed frame with bounding box drawn around reflective tape"""
    hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
    lower_tape_thresh = np.array([89, 39, 216])
    upper_tape_thresh = np.array([130, 253, 255])

    thresh_frame = cv2.inRange(hsv, lower_tape_thresh, upper_tape_thresh)
    contours = cv2.findContours(thresh_frame, cv_const("RETR_EXTERNAL"), cv_const("CHAIN_APPROX_NONE"))[1]
    contours = np.array(contours)
    if len(contours) > 0:
        max_area_contour = filter_contours(contours)
        rect = cv2.minAreaRect(max_area_contour)
        rect_width_px = rect[0][0] - rect [1][0]
        #print "distance to tape: %f" % (distance_to_marker(TAPE_WIDTH_ACTUAL, rect_width_px))
        if not hasattr(cv2, 'cv'):
            box = cv2.boxPoints(rect)
        else:
            box = cv2.cv.BoxPoints(rect)
        box = np.int0(box)
        cv2.drawContours(frame, [box], 0, (0, 0, 255), 3)
    return frame

def filter_contours(contours):
    """filters input contours and returns the one that matches
       the criteria defined by the method. current function is 
       to find the contour with the maximum area"""
    #vectorized_cnt_area = np.vectorize(cv2.contourArea)
    #contour_areas = vectorized_cnt_area(contours)
    contour_areas = []
    for cnt in contours:
        contour_areas.append(cv2.contourArea(cnt))
    return contours[np.argmax(contour_areas)]

def distance_to_marker(width_actual, width_px): #i forget how i got this formula, should probably figure it out
    return FOCAL_LENGTH * width_actual / width_px
