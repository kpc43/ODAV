import cv2
import numpy as np
import onnxruntime as ort
import time
from picamera2 import Picamera2
from multiprocessing import Queue
import queue
from gpiozero import LED

algorithm = "odavFinalAlg.onnx"
frameSize = 640

# LEDs are in order of class
className = ["Elevator", "Exit Sign", "Person", "Stairs Down", "Stairs Up"]
yellowled = LED(17)
blueled = LED(27)

def process_yolo_outputs(qOut, outputs, frame, conf_threshold=0.4, nms_threshold=0.5):
    h, w = frame.shape[:2]

    preds = outputs[0][0]
    preds = preds.T

    boxes = []
    scores = []
    class_ids = []
    
    for pred in preds:
        x, y, bw, bh = pred[:4]

        class_scores = pred[4:]
        class_id = np.argmax(class_scores)
        confidence = class_scores[class_id]

        if class_id >= len(className):
            continue
        
        if class_id == 0: # Elevator
            if confidence > 0.4:
                scaleX = w / frameSize
                scaleY = h / frameSize
                x1 = int((x - bw / 2) * scaleX)
                y1 = int((y - bh / 2) * scaleY)
                bw_px = int(bw * scaleX)
                bh_px = int(bh * scaleY)

                if y1 > frameSize/2:
                    if x1 < frameSize/3:
                        quadrant = "left"
                    elif x1 > frameSize/3 and x1 < 2*frameSize/3:
                        quadrant = "center"
                    elif x1 > 2*frameSize/3:
                        quadrant = "right"

                boxes.append([x1, y1, bw_px, bh_px])
                scores.append(float(confidence))
                class_ids.append(class_id)

                # Clear values from queue not collected by main
                try:
                    while True:
                        qOut.get_nowait()
                except queue.Empty:
                    pass

                # Send detection to queue
                detection = {
                    "type": "vision",
                    "object": className[class_id],
                    "confidence": confidence,
                    "quadrant": quadrant
                }
                qOut.put(detection)
        elif class_id == 1: # Exit sign
            if confidence > 0.6:
                scaleX = w / frameSize
                scaleY = h / frameSize
                x1 = int((x - bw / 2) * scaleX)
                y1 = int((y - bh / 2) * scaleY)
                bw_px = int(bw * scaleX)
                bh_px = int(bh * scaleY)

                if y1 > frameSize/2:
                    if x1 < frameSize/3:
                        quadrant = "left"
                    elif x1 > frameSize/3 and x1 < 2*frameSize/3:
                        quadrant = "center"
                    elif x1 > 2*frameSize/3:
                        quadrant = "right"

                boxes.append([x1, y1, bw_px, bh_px])
                scores.append(float(confidence))
                class_ids.append(class_id)

                # Clear values from queue not collected by main
                try:
                    while True:
                        qOut.get_nowait()
                except queue.Empty:
                    pass

                # Send detection to queue
                detection = {
                    "type": "vision",
                    "object": className[class_id],
                    "confidence": confidence,
                    "quadrant": quadrant
                }
                qOut.put(detection)
        elif class_id == 2: # Person
            if confidence > 0.6:
                scaleX = w / frameSize
                scaleY = h / frameSize
                x1 = int((x - bw / 2) * scaleX)
                y1 = int((y - bh / 2) * scaleY)
                bw_px = int(bw * scaleX)
                bh_px = int(bh * scaleY)

                if y1 > frameSize/2:
                    if x1 < frameSize/3:
                        quadrant = "left"
                    elif x1 > frameSize/3 and x1 < 2*frameSize/3:
                        quadrant = "center"
                    elif x1 > 2*frameSize/3:
                        quadrant = "right"

                boxes.append([x1, y1, bw_px, bh_px])
                scores.append(float(confidence))
                class_ids.append(class_id)

                # Clear values from queue not collected by main
                try:
                    while True:
                        qOut.get_nowait()
                except queue.Empty:
                    pass

                # Send detection to queue
                detection = {
                    "type": "vision",
                    "object": className[class_id],
                    "confidence": confidence,
                    "quadrant": quadrant
                }
                qOut.put(detection)
        elif class_id == 3: # Stairs Down
            if confidence > 0.5:
                scaleX = w / frameSize
                scaleY = h / frameSize
                x1 = int((x - bw / 2) * scaleX)
                y1 = int((y - bh / 2) * scaleY)
                bw_px = int(bw * scaleX)
                bh_px = int(bh * scaleY)

                if y1 > frameSize/2:
                    if x1 < frameSize/3:
                        quadrant = "left"
                    elif x1 > frameSize/3 and x1 < 2*frameSize/3:
                        quadrant = "center"
                    elif x1 > 2*frameSize/3:
                        quadrant = "right"

                boxes.append([x1, y1, bw_px, bh_px])
                scores.append(float(confidence))
                class_ids.append(class_id)

                # Clear values from queue not collected by main
                try:
                    while True:
                        qOut.get_nowait()
                except queue.Empty:
                    pass

                # Send detection to queue
                detection = {
                    "type": "vision",
                    "object": className[class_id],
                    "confidence": confidence,
                    "quadrant": quadrant
                }
                qOut.put(detection)
        elif class_id == 4: # Stairs Up
            if confidence > 0.4:
                scaleX = w / frameSize
                scaleY = h / frameSize
                x1 = int((x - bw / 2) * scaleX)
                y1 = int((y - bh / 2) * scaleY)
                bw_px = int(bw * scaleX)
                bh_px = int(bh * scaleY)

                if y1 > frameSize/2:
                    if x1 < frameSize/3:
                        quadrant = "left"
                    elif x1 > frameSize/3 and x1 < 2*frameSize/3:
                        quadrant = "center"
                    elif x1 > 2*frameSize/3:
                        quadrant = "right"

                boxes.append([x1, y1, bw_px, bh_px])
                scores.append(float(confidence))
                class_ids.append(class_id)

                # Clear values from queue not collected by main
                try:
                    while True:
                        qOut.get_nowait()
                except queue.Empty:
                    pass

                # Send detection to queue
                detection = {
                    "type": "vision",
                    "object": className[class_id],
                    "confidence": confidence,
                    "quadrant": quadrant
                }
                qOut.put(detection)


        indices = []
        for c in set(class_ids):
            idxs = [i for i in range(len(class_ids)) if class_ids[i] == c]
            c_boxes = [boxes[i] for i in idxs]
            c_scores = [scores[i] for i in idxs]

            c_indices = cv2.dnn.NMSBoxes(c_boxes, c_scores, conf_threshold, nms_threshold)

            if len(c_indices) > 0:
                for i in c_indices.flatten():
                    indices.append(idxs[i])


    results = []
    if len(indices) > 0:
        for i in indices:
            x, y, bw, bh = boxes[i]
            results.append((x, y, bw, bh, scores[i], class_ids[i]))

            if class_ids[i] == 0:
                yellowled.on()
            if class_ids[i] == 1:
                blueled.on()
    else:
        yellowled.off()
        blueled.off()

    return frame, results

def vision(qOut: Queue):
    algorithm = "exitSignAlg.onnx"
    frameSize = 640

    # Model Optimizationms
    so = ort.SessionOptions()
    so.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_ALL
    so.intra_op_num_threads = 2
    so.inter_op_num_threads = 1

    # Load model
    session = ort.InferenceSession(algorithm, sess_options=so)
    input_name = session.get_inputs()[0].name

    # Camera setup
    picam2 = Picamera2()
    picam2.configure(picam2.create_preview_configuration())
    picam2.start()

    startTime = time.time()
    frameCount = 0
    while True:
        frame = picam2.capture_array()
        frame = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)

        # Preprocess
        img = cv2.resize(frame, (frameSize,frameSize))
        img = img.astype(np.float32)/255.0
        img = np.transpose(img, (2,0,1))
        img = np.expand_dims(img, axis=0)

        if frameCount % 1 == 0:
            # Run inference
            outputs = session.run(None, {input_name: img})

            # Postprocess YOLO outputs here (NMS, boxes, classes)
            frame, detections = process_yolo_outputs(qOut, outputs, frame)

        if frameCount % 10 == 0:
            endTime = time.time()
            fps = 10 / (endTime - startTime)
            startTime = endTime
            print(f"FPS: {fps:.2f}")

        frameCount += 1
