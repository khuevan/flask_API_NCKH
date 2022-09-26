import os

# comment out below line to enable tensorflow outputs
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'
import tensorflow as tf

physical_devices = tf.config.experimental.list_physical_devices('GPU')
if len(physical_devices) > 0:
    tf.config.experimental.set_memory_growth(physical_devices[0], True)
from absl import app, flags, logging
from absl.flags import FLAGS
import core.utils as utils
from core.yolov4 import filter_boxes
from core.functions import *
from tensorflow.python.saved_model import tag_constants
from PIL import Image
import cv2
import numpy as np
from tensorflow.compat.v1 import ConfigProto
from tensorflow.compat.v1 import InteractiveSession
import calendar
import time
import datetime
import json

def check_boolean(count, crop):
    if count & crop:
        return "Count, Cutout"
    if count == False:
        if crop == False:
            return ""
        else: return "Crop"
    else: return "Count"

def datetime_now():
    x = datetime.datetime.now()
    return x.strftime("%x")

def main(
        framework='tf',
        weights='./checkpoints/yolov4-tiny-416',
        size=416,
        tiny=True,
        model='yolov4',
        images='./data/images/pine.jpg',
        output='./static/album-images/',
        iou=0.5,
        score=0.5,
        dont_show=False,
        info=False,
        crop=True,
        plate=False,
        counted=False,
        model_type="Pineapple",
        name_created= "Xuan Thien Bui"):

    data = []
    # get time to rename image
    times = calendar.timegm(time.gmtime())
    img_name = "Pineapple-" + str(times)
    img_name_folder_crop = times
    # path image
    path = output + img_name + '.png'
    # path crop image
    # crop_path = output + "/crop/"
    img_pathname = "./static/crop/"

    config = ConfigProto()
    config.gpu_options.allow_growth = True
    session = InteractiveSession(config=config)
    STRIDES, ANCHORS, NUM_CLASS, XYSCALE = utils.load_config(tiny, model)
    input_size = size
    images = [images]

    # print(images)

    # load model
    if framework == 'tflite':
        interpreter = tf.lite.Interpreter(model_path= weights)
    else:
        saved_model_loaded = tf.saved_model.load(weights, tags=[tag_constants.SERVING])

    # loop through images in list and run Yolov4 model on each
    for count, image_path in enumerate(images, 1):
        original_image = cv2.imread(image_path)

        original_image = cv2.cvtColor(original_image, cv2.COLOR_BGR2RGB)

        image_data = cv2.resize(original_image, (input_size, input_size))
        image_data = image_data / 255.

        # get image name by using split method
        image_name = image_path.split('/')[-1]
        image_name = image_name.split('.')[0]

        images_data = []
        for i in range(1):
            images_data.append(image_data)
        images_data = np.asarray(images_data).astype(np.float32)

        if framework == 'tflite':
            interpreter.allocate_tensors()
            input_details = interpreter.get_input_details()
            output_details = interpreter.get_output_details()
            interpreter.set_tensor(input_details[0]['index'], images_data)
            interpreter.invoke()
            pred = [interpreter.get_tensor(output_details[i]['index']) for i in range(len(output_details))]
            if model == 'yolov3' and tiny == True:
                boxes, pred_conf = filter_boxes(pred[1], pred[0], score_threshold=0.25,
                                                input_shape=tf.constant([input_size, input_size]))
            else:
                boxes, pred_conf = filter_boxes(pred[0], pred[1], score_threshold=0.25,
                                                input_shape=tf.constant([input_size, input_size]))
        else:
            infer = saved_model_loaded.signatures['serving_default']
            batch_data = tf.constant(images_data)
            pred_bbox = infer(batch_data)
            for key, value in pred_bbox.items():
                boxes = value[:, :, 0:4]
                pred_conf = value[:, :, 4:]

        # run non max suppression on detections
        boxes, scores, classes, valid_detections = tf.image.combined_non_max_suppression(
            boxes=tf.reshape(boxes, (tf.shape(boxes)[0], -1, 1, 4)),
            scores=tf.reshape(
                pred_conf, (tf.shape(pred_conf)[0], -1, tf.shape(pred_conf)[-1])),
            max_output_size_per_class=50,
            max_total_size=50,
            iou_threshold=iou,
            score_threshold=score
        )

        # format bounding boxes from normalized ymin, xmin, ymax, xmax ---> xmin, ymin, xmax, ymax
        original_h, original_w, _ = original_image.shape
        bboxes = utils.format_boxes(boxes.numpy()[0], original_h, original_w)

        # hold all detection data in one variable
        pred_bbox = [bboxes, scores.numpy()[0], classes.numpy()[0], valid_detections.numpy()[0]]

        list_bbox = {"Ripe": [], "Semi_Ripe": [], "Un_Ripe": []}
        for i in range(valid_detections.numpy()[0]):
            if int(classes.numpy()[0][i]) == 0:
                list_bbox["Ripe"].append({"id": i, "acc": float(scores.numpy()[0][i]), "classes": int(classes.numpy()[0][i])})
            if int(classes.numpy()[0][i]) == 1:
                list_bbox["Semi_Ripe"].append({"id": i, "acc": float(scores.numpy()[0][i]), "classes": int(classes.numpy()[0][i])})
            if int(classes.numpy()[0][i]) == 2:
                list_bbox["Un_Ripe"].append({"id": i, "acc": float(scores.numpy()[0][i]), "classes": int(classes.numpy()[0][i])})
            else: continue

        # read in all class names from config
        class_names = utils.read_class_names(cfg.YOLO.CLASSES)

        # by default allow all classes in .names file
        allowed_classes = list(class_names.values())

        # custom allowed classes (uncomment line below to allow detections for only people)
        # allowed_classes = ['person']

        # if crop flag is enabled, crop each detection and save it as new image
        crop_img = None
        if crop:
            crop_path = os.path.join(os.getcwd(),'static', 'crop', str(img_name_folder_crop))
            try:
                os.mkdir(crop_path)
            except FileExistsError:
                pass
            crop_img = crop_objects(cv2.cvtColor(original_image, cv2.COLOR_BGR2RGB), pred_bbox, crop_path, allowed_classes, img_name, img_pathname, img_name_folder_crop)

        # # if ocr flag is enabled, perform general text extraction using Tesseract OCR on object detection bounding box
        # if FLAGS.ocr:
        #     ocr(cv2.cvtColor(original_image, cv2.COLOR_BGR2RGB), pred_bbox)

        # if count flag is enabled, perform counting of objects
        if counted:
            # count objects found
            counted_classes = count_objects(pred_bbox, by_class=False, allowed_classes=allowed_classes)
            # loop through dict and print
            for key, value in counted_classes.items():
                print("Number of {}s: {}".format(key, value))
            image = utils.draw_bbox(original_image, pred_bbox, info, counted_classes,
                                    allowed_classes=allowed_classes, read_plate=plate)
            # print(pred_bbox, info)
        else:
            image = utils.draw_bbox(original_image, pred_bbox, info, allowed_classes=allowed_classes,
                                    read_plate=plate)
            # print(pred_bbox, info)

        image = Image.fromarray(image.astype(np.uint8))
        if not dont_show:
            image.show()

        image = cv2.cvtColor(np.array(image), cv2.COLOR_BGR2RGB)
        cv2.imwrite(output + str(img_name) + '.png', image)

        username_id = name_created
        data = {"user-created" : username_id,
                "date-created": datetime_now(),
                "image": str(img_name) + '.png',
                "path": path,
                "list_box": list_bbox,
                "crop_path": crop_img,
                "model_type": model_type,
                "function": check_boolean(counted, crop)}
        return data

if __name__ == '__main__':
    # try:
    #     app.run(main)
    # except SystemExit:
    #     pass
    data = main()
    print(data)
