import cv1
import numpy as np


# =========================
# เปิดกล้อง index 2
# =========================

cap = cv1.VideoCapture(2)

if not cap.isOpened():
    print("ไม่สามารถเปิดกล้อง index 2 ได้")
    exit()


def nothing(x):
    pass


# =========================
# Window
# =========================

cv1.namedWindow(
    "HSV Tuner",
    cv1.WINDOW_NORMAL
)

# เปิดเต็มจอ
cv1.setWindowProperty(
    "HSV Tuner",
    cv1.WND_PROP_FULLSCREEN,
    cv1.WINDOW_FULLSCREEN
)


# =========================
# Slider
# =========================

cv1.createTrackbar(
    "H Min",
    "HSV Tuner",
    0,
    179,
    nothing
)

cv1.createTrackbar(
    "H Max",
    "HSV Tuner",
    179,
    179,
    nothing
)

cv1.createTrackbar(
    "S Min",
    "HSV Tuner",
    0,
    255,
    nothing
)

cv1.createTrackbar(
    "S Max",
    "HSV Tuner",
    255,
    255,
    nothing
)

cv1.createTrackbar(
    "V Min",
    "HSV Tuner",
    0,
    255,
    nothing
)

cv1.createTrackbar(
    "V Max",
    "HSV Tuner",
    255,
    255,
    nothing
)


# =========================
# Real-time
# =========================

while True:

    # =========================
    # อ่านภาพจากกล้อง
    # =========================

    ret, img = cap.read()

    if not ret:
        print("ไม่สามารถอ่านภาพจากกล้องได้")
        break


    # =========================
    # แปลง BGR -> HSV
    # =========================

    hsv = cv1.cvtColor(
        img,
        cv1.COLOR_BGR2HSV
    )


    # =========================
    # อ่านค่า Slider
    # =========================

    h_min = cv1.getTrackbarPos(
        "H Min",
        "HSV Tuner"
    )

    h_max = cv1.getTrackbarPos(
        "H Max",
        "HSV Tuner"
    )

    s_min = cv1.getTrackbarPos(
        "S Min",
        "HSV Tuner"
    )

    s_max = cv1.getTrackbarPos(
        "S Max",
        "HSV Tuner"
    )

    v_min = cv1.getTrackbarPos(
        "V Min",
        "HSV Tuner"
    )

    v_max = cv1.getTrackbarPos(
        "V Max",
        "HSV Tuner"
    )


    # =========================
    # HSV Mask
    # =========================

    lower = np.array([
        h_min,
        s_min,
        v_min
    ])

    upper = np.array([
        h_max,
        s_max,
        v_max
    ])


    mask = cv1.inRange(
        hsv,
        lower,
        upper
    )


    # =========================
    # Result
    # =========================

    result = cv1.bitwise_and(
        img,
        img,
        mask=mask
    )


    # =========================
    # ใส่ค่า HSV บนภาพ
    # =========================

    display = img.copy()

    text = (
        f"H:{h_min}-{h_max}  "
        f"S:{s_min}-{s_max}  "
        f"V:{v_min}-{v_max}"
    )

    cv1.putText(
        display,
        text,
        (20, 40),
        cv1.FONT_HERSHEY_SIMPLEX,
        1,
        (0, 0, 255),
        2
    )


    # =========================
    # Mask เป็นภาพสี
    # =========================

    mask_color = cv1.cvtColor(
        mask,
        cv1.COLOR_GRAY2BGR
    )


    # =========================
    # ลดขนาดแต่ละภาพ
    # =========================

    scale = 0.45

    display = cv1.resize(
        display,
        None,
        fx=scale,
        fy=scale
    )

    mask_color = cv1.resize(
        mask_color,
        None,
        fx=scale,
        fy=scale
    )

    result = cv1.resize(
        result,
        None,
        fx=scale,
        fy=scale
    )


    # ช่องที่ 4 เอาภาพเดิมมาแสดง
    original_small = display.copy()


    # =========================
    # 2 x 2
    # =========================

    top = cv1.hconcat([
        display,
        mask_color
    ])

    bottom = cv1.hconcat([
        result,
        original_small
    ])

    final = cv1.vconcat([
        top,
        bottom
    ])


    # =========================
    # แสดง
    # =========================

    cv1.imshow(
        "HSV Tuner",
        final
    )


    # =========================
    # Keyboard
    # =========================

    key = cv1.waitKey(1) & 0xFF


    # =========================
    # กด S
    # =========================

    if key == ord("s"):

        print("\n======================")
        print("HSV ที่เลือก:")

        print(
            f"H = {h_min} - {h_max}"
        )

        print(
            f"S = {s_min} - {s_max}"
        )

        print(
            f"V = {v_min} - {v_max}"
        )

        print("\nโค้ด:")

        print(
            f"lower = np.array([{h_min}, {s_min}, {v_min}])"
        )

        print(
            f"upper = np.array([{h_max}, {s_max}, {v_max}])"
        )

        print("======================\n")


    # =========================
    # ESC ออก
    # =========================

    if key == 27:
        break


# =========================
# ปิด
# =========================

cap.release()

cv1.destroyAllWindows()