import os
# comment out below line to enable tensorflow outputs
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'
import time
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
import collections
# flags.DEFINE_string('framework', 'tf', '(tf, tflite, trt')
# flags.DEFINE_string('weights', './checkpoints/yolov4-416',
#                     'path to weights file')
# flags.DEFINE_integer('size', 416, 'resize images to')
# flags.DEFINE_boolean('tiny', False, 'yolo or yolo-tiny')
# flags.DEFINE_string('model', 'yolov4', 'yolov3 or yolov4')
# flags.DEFINE_string('video', './data/video/video.mp4', 'path to input video or set to 0 for webcam')
# flags.DEFINE_string('output', None, 'path to output video')
# flags.DEFINE_string('output_format', 'XVID', 'codec used in VideoWriter when saving video to file')
# flags.DEFINE_float('iou', 0.45, 'iou threshold')
# flags.DEFINE_float('score', 0.50, 'score threshold')
# flags.DEFINE_boolean('count', False, 'count objects within video')
# flags.DEFINE_boolean('dont_show', False, 'dont show video output')
# flags.DEFINE_boolean('info', False, 'print info on detections')
# flags.DEFINE_boolean('crop', False, 'crop detections from images')
# flags.DEFINE_boolean('plate', False, 'perform license plate recognition')

def datetime_now():
    x = datetime.datetime.now()
    return x.strftime("%x")

def check_boolean(count, crop):
    if count & crop:
        return "Count, Cutout"
    if count == False:
        if crop == False:
            return ""
        else: return "Crop"
    else: return "Count"

