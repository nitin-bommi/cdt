import cv2, os, winsound
from system import app
import numpy as np


BASE = os.path.join(app.root_path, 'static', 'models')

face_cascade = cv2.CascadeClassifier(os.path.join(BASE, 'haarcascade_frontalface_default.xml'))
eye_cascade = cv2.CascadeClassifier(os.path.join(BASE, 'haarcascade_eye.xml'))
detector_params = cv2.SimpleBlobDetector_Params()
detector_params.filterByArea = True
detector_params.maxArea = 1500
detector = cv2.SimpleBlobDetector_create(detector_params)


def detect_faces(img, cascade):
    gray_frame = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    coords = cascade.detectMultiScale(gray_frame, 1.5, 5)
    if len(coords) > 1:
        biggest = (0, 0, 0, 0)
        for i in coords:
            if i[3] > biggest[3]:
                biggest = i
        biggest = np.array([i], np.int32)
    elif len(coords) == 1:
        biggest = coords
    else:
        return (None, (0, 0, 0, 0), 0)
    for (x, y, w, h) in biggest:
        frame = img[y:y + h, x:x + w]
    return (frame, (x, y, w, h), len(coords))


def detect_eyes(img, cascade):
    gray_frame = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    eyes = cascade.detectMultiScale(gray_frame, 1.3, 5)  # detect eyes
    width = np.size(img, 1)  # get face frame width
    height = np.size(img, 0)  # get face frame height
    left_eye = None
    right_eye = None
    for (x, y, w, h) in eyes:
        if y > height / 2:
            pass
        eyecenter = x + w / 2  # get the eye center
        if eyecenter < width * 0.5:
            left_eye = img[y:y + h, x:x + w]
        else:
            right_eye = img[y:y + h, x:x + w]
    return left_eye, right_eye


def store_activity(frame, category, name, exam, box, count=0, warnings=5):
    if category in ['CELL PHONE', 'LAPTOP']:
        count += 1
        winsound.Beep(2500, 100)
        cv2.putText(frame, category, (box[0]+10,box[1]+30), cv2.FONT_HERSHEY_COMPLEX,1,(0,0,255),2)
        if count%warnings == 0:
            path = os.path.join(BASE, 'logs', str(exam.id), str(name), f'{count//warnings}.png')
            cv2.imwrite(path, frame)
            print('Saved frame to file system')


def detect_objects(frame):
    configPath = os.path.join(BASE, 'models', 'ssd_mobilenet_v3_large_coco_2020_01_14.pbtxt')
    weightsPath = os.path.join(BASE, 'models', 'frozen_inference_graph.pb')
    net = cv2.dnn_DetectionModel(weightsPath, configPath)
    classNames= []
    classIds, confs, bbox = net.detect(frame, confThreshold=0.5)
    bbox = list(bbox)
    confs = list(np.array(confs).reshape(1,-1)[0])
    confs = list(map(float,confs))

    indices = cv2.dnn.NMSBoxes(bbox, confs, 0.5, 0.2)
    for i in indices:
        i = i[0]
        box = bbox[i]
        x,y,w,h = box[0],box[1],box[2],box[3]
        cv2.rectangle(frame, (x,y), (x+w,h+y), color=(0, 255, 0), thickness=2)
        category = classNames[classIds[i][0]-1].upper()
        cv2.putText(frame, category, (box[0]+10,box[1]+30), cv2.FONT_HERSHEY_COMPLEX,1,(0,255,0),2)
        store_activity(frame, category, box)


def cut_eyebrows(img):
    height, width = img.shape[:2]
    eyebrow_h = int(height / 4)
    img = img[eyebrow_h:height, 0:width]  # cut eyebrows out (15 px)

    return img


def blob_process(img, threshold, detector):
    gray_frame = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    _, img = cv2.threshold(gray_frame, threshold, 255, cv2.THRESH_BINARY)
    img = cv2.erode(img, None, iterations=2)
    img = cv2.dilate(img, None, iterations=4)
    img = cv2.medianBlur(img, 5)
    keypoints = detector.detect(img)
    #print(keypoints)
    return keypoints


class Detector(object):
    def __init__(self):
        self.video = cv2.VideoCapture(0)
    
    def __del__(self):
        self.video.release()
    
    def get_frame(self):
        _, frame = self.video.read()
        frame = cv2.resize(frame, (640, 480))
        (face_frame, (x, y, w, h), persons) = detect_faces(frame, face_cascade)
        if face_frame is not None:
            cv2.rectangle(frame, (x, y), (x+w, y+h), (0, 255, 0), 2)
            if face_frame is not None:
                eyes = detect_eyes(face_frame, eye_cascade)
                for eye in eyes:
                    if eye is not None:
                        threshold = 55
                        eye = cut_eyebrows(eye)
                        keypoints = blob_process(eye, threshold, detector)
                        eye = cv2.drawKeypoints(eye, keypoints, eye, (0, 0, 255), cv2.DRAW_MATCHES_FLAGS_DRAW_RICH_KEYPOINTS)

            ret, jpeg = cv2.imencode('.jpg', frame)
            return (jpeg.tobytes(), persons)
        
        detect_objects(frame)



