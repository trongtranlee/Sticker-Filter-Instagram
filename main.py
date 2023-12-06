import argparse
import numpy
import threading
import time
from threading import Thread
import cv2
from PIL import Image
import PIL.ImageTk as ImageTk
from tkinter import Tk, Button, Label
import tkinter.font as font


def UpdateSpriteStatus(num):
    global SPRITES
    SPRITES[num] = 1 - SPRITES[num]


def displaySprite(frame, sprite, x_offset, y_offset):
    (h, w) = (sprite.shape[0], sprite.shape[1])
    (imgH, imgW) = (frame.shape[0], frame.shape[1])

    if y_offset + h >= imgH:
        sprite = sprite[0: imgH - y_offset, :, :]

    if x_offset + w >= imgW:
        sprite = sprite[:, 0: imgW - x_offset, :]

    if x_offset < 0:
        sprite = sprite[:, abs(x_offset)::, :]
        w = sprite.shape[1]
        x_offset = 0

    for c in range(3):
        frame[y_offset: y_offset + h, x_offset: x_offset + w, c] = sprite[:, :, c] * (
            sprite[:, :, 3] / 255.0
        ) + frame[y_offset: y_offset + h, x_offset: x_offset + w, c] * (
            1.0 - sprite[:, :, 3] / 255.0
        )
    return frame


def applyHaarCascade(img, haar_cascade, scaleFact=1.1, minNeigh=5, minSizeW=30):
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    features = haar_cascade.detectMultiScale(
        gray,
        scaleFactor=scaleFact,
        minNeighbors=minNeigh,
        minSize=(minSizeW, minSizeW),
        flags=cv2.CASCADE_SCALE_IMAGE,
    )
    return features


def orientSpriteRelative(sprite, head_width, head_ypos):
    (h_sprite, w_sprite) = (sprite.shape[0], sprite.shape[1])
    factor = 1.0 * head_width / w_sprite
    sprite = cv2.resize(sprite, (0, 0), fx=factor, fy=factor)
    (h_sprite, w_sprite) = (sprite.shape[0], sprite.shape[1])
    y_orig = (head_ypos - h_sprite)
    if (y_orig < 0):
        sprite = sprite[abs(y_orig)::, :, :]
        y_orig = 0
    return (sprite, y_orig)


def applySpriteTop(image, path2sprite, w, x, y):
    sprite = cv2.imread(path2sprite, -1)
    (sprite, y_final) = orientSpriteRelative(sprite, w, y)
    image = displaySprite(image, sprite, x, y_final)


def applySpriteInternal(image, sprite_path, haar_filter, x_offset, y_offset, y_offset_image,
                        adjust2feature, desired_width, x, y, w, h,):
    sprite = cv2.imread(sprite_path, -1)
    (h_sprite, w_sprite) = (sprite.shape[0], sprite.shape[1])

    xpos = x + x_offset
    ypos = y + y_offset
    factor = 1.0 * desired_width / w_sprite

    sub_img = image[y + int(y_offset_image): y + h, x: x + w, :]

    feature = applyHaarCascade(sub_img, haar_filter, 1.3, 10, 10)
    if len(feature) != 0:
        xpos, ypos = x, y + feature[0, 1]
        if adjust2feature:
            mustacheSize = 1.2
            factor = 1.0 * (feature[0, 2] * mustacheSize) / w_sprite
            xpos = (x + feature[0, 0] -
                    int(feature[0, 2] * (mustacheSize - 1) / 2))
            ypos = (y + y_offset_image +
                    feature[0, 1] - int(h_sprite * factor))

    sprite = cv2.resize(sprite, (0, 0), fx=factor, fy=factor)
    image = displaySprite(image, sprite, int(xpos), int(ypos))