def main(
        framework='tf',
        weights='./checkpoints/yolov4-tiny-416',
        size=416,
        tiny=True,
        model='yolov4',
        video='./data/video/test.mp4',
        output='./static/album-videos/',
        output_format='XVID',
        iou=0.5,
        score=0.5,
        dont_show=True,
        info=False,
        crop=True,
        plate=False,
        counted=True,
        model_type="Pineapple",
        name_created= "Xuan Thien Bui"):

    data = []
    crop_folder = {}
    detect_folder = {}
    times = calendar.timegm(time.gmtime())
    img_name = "Pineapple-" + str(times)
    img_name_folder_crop = times
    output = output + str(img_name) + ".mp4"
    img_pathname_crop = "./static/crop_video/"

    config = ConfigProto()
    config.gpu_options.allow_growth = True
    session = InteractiveSession(config=config)
    STRIDES, ANCHORS, NUM_CLASS, XYSCALE = utils.load_config(tiny, model)
    input_size = size
    video_path = video
    # get video name by using split method
    video_name = video_path.split('/')[-1]
    video_name = video_name.split('.')[0]
    if framework == 'tflite':
        interpreter = tf.lite.Interpreter(model_path=weights)
        interpreter.allocate_tensors()
        input_details = interpreter.get_input_details()
        output_details = interpreter.get_output_details()
        print(input_details)
        print(output_details)
    else:
        saved_model_loaded = tf.saved_model.load(weights, tags=[tag_constants.SERVING])
        infer = saved_model_loaded.signatures['serving_default']

    # begin video capture
    try:
        vid = cv2.VideoCapture(int(video_path))
    except:
        vid = cv2.VideoCapture(video_path)

    out = None

    if output:
        # by default VideoCapture returns float instead of int
        width = int(vid.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(vid.get(cv2.CAP_PROP_FRAME_HEIGHT))
        fps = int(vid.get(cv2.CAP_PROP_FPS))
        codec = cv2.VideoWriter_fourcc(*output_format)
        out = cv2.VideoWriter(output, codec, fps, (width, height))

    frame_num = 0
    while True:
        return_value, frame = vid.read()
        if return_value:
            frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            frame_num += 1
            image = Image.fromarray(frame)
        else:
            print('Video has ended or failed, try a different video format!')
            break
    
        frame_size = frame.shape[:2]
        image_data = cv2.resize(frame, (input_size, input_size))
        image_data = image_data / 255.
        image_data = image_data[np.newaxis, ...].astype(np.float32)
        start_time = time.time()

        if framework == 'tflite':
            interpreter.set_tensor(input_details[0]['index'], image_data)
            interpreter.invoke()
            pred = [interpreter.get_tensor(output_details[i]['index']) for i in range(len(output_details))]
            if model == 'yolov3' and tiny == True:
                boxes, pred_conf = filter_boxes(pred[1], pred[0], score_threshold=0.25,
                                                input_shape=tf.constant([input_size, input_size]))
            else:
                boxes, pred_conf = filter_boxes(pred[0], pred[1], score_threshold=0.25,
                                                input_shape=tf.constant([input_size, input_size]))
        else:
            batch_data = tf.constant(image_data)
            pred_bbox = infer(batch_data)
            for key, value in pred_bbox.items():
                boxes = value[:, :, 0:4]
                pred_conf = value[:, :, 4:]

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
        original_h, original_w, _ = frame.shape
        bboxes = utils.format_boxes(boxes.numpy()[0], original_h, original_w)

        pred_bbox = [bboxes, scores.numpy()[0], classes.numpy()[0], valid_detections.numpy()[0]]
        # print(pred_bbox)
        frame_image = 20
        if frame_num % frame_image == 0:
            list_bbox = {"Ripe": [], "Semi_Ripe": [], "Un_Ripe": []}
            frame_detect = 'frame_' + str(frame_num)
            for i in range(valid_detections.numpy()[0]):
                if int(classes.numpy()[0][i]) == 0:
                    list_bbox["Ripe"].append(
                        {"id": i, "acc": scores.numpy()[0][i], "classes": int(classes.numpy()[0][i])})
                if int(classes.numpy()[0][i]) == 1:
                    list_bbox["Semi_Ripe"].append(
                        {"id": i, "acc": scores.numpy()[0][i], "classes": int(classes.numpy()[0][i])})
                if int(classes.numpy()[0][i]) == 2:
                    list_bbox["Un_Ripe"].append(
                        {"id": i, "acc": scores.numpy()[0][i], "classes": int(classes.numpy()[0][i])})
                else:
                    continue
            detect_folder[str(frame_detect)] = list_bbox
            # print(list_bbox)
        # read in all class names from config
        class_names = utils.read_class_names(cfg.YOLO.CLASSES)

        # by default allow all classes in .names file
        allowed_classes = list(class_names.values())
        
        # custom allowed classes (uncomment line below to allow detections for only people)
        #allowed_classes = ['person']


        # if crop flag is enabled, crop each detection and save it as new image
        if crop:
            crop_rate = 20 # capture images every so many frames (ex. crop photos every 150 frames)
            crop_path = os.path.join(os.getcwd(), 'static', 'crop_videos', str(img_name))
            try:
                os.makedirs(crop_path)
            except FileExistsError:
                pass
            if frame_num % crop_rate == 0:
                final_path = os.path.join(crop_path, 'frame_' + str(frame_num))
                final_path_crop = 'frame_' + str(frame_num)
                try :
                    os.makedirs(final_path)
                except FileExistsError:
                    pass
                data = crop_objects_vid(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB), pred_bbox, final_path, allowed_classes,img_name,img_pathname_crop,final_path_crop)
                crop_folder[str(final_path_crop)] = data
            else:
                pass

        if counted:
            # count objects found
            counted_classes = count_objects(pred_bbox, by_class = True, allowed_classes=allowed_classes)
            # loop through dict and print
            # for key, value in counted_classes.items():
                # print("Number of {}s: {}".format(key, value))
            image = utils.draw_bbox(frame, pred_bbox, info, counted_classes, allowed_classes=allowed_classes, read_plate=plate)
        else:
            image = utils.draw_bbox(frame, pred_bbox, info, allowed_classes=allowed_classes, read_plate=plate)
        
        fps = 1.0 / (time.time() - start_time)
        # print("FPS: %.2f" % fps)
        result = np.asarray(image)
        # cv2.namedWindow("result", cv2.WINDOW_AUTOSIZE)
        result = cv2.cvtColor(image, cv2.COLOR_RGB2BGR)
        
        if not dont_show:
            cv2.imshow("result", result)
        
        if output:
            out.write(result)
        if cv2.waitKey(1) & 0xFF == ord('q'): break

    data = {"User created": name_created,
            "Date created": datetime_now(),
            "video": output,
            "list_box": detect_folder,
            "crop_path": crop_folder,
            "model_type": model_type,
            "function": check_boolean(counted, crop)}
    # from pprint import pprint
    # pprint(data)
    cv2.destroyAllWindows()

if __name__ == '__main__':
    try:
        app.run(main)
    except SystemExit:
        pass
