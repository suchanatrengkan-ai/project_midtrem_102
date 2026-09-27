import cv2
import numpy as np

aruco_dict = cv2.aruco.getPredefinedDictionary(
    cv2.aruco.DICT_4X4_50
)

parameters = cv2.aruco.DetectorParameters()

detector = cv2.aruco.ArucoDetector(
    aruco_dict,
    parameters
)

images = {
    8: cv2.imread("images/arrows.jpg")
}

cap = cv2.VideoCapture(1)

while True:

    ret, frame = cap.read()

    if not ret:
        break

    corners, ids, rejected = detector.detectMarkers(frame)

    if ids is not None:

        for i, marker_id in enumerate(ids.flatten()):

            marker_id = int(marker_id)

            if marker_id != 8:
                continue

            dst = corners[i][0].astype("float32")

            center_x = int(dst[:, 0].mean())
            center_y = int(dst[:, 1].mean())

            cv2.polylines(
                frame,
                [dst.astype(int)],
                True,
                (0, 255, 0),
                3
            )

            img = images[8]

            if img is None:
                continue

            h, w = img.shape[:2]

            src_points = np.array([
                [0, 0],
                [w - 1, 0],
                [w - 1, h - 1],
                [0, h - 1]
            ], dtype="float32")

            matrix = cv2.getPerspectiveTransform(
                src_points,
                dst
            )

            warped = cv2.warpPerspective(
                img,
                matrix,
                (frame.shape[1], frame.shape[0])
            )

            mask = np.zeros(
                (frame.shape[0], frame.shape[1]),
                dtype=np.uint8
            )

            cv2.fillConvexPoly(
                mask,
                dst.astype(int),
                255
            )

            mask_inv = cv2.bitwise_not(mask)

            background = cv2.bitwise_and(
                frame,
                frame,
                mask=mask_inv
            )

            foreground = cv2.bitwise_and(
                warped,
                warped,
                mask=mask
            )

            frame = cv2.add(
                background,
                foreground
            )

            cv2.polylines(
                frame,
                [dst.astype(int)],
                True,
                (0, 255, 0),
                3
            )

            cv2.circle(
                frame,
                (center_x, center_y),
                5,
                (0, 0, 255),
                -1
            )

            cv2.putText(
                frame,
                "ID: 8",
                (center_x - 40, center_y - 20),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.7,
                (0, 255, 0),
                2
            )

    cv2.imshow(
        "ArUco Reader",
        frame
    )

    if cv2.waitKey(1) & 0xFF == ord("q"):
        break

cap.release()
cv2.destroyAllWindows()