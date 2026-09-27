import cv2

# เปิดกล้อง
cap = cv2.VideoCapture(0)

# ตัวอ่าน QR
qr_detector = cv2.QRCodeDetector()

while True:

    ret, frame = cap.read()

    if not ret:
        break

    # ตรวจ QR
    data, points, _ = qr_detector.detectAndDecode(frame)

    if points is not None and data != "":
        
        points = points[0]

        # หาจุดกึ่งกลาง QR
        center_x = int(points[:, 0].mean())
        center_y = int(points[:, 1].mean())

        print("QR:", data)
        print("Position:", center_x, center_y)

        # วาดกรอบ QR
        points = points.astype(int)

        for i in range(4):
            p1 = tuple(points[i])
            p2 = tuple(points[(i + 1) % 4])

            cv2.line(
                frame,
                p1,
                p2,
                (0, 255, 0),
                2
            )

        # วาดจุดกลาง
        cv2.circle(
            frame,
            (center_x, center_y),
            5,
            (0, 0, 255),
            -1
        )

        cv2.putText(
            frame,
            f"{data} ({center_x},{center_y})",
            (center_x, center_y - 10),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.6,
            (0, 255, 0),
            2
        )

    cv2.imshow("Camera", frame)

    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()