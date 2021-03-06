#Source for findBoard: https://www.pyimagesearch.com/2014/04/21/building-pokedex-python-finding-game-boy-screen-step-4-6/
#Source for warpPerspective: https://www.pyimagesearch.com/2014/05/05/building-pokedex-python-opencv-perspective-warping-step-5-6/

# import the necessary packages
from skimage import exposure
import numpy as np
import imutils
import cv2
import math 

# adjustments
Precision = 0.12
Canny1 = 30
Canny2 = 265
TestValue = 150

# For frame retention between frames
LargestAreaFound = 1000
BiggestAreaContours = None
BestWarpFound = None

def getDistanceFromPoint(point, point2 = (0,0)):
    return math.sqrt((point[0] - point2[0])**2 + (point[1] - point2[1])**2)

def orderPoints(points):
    sortedList = sorted(points, key=getDistanceFromPoint)
    target = np.array(sortedList)

    # We can't trust the topRight and bottom left corners as they can flip. This is because we order based on distance from origin.
    # A slight rotation can therefore cause a difference and they will flip. However this is not the case with the top left and bottom
    # right corners. Compensate by making sure that the top right corner is the one with the larger x
    if (target[1][0] < target[2][0]):
        tmp = [target[1][0], target[1][1]] # done this way to pass actual value instead of reference
        target[1] = target[2]
        target[2] = tmp

    return target

