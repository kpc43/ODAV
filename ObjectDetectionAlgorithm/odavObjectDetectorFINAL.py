import cv2
import numpy as np
import onnxruntime as ort
import time
from picamera2 import Picamera2
from gpiozero import LED
yellowled = LED(17)
blueled = LED(27)

algorithm = "twoClassAlg.onnx"
# algorithm = "exitSignAlg.onnx"
frameSize = 640
className = ["Exit Sign", "Stairs"]

def process_yolo_outputs(outputs, frame, conf_threshold=0.4, nms_threshold=0.5):
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

        if confidence > conf_threshold:
            print(f"Detected {className[class_id]}; Confidence = {confidence:.2f}")

            scaleX = w / frameSize
            scaleY = h / frameSize
            x1 = int((x - bw / 2) * scaleX)
            y1 = int((y - bh / 2) * scaleY)
            bw_px = int(bw * scaleX)
            bh_px = int(bh * scaleY)

            boxes.append([x1, y1, bw_px, bh_px])
            scores.append(float(confidence))
            class_ids.append(class_id)


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

            cv2.rectangle(frame, (x, y), (x + bw, y + bh), (0, 255, 0), 2)
            label = f"{className[class_ids[i]]}: {scores[i]:.2f}"
            cv2.putText(frame, label, (x, y - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)

    return frame, results

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
        frame, detections = process_yolo_outputs(outputs, frame)

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