def imageOverlayLoop(runEvent, read_camera=0):
    global panelOne
    global SPRITES
    video_capture = cv2.VideoCapture(read_camera)
    video_capture.set(cv2.CAP_PROP_FRAME_WIDTH, 648)
    video_capture.set(cv2.CAP_PROP_FRAME_HEIGHT, 486)
    (x, y, w, h) = (0, 0, 10, 10)

    haar_faces = cv2.CascadeClassifier("D:\Computer Vision\Selfie-Filter-Application-master\cascades\haarcascade_frontalface_default.xml")
    haar_eyes = cv2.CascadeClassifier("D:\Computer Vision\Selfie-Filter-Application-master\cascades\haarcascade_eye.xml")
    haar_mouth = cv2.CascadeClassifier("D:\Computer Vision\Selfie-Filter-Application-master\cascades\Mouth.xml")
    # chưa thêm xong filter cho mũi 
    haar_nose = cv2.CascadeClassifier("D:\\Computer Vision\\Selfie-Filter-Application-master\\cascades\\Nose.xml")

    while runEvent.is_set():  # while thread is active
        ret, image = video_capture.read()
        image = cv2.flip(image, 1)

        if not ret:
            print("Error capturing camera feed, exiting")
            break

        faces = applyHaarCascade(image, haar_faces, 1.3, 5, 30)
        # (x,y,w,h) = (faces[0,0],faces[0,1],faces[0,2],faces[0,3])
        for (x, y, w, h) in faces:

            if SPRITES[0]:
                applySpriteTop(image, "./sprites/crown.png", w, x, y)
                #applySpriteTop(image, "./sprites/te.png", w, x, y)

            if SPRITES[1]:
                applySpriteInternal(
                    image, "./sprites/mustache.png",
                    haar_mouth, w / 4, 2 * h / 3, h / 2, True, w / 2, x, y, w, h,)

            if SPRITES[2]:
                applySpriteInternal(
                    image, "./sprites/thuglife.png",
                    haar_eyes, 0, h / 3, 0, False, w, x, y, w, h,)

            if SPRITES[3]:
                applySpriteTop(
                    image, "./sprites/santahat.png", w, x, y)

                applySpriteInternal(
                    image, "./sprites/santabeard.png",
                    haar_mouth, 0, 2 * h / 3, h / 2, True, w, x, y, w, h,)

        image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        image = Image.fromarray(image)
        image = ImageTk.PhotoImage(image)
        panelOne.configure(image=image)
        panelOne.image = image

    video_capture.release()


appParser = argparse.ArgumentParser()
appParser.add_argument("--read_camera", type=int, default=0)
appArgs = appParser.parse_args()

root = Tk()
root.title("Andrew's Facial Filter Application")
myFont = font.Font(size=10)

panelOne = Label(root)
panelOne.pack(side="top", padx=10, pady=10)

panelTwo = Label(root)
panelTwo.pack(side="bottom", padx=10, pady=10)

button1 = Button(panelTwo, text="Crown", width=20, height=3,
                 bg='#0052cc', fg='#ffffff', command=lambda: UpdateSpriteStatus(0))
button1['font'] = myFont
button1.pack(side="left", expand="no", padx="10", pady="10")

button2 = Button(panelTwo, text="Mustache", width=20, height=3,
                 bg='#0052cc', fg='#ffffff', command=lambda: UpdateSpriteStatus(1))
button2['font'] = myFont
button2.pack(side="left", expand="no", padx="10", pady="10")

button3 = Button(panelTwo, text="Sunglasses", width=20, height=3,
                 bg='#0052cc', fg='#ffffff', command=lambda: UpdateSpriteStatus(2))
button3['font'] = myFont
button3.pack(side="left", expand="no",  padx="10", pady="10")

button4 = Button(panelTwo, text="Santa", width=20, height=3,
                 bg='#0052cc', fg='#ffffff', command=lambda: UpdateSpriteStatus(3))
button4['font'] = myFont
button4.pack(side="left", expand="no", padx="10", pady="10")

SPRITES = [0, 0, 0, 0, ]

runEvent = threading.Event()
runEvent.set()
actionThread = Thread(target=imageOverlayLoop,
                      args=(runEvent, appArgs.read_camera))
actionThread.setDaemon(True)
actionThread.start()


def terminateAll():
    global root, runEvent, actionThread
    runEvent.clear()
    time.sleep(1)
    root.destroy()


root.protocol("WM_DELETE_WINDOW", terminateAll)
root.mainloop()