def findBoard(image):
    global Precision, BiggestAreaContours, LargestAreaFound, Canny1, Canny2
    # compute the ratio of the old height
    # to the new height, clone it, and resize it
    ratio = image.shape[0] / 300.0
    orig = image.copy()
    image = imutils.resize(image, height = 300)
    # convert the image to grayscale, blur it, and find edges
    # in the image
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    gray = cv2.bilateralFilter(gray, 5, 17, 17)
    edged = cv2.Canny(gray, Canny1, Canny2)

    # FIND THE SCREEN
    # find contours in the edged image, keep only the largest
    # ones, and initialize our screen contour
    cnts = cv2.findContours(edged.copy(), cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
    cnts = imutils.grab_contours(cnts)
    cnts = sorted(cnts, key = cv2.contourArea, reverse = True)[:10]
    screenCnt = None
    area = None

    # loop over our contours WHICH ARE NOW SORTED IN ORDER FROM BIGGEST DOWN
    for c in cnts:
        # approximate the contour
        peri = cv2.arcLength(c, True)
        area = cv2.contourArea(c)

        # There is no way a tiny board can happen so limit min size
        if (area < LargestAreaFound-100):
            #print("area too small")
            continue
        
        # If it is the largest go with it
        elif (BiggestAreaContours is not None and area == LargestAreaFound):
            print("area equals biggest area")
            screenCnt = BiggestAreaContours
            break

        approxOutline = cv2.approxPolyDP(c, Precision * peri, True)

        # if our approximated contour has four points, then
        # we can assume that we have found our screen
        if len(approxOutline) >= 4:
            print("defining a new area")

            # flatten approx array (3D --> 2D)
            approx = approxOutline.ravel()

            unsorted_coords = []

            # loop through the approx and extract the coords
            for i in range(0, len(approx), 2): 
                x = approx[i] 
                y = approx[i + 1] 

                unsorted_coords.append((x,y))
    
                # for debugging - show coord of each point

                # String containing the co-ordinates. 
                string = str(x) + " " + str(y)  
    
                if(i == 0): 
                    # text on topmost co-ordinate. 
                    cv2.putText(image, "Arrow tip", (x, y), 
                                    cv2.FONT_HERSHEY_COMPLEX , 0.5, (255, 0, 0))  
                else: 
                    # text on remaining co-ordinates. 
                    cv2.putText(image, string, (x, y),  
                            cv2.FONT_HERSHEY_COMPLEX , 0.5, (0, 255, 0))  

            # Check if it is a valid shape by checking that the lines never cross

            # the coords are not relative to head but to top left of window. So re-organize them to make it more consistent.
            # top left becomes first entry and bottom right becomes last entry
            coords = orderPoints(unsorted_coords)

            
            # if we made it this far it is a good contour and so we can save it
            LargestAreaFound = area
            BiggestAreaContours = approxOutline

            screenCnt = approxOutline
            break

    if (screenCnt is None):
        screenCnt = BiggestAreaContours

    # show contours for debugging
    if (screenCnt is not None): # BiggestAreaContours starts off null
        cv2.drawContours(image, [screenCnt], -1, (0, 255, 0), 3)

    return screenCnt, ratio, image, edged, area


def warpPerspective(orig, screenCnt, resizeRatio, area):
    global LargestAreaFound, BestWarpFound

    warp = None

    if (BestWarpFound is None or area != LargestAreaFound):
        # now that we have our screen contour, we need to determine
        # the top-left, top-right, bottom-right, and bottom-left
        # points so that we can later warp the image -- we'll start
        # by reshaping our contour to be our finals and initializing
        # our output rectangle in top-left, top-right, bottom-right,
        # and bottom-left order
        pts = screenCnt.reshape(4, 2)
        rect = np.zeros((4, 2), dtype = "float32")
        # the top-left point has the smallest sum whereas the
        # bottom-right has the largest sum
        s = pts.sum(axis = 1)
        rect[0] = pts[np.argmin(s)]
        rect[2] = pts[np.argmax(s)]
        # compute the difference between the points -- the top-right
        # will have the minumum difference and the bottom-left will
        # have the maximum difference
        diff = np.diff(pts, axis = 1)
        rect[1] = pts[np.argmin(diff)]
        rect[3] = pts[np.argmax(diff)]

        # multiply the rectangle by the original ratio
        rect *= resizeRatio
        # now that we have our rectangle of points, let's compute
        # the width of our new image
        (tl, tr, br, bl) = rect
        widthA = np.sqrt(((br[0] - bl[0]) ** 2) + ((br[1] - bl[1]) ** 2))
        widthB = np.sqrt(((tr[0] - tl[0]) ** 2) + ((tr[1] - tl[1]) ** 2))
        # ...and now for the height of our new image
        heightA = np.sqrt(((tr[0] - br[0]) ** 2) + ((tr[1] - br[1]) ** 2))
        heightB = np.sqrt(((tl[0] - bl[0]) ** 2) + ((tl[1] - bl[1]) ** 2))
        # take the maximum of the width and height values to reach
        # our final dimensions
        maxWidth = max(int(widthA), int(widthB))
        maxHeight = max(int(heightA), int(heightB))
        # construct our destination points which will be used to
        # map the screen to a top-down, "birds eye" view
        dst = np.array([
            [0, 0],
            [maxWidth - 1, 0],
            [maxWidth - 1, maxHeight - 1],
            [0, maxHeight - 1]], dtype = "float32")
        # calculate the perspective transform matrix and warp
        # the perspective to grab the screen
        M = cv2.getPerspectiveTransform(rect, dst)
    
        warp = cv2.warpPerspective(orig, M, (maxWidth, maxHeight))

        BestWarpFound = warp
    else:
        warp = BestWarpFound
    # convert the warped image to grayscale and then adjust
    # the intensity of the pixels to have minimum and maximum
    # values of 0 and 255, respectively
    warp = exposure.rescale_intensity(warp, out_range = (0, 1))

    return warp

def enhance(image):
    # See clarity.py
    # Somehow we're getting float64 image. convert it to something that cvtColor can understand
    image = (image*255).astype('uint8')
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    # adaptiveThreshold accepts single channel (grayscale) images
    # Good values are 198 for the threshold, and a low blockSize, e.g. 3
    at = cv2.adaptiveThreshold(gray, 198, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY_INV,3,2)

    foreground = cv2.bitwise_and(image, image, mask=at)

    # Get the background. Blur it an desaturate it
    #backgroundBlur = cv2.GaussianBlur(image, (15, 15), cv2.BORDER_DEFAULT)
    #backgroundBlur = cv2.bilateralFilter(image, 5, TestValue, TestValue)
    backgroundBlur = image # don't do any smoothing of the background

    amplifiedLight = 0.9
    addedGamma = 0.5
    # Make the background brighter prior to multiplication
    # Values 0.0, 0.9 and 0.5 (=128) seem to do well
    washedOut = cv2.addWeighted(backgroundBlur, 0.0, backgroundBlur, amplifiedLight, addedGamma*255)
    # remove the area taken care of by the edge detector
    # I can't figure out why, but we can't use mask=bitwise_not(at) like above.
    # BTW we convert to BGR is that the two arrays for bitwise_and must match number of channels
    mask = cv2.cvtColor(at, cv2.COLOR_GRAY2BGR)
    backgroundMask = cv2.bitwise_not(mask)
    background = cv2.bitwise_and(washedOut, backgroundMask)

    # Combine background with foreground
    composite = cv2.add(background, foreground)
    return composite

capture = cv2.VideoCapture(0)
capture = cv2.VideoCapture(0, cv2.CAP_DSHOW)
capture.set(cv2.CAP_PROP_FRAME_WIDTH, 2560)
capture.set(cv2.CAP_PROP_FRAME_HEIGHT, 1440)

if not capture.isOpened():
    print("Cannot open camera")
    exit()
while True:
    # get data from camera
    ret, image = capture.read()

    # process data
    contours, resizeRatio, annotatedImg, edges, area = findBoard(image)
    
    if contours is not None and len(contours) > 0:
        
        cropped = warpPerspective(image, contours, resizeRatio, area)
        enhanced = enhance(cropped)

        # show result
        cv2.imshow('Whiteboard: Original Image', imutils.resize(annotatedImg, height = 300))
        cv2.imshow('Whiteboard: Edges Image', imutils.resize(edges, height = 300))
        cv2.imshow('Whiteboard: Cropped Image', imutils.resize(cropped, height = 300))
        cv2.imshow('Whiteboard: Enhanced Image', imutils.resize(enhanced))

    else:
        cv2.imshow('Whiteboard: Original Image', imutils.resize(annotatedImg, height = 300))
        print("no suitable contours found")

    # # print diagnostics
    diagnostics = '{},{},{},{}'.format(Precision, Canny1, Canny2, TestValue)
    print(diagnostics)

    # the overly elaborate controls
    key = cv2.waitKey(1)
    if key == 27: # Escape - pause then when enter is pressed in the console, resume
        input("Press Enter to continue...")
    elif key == ord('q'): # exit 
        break
    elif key == ord('r'): # reset
        LargestAreaFound = 1000
        BiggestAreaContours = None
        BestWarpFound = None
    elif key == ord('w'):
        Precision += 0.001
    elif key == ord('W'):
        Precision -= 0.001
    elif key == ord('s'):
        TestValue += 5
    elif key == ord('S'):
        TestValue -= 5
   
    elif key == ord('a'):
        Canny1 += 1
    elif key == ord('A'):
        Canny1 -= 1
    elif key == ord('d'):
        Canny2 += 1
    elif key == ord('D'):
        Canny2 -= 1

# release resources
cv2.destroyAllWindows()