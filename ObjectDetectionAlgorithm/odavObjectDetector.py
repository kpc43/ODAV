import cv2
import numpy as np
import onnxruntime as ort
import time
import json
from picamera2 import Picamera2
from multiprocessing import Queue

def process_yolo_outputs(q, outputs, frame, conf_threshold=0.3, nms_threshold=0.5):
    frameSize = 640
    className = ["Exit Sign"]

    h, w = frame.shape[:2]

    preds = outputs[0][0]
    preds = preds.T

    boxes = []
    scores = []
    class_ids = []
    
    for pred in preds:
        x, y, bw, bh = pred[:4]

        if len(pred) > 5: # multi-class
            obj_conf = pred[4]
            class_scores = pred[5:]

            class_id = np.argmax(class_scores)
            class_conf = class_scores[class_id]

            confidence = obj_conf * class_conf

        else: # single class
            confidence = pred[4]
            class_id = 0

        if confidence > conf_threshold:
            # Terminal output
            # print(f"Detected {className[class_id]}; Confidence = {confidence}")

            # Bounding box camera output
            x1 = int((x - bw / 2) * w / frameSize)
            y1 = int((y - bh / 2) * h / frameSize)
            bw = int(bw * w / frameSize)
            bh = int(bh * h / frameSize)

            # Send detection to queue
            detection = {
                "type": "vision",
                "object": className[class_id],
                "confidence": confidence,
                "position": [[x1, y1], [x1+bw, y1+bh]]
            }
            q.put(detection)
            
            boxes.append([x1, y1, bw, bh])
            scores.append(float(confidence))
            class_ids.append(class_id)
        else:
            # JSON output
            detection = {
                "type": "vision",
                "object": "None",
                "confidence": 0.0,
                "position": [[0, 0], [0, 0]]
            }
            q.put(detection)

    indices = cv2.dnn.NMSBoxes(boxes, scores, conf_threshold, nms_threshold)

    results = []
    if len(indices) > 0:
        for i in indices.flatten():
            x, y, bw, bh = boxes[i]
            results.append((x, y, bw, bh, scores[i], class_ids[i]))

            cv2.rectangle(frame, (x, y), (x + bw, y + bh), (0, 255, 0), 2)
            label = f"{className[class_ids[i]]}: {scores[i]:.2f}"
            cv2.putText(frame, label, (x, y - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)

    return frame, results

def vision(q: Queue):
    algorithm = "exitSignAlg.onnx"
    frameSize = 640

    # Model Optimizationms
    so = ort.SessionOptions()
    so.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_ALL
    so.intra_op_num_threads = 2
    so.inter_op_num_threads = 1

    # Load model
    session = ort.InferenceSession(algorithm, sess_otions=so)
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
            frame, detections = process_yolo_outputs(q, outputs, frame)

        if frameCount % 10 == 0:
            endTime = time.time()
            fps = 10 / (endTime - startTime)
            startTime = endTime
            print(f"FPS: {fps:.2f}")

        frameCount += 1

        cv2.waitKey(1)
        cv2.imshow("Camera", frame)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    cv2.destroyAllWindows()