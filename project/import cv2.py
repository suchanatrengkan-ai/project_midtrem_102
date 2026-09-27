import cv2

# เปิดกล้อง
cap = cv2.VideoCapture(0)

# ตัวอ่าน QR Code
qr_detector = cv2.QRCodeDetector()

while True:
    ret, frame = cap.read()

    if not ret:
        print("เปิดกล้องไม่ได้")
        break

    # ตรวจหาและอ่าน QR
    data, points, _ = qr_detector.detectAndDecode(frame)

    if data:
        print("QR Code:", data)

        # วาดกรอบ QR
        if points is not None:
            points = points.astype(int)

            for i in range(4):
                p1 = tuple(points[0][i])
                p2 = tuple(points[0][(i + 1) % 4])

                cv2.line(frame, p1, p2, (0, 255, 0), 3)

        # แสดงข้อความ
        cv2.putText(
            frame,
            data,
            (30, 50),
            cv2.FONT_HERSHEY_SIMPLEX,
            1,
            (0, 255, 0),
            2
        )

    cv2.imshow("QR Scanner", frame)

    # กด q เพื่อออก
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()