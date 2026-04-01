from multiprocessing import Queue, Process
from visionQueueTest import vision
from tofQueueTest import tof

def main():
    q = Queue()

    visionProcess = Process(target=vision, args=(q,))
    tofProcess = Process(target=tof, args=(q,))

    visionProcess.start()
    tofProcess.start()

    latestObject = None
    latestDistance = None

    try:
        while True:
            data = q.get()

            if data["type"] == "vision":
                latestObject = data["object"]

            elif data["type"] == "sensor":
                latestDistance = data["distance"]

            print(f"{latestObject} at {latestDistance} meters")

    except KeyboardInterrupt:
        visionProcess.terminate()
        tofProcess.terminate()


if __name__ == "__main__":
    main()