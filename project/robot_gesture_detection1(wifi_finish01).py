import sys
import time
from pathlib import Path

import cv2
import numpy as np
import mediapipe as mp

# เชื่อมต่อกับ ESP32 ผ่าน Wi-Fi (TCP socket) แทนสาย USB/Serial
import socket

# =========================================================
# ค่าคงที่ / การตั้งค่า
# =========================================================

MODEL_PATH = Path(__file__).parent / "hand_landmarker.task"

CAMERA_INDEX = 0
FRAME_WIDTH = 1280
FRAME_HEIGHT = 720

NUM_HANDS = 2
MIN_DETECTION_CONFIDENCE = 0.5
MIN_PRESENCE_CONFIDENCE = 0.5
MIN_TRACKING_CONFIDENCE = 0.5

WINDOW_NAME = "Robot Gesture Detection"

# ค่าตั้งต้นการเชื่อมต่อ ESP32 ผ่าน Wi-Fi — แก้ ESP32_IP ให้ตรงกับ IP จริงของบอร์ด
# (ดูได้จาก Serial Monitor ตอนบอร์ดต่อ Wi-Fi สำเร็จ, มักจะ print IP ออกมา)
ESP32_IP = "10.128.189.123"
ESP32_PORT = 5000
_wifi_conn = None   # ตัวแปรเก็บ socket connection ไว้ใช้ทั้งโปรแกรม (ตั้งค่าตอนเรียก connect_wifi)

# กันส่งคำสั่งรัว ๆ ทุกเฟรม — ต้องเจอท่าเดิมติดกันกี่เฟรมก่อนค่อยส่งคำสั่งใหม่จริง
GESTURE_DEBOUNCE_FRAMES = 4

# สี (BGR)
COLOR_POINT = (0, 255, 0)
COLOR_LINE = (255, 200, 0)
COLOR_TEXT = (0, 255, 0)
COLOR_PANEL = (0, 0, 0)
COLOR_COMMAND = (0, 220, 255)  # สีคำสั่งที่ลอยเหนือมือ (เหลือง-ส้ม เด่นสะดุดตา)

# คู่ของ landmark ที่ลากเส้นเชื่อมกันเป็นโครงมือ (21 จุดของ MediaPipe)
HAND_CONNECTIONS = (
    (0, 1), (1, 2), (2, 3), (3, 4),            # นิ้วโป้ง
    (0, 5), (5, 6), (6, 7), (7, 8),            # นิ้วชี้
    (5, 9), (9, 10), (10, 11), (11, 12),       # นิ้วกลาง
    (9, 13), (13, 14), (14, 15), (15, 16),     # นิ้วนาง
    (13, 17), (17, 18), (18, 19), (19, 20),    # นิ้วก้อย
    (0, 17),                                    # ขอบฝ่ามือ
)

# ดัชนี landmark ของปลายนิ้วและข้อกลางแต่ละนิ้ว (ใช้เช็คว่านิ้วกางออกหรือไม่)
# ลำดับ: (ปลายนิ้ว, ข้อกลาง) — นิ้วโป้งไม่รวมเพราะทิศทางงอต่างจากนิ้วอื่น ต้องเช็คแยก
FINGER_TIP_PIP = {
    "index": (8, 6),
    "middle": (12, 10),
    "ring": (16, 14),
    "pinky": (20, 18),
}
THUMB_TIP_IP = (4, 3)  # ปลายนิ้วโป้ง, ข้อกลางนิ้วโป้ง

# landmark สำหรับวัดระยะ "หยิบ/คีบ" (ปลายนิ้วโป้งกับปลายนิ้วชี้ชนกัน)
THUMB_TIP = 4
INDEX_TIP = 8
WRIST = 0
MIDDLE_MCP = 9  # ใช้เป็นสเกลอ้างอิงขนาดมือ (ยิ่งมือใกล้กล้อง ระยะยิ่งเป็นพิกเซลเยอะ)
PINCH_RATIO_THRESHOLD = 0.4  # ถ้าระยะโป้ง-ชี้ / ขนาดมือ ต่ำกว่านี้ = ถือว่าคีบ ปรับได้ตามจริง

# เพราะเรา flip ภาพก่อนส่งเข้าโมเดล ป้าย Left/Right ที่โมเดลตอบกลับมา
# จะสลับข้างกับที่ตาเราเห็นบนจอ (โมเดลตัดสินจากมุมกล้องจริง ไม่ใช่มุมกระจก)
# แก้ด้วยการสลับป้ายตอนแสดงผลแทนที่จะไปยุ่งกับ pipeline การตรวจจับ
HANDEDNESS_DISPLAY_FIX = {"Left": "Right", "Right": "Left"}

# MediaPipe Tasks API
BaseOptions = mp.tasks.BaseOptions
VisionRunningMode = mp.tasks.vision.RunningMode
HandLandmarker = mp.tasks.vision.HandLandmarker
HandLandmarkerOptions = mp.tasks.vision.HandLandmarkerOptions


# =========================================================
# ฟังก์ชันย่อย
# =========================================================

def create_landmarker():
    """สร้างตัวตรวจจับมือ พร้อมเช็คว่าไฟล์โมเดลมีจริง"""
    if not MODEL_PATH.is_file():
        sys.exit(
            f"ERROR: ไม่พบไฟล์โมเดลที่ {MODEL_PATH}\n"
            "ดาวน์โหลด hand_landmarker.task มาวางไว้โฟลเดอร์เดียวกับสคริปต์นี้"
        )

    options = HandLandmarkerOptions(
        base_options=BaseOptions(model_asset_path=str(MODEL_PATH)),
        running_mode=VisionRunningMode.VIDEO,
        num_hands=NUM_HANDS,
        min_hand_detection_confidence=MIN_DETECTION_CONFIDENCE,
        min_hand_presence_confidence=MIN_PRESENCE_CONFIDENCE,
        min_tracking_confidence=MIN_TRACKING_CONFIDENCE,
    )
    return HandLandmarker.create_from_options(options)


def open_camera() -> cv2.VideoCapture:
    """เปิดกล้องและตั้งค่าความละเอียด"""
    cap = cv2.VideoCapture(CAMERA_INDEX)
    if not cap.isOpened():
        sys.exit("ERROR: ไม่สามารถเปิดกล้องได้ (ลองเปลี่ยน CAMERA_INDEX)")

    cap.set(cv2.CAP_PROP_FRAME_WIDTH, FRAME_WIDTH)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, FRAME_HEIGHT)
    return cap


def to_pixels(landmarks, width: int, height: int) -> list[tuple[int, int]]:
    """แปลงพิกัด normalized (0-1) ของ MediaPipe เป็นพิกเซลบนภาพ"""
    return [
        (int(lm.x * width), int(lm.y * height))
        for lm in landmarks
    ]


def draw_hand(frame: np.ndarray, points: list[tuple[int, int]], label: str, command_text: str = "") -> None:
    """วาดเส้นโครงมือ จุด landmark, ป้ายชื่อมือ (ซ้าย/ขวา) และคำสั่งที่กำลังสั่งอยู่"""
    for start, end in HAND_CONNECTIONS:
        cv2.line(frame, points[start], points[end], COLOR_LINE, 2)

    for point in points:
        cv2.circle(frame, point, 5, COLOR_POINT, -1)

    wrist_x, wrist_y = points[0]

    if label:
        cv2.putText(
            frame, label, (wrist_x - 20, wrist_y + 30),
            cv2.FONT_HERSHEY_SIMPLEX, 0.7, COLOR_TEXT, 2,
        )

    # แสดงคำสั่งที่ท่านี้กำลังสั่งรถอยู่ ลอยอยู่เหนือมือ พร้อมกล่องพื้นหลัง
    # ให้อ่านง่ายไม่จมไปกับพื้นหลังของภาพ
    if command_text:
        (text_w, text_h), _ = cv2.getTextSize(
            command_text, cv2.FONT_HERSHEY_SIMPLEX, 0.9, 2
        )
        box_x1 = wrist_x - text_w // 2 - 12
        box_y1 = wrist_y - 90 - text_h
        box_x2 = wrist_x + text_w // 2 + 12
        box_y2 = wrist_y - 70

        cv2.rectangle(frame, (box_x1, box_y1), (box_x2, box_y2), COLOR_PANEL, -1)
        cv2.putText(
            frame, command_text, (box_x1 + 12, box_y2 - 10),
            cv2.FONT_HERSHEY_SIMPLEX, 0.9, COLOR_COMMAND, 2,
        )


def draw_hud(frame: np.ndarray, hand_count: int, fps: float, gesture: str = "") -> None:
    """วาดแถบข้อมูลมุมซ้ายบน"""
    cv2.rectangle(frame, (10, 10), (400, 100), COLOR_PANEL, -1)
    cv2.putText(
        frame, f"HANDS: {hand_count}   FPS: {fps:.1f}", (25, 50),
        cv2.FONT_HERSHEY_SIMPLEX, 0.9, COLOR_TEXT, 2,
    )
    if gesture:
        cv2.putText(
            frame, f"GESTURE: {gesture}", (25, 85),
            cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 200, 255), 2,
        )


# =========================================================
# ส่วนตรวจจับท่าทาง (Gesture Recognition)
# =========================================================
# นี่คือจุดหลักที่ต้องแก้/เพิ่มถ้าอยากทำ "ท่าทาง -> คำสั่งควบคุมรถ"
# แนวคิด: ท่าทาง 1 ท่า = การกางนิ้วรูปแบบหนึ่ง เราเช็คว่านิ้วไหน "กาง" อยู่
# แล้วเทียบรูปแบบนั้นกับท่าที่กำหนดไว้ล่วงหน้า

def is_finger_extended(points: list[tuple[int, int]], tip_idx: int, pip_idx: int) -> bool:
    """
    เช็คว่านิ้วนั้นกางออกหรือไม่ โดยเทียบตำแหน่ง y ของปลายนิ้วกับข้อกลาง
    (ปลายนิ้วอยู่สูงกว่า/y น้อยกว่า ข้อกลาง = นิ้วกางออก)
    หมายเหตุ: ใช้ได้กับกรณีมือตั้งตรงในแนวดิ่งเป็นหลัก ถ้ามือเอียงมาก
    ควรเปลี่ยนไปเทียบระยะห่างจากจุดศูนย์กลางฝ่ามือ (landmark 0 หรือ 9) แทน
    """
    tip_y = points[tip_idx][1]
    pip_y = points[pip_idx][1]
    return tip_y < pip_y


def count_extended_fingers(points: list[tuple[int, int]]) -> int:
    """นับจำนวนนิ้ว (ไม่รวมโป้ง) ที่กางออกอยู่ — ใช้เป็นฐานสำหรับแยกท่าทาง"""
    count = 0
    for tip_idx, pip_idx in FINGER_TIP_PIP.values():
        if is_finger_extended(points, tip_idx, pip_idx):
            count += 1
    return count


def pinch_ratio(points: list[tuple[int, int]]) -> float:
    """
    คำนวณ 'ระยะห่างโป้ง-ชี้' หารด้วย 'ขนาดมือ' (ระยะข้อมือ-โคนนิ้วกลาง)
    ใช้อัตราส่วนแทนระยะดิบ เพราะระยะพิกเซลจะเปลี่ยนไปตามระยะห่างมือ-กล้อง
    ค่ายิ่งน้อย = ปลายนิ้วโป้งกับนิ้วชี้ยิ่งชนกัน (ท่าคีบ/หยิบ)
    """
    thumb_x, thumb_y = points[THUMB_TIP]
    index_x, index_y = points[INDEX_TIP]
    pinch_dist = ((thumb_x - index_x) ** 2 + (thumb_y - index_y) ** 2) ** 0.5

    wrist_x, wrist_y = points[WRIST]
    mcp_x, mcp_y = points[MIDDLE_MCP]
    hand_scale = ((wrist_x - mcp_x) ** 2 + (wrist_y - mcp_y) ** 2) ** 0.5

    if hand_scale == 0:
        return 1.0  # กันหารด้วยศูนย์ ถือว่าไม่คีบ
    return pinch_dist / hand_scale


def classify_gesture(points: list[tuple[int, int]]) -> str:
    """
    ========== TODO: เพิ่มท่าทางใหม่ตรงนี้ ==========
    ลำดับการเช็คมีผล — ท่า "คีบ" เช็คก่อนท่าอื่นเสมอ เพราะขณะคีบ
    นิ้วชี้อาจกางอยู่ (ตรงกับเงื่อนไข POINT ด้วย) ถ้าอยากเพิ่มท่าใหม่
    ที่ชนกับท่าเดิม ให้จัดลำดับความสำคัญแบบนี้เหมือนกัน

    ถ้าต้องการท่าที่ซับซ้อนขึ้น ให้เช็คนิ้วแต่ละนิ้วแยกกันเป็นเงื่อนไข เช่น:

        index_up = is_finger_extended(points, 8, 6)
        middle_up = is_finger_extended(points, 12, 10)
        if index_up and not middle_up:
            return "POINT"
        if index_up and middle_up:
            return "PEACE"
    """
    # 1) เช็คท่าคีบก่อนเป็นอันดับแรก (สำคัญที่สุดสำหรับควบคุมก้ามคีบ)
    if pinch_ratio(points) < PINCH_RATIO_THRESHOLD:
        return "GRAB"

    extended = count_extended_fingers(points)

    if extended == 0:
        return "FIST"          # กำมือ
    if extended == 4:
        return "OPEN_PALM"     # แบมือ
    if extended == 1 and is_finger_extended(points, 8, 6):
        return "POINT"         # ชี้นิ้วเดียว (นิ้วชี้)
    if extended == 2 and is_finger_extended(points, 8, 6) and is_finger_extended(points, 12, 10):
        return "PEACE"         # ท่าวี (นิ้วชี้+นิ้วกลาง)

    return "UNKNOWN"


def gesture_to_command(gesture: str) -> str:
    """
    ========== TODO: ผูกท่าทางเข้ากับคำสั่งควบคุมรถตรงนี้ ==========
    แก้ mapping ในดิกชันนารีนี้ให้ตรงกับกติกาของรถ/หุ่นยนต์ที่ใช้
    ค่าที่คืนกลับมาจากฟังก์ชันนี้คือ "คำสั่ง" ที่จะส่งออกไปควบคุมจริง
    ต้องให้ตรงกับคำสั่งที่ฝั่ง ESP32 (ใน Arduino IDE) รู้จัก/parse ได้
    """
    gesture_map = {
        "OPEN_PALM": "FORWARD",    # แบมือ = เดินหน้า
        "FIST": "BACKWARD",        # กำมือ = ถอยหลัง
        "POINT": "TURN_RIGHT",     # ชี้นิ้วเดียว = เลี้ยวขวา
        "PEACE": "TURN_LEFT",      # ท่าวี = เลี้ยวซ้าย
        "GRAB": "GRAB",            # โป้ง+ชี้ชนกัน = สั่งคีบ (หุบก้าม)
    }
    return gesture_map.get(gesture, "STOP")   # ท่าที่ไม่รู้จัก (UNKNOWN) = หยุดไว้ก่อน เพื่อความปลอดภัย


def send_command_to_car(command: str) -> None:
    global _wifi_conn

    if _wifi_conn is None:
        if not connect_wifi():
            print(f"[WARN] ยังเชื่อมต่อ ESP32 ไม่ได้: {command}")
            return

    try:
        _wifi_conn.sendall((command + "\n").encode())
        print(f"[SEND] {command}")

    except OSError as exc:
        print(f"[WARN] ส่งคำสั่งไม่สำเร็จ: {exc}")

        try:
            _wifi_conn.close()
        except:
            pass

        _wifi_conn = None


def connect_wifi() -> bool:
    """เปิดการเชื่อมต่อ TCP ไปยัง ESP32 ตาม ESP32_IP / ESP32_PORT ที่ตั้งไว้ด้านบน"""
    global _wifi_conn

    try:
        _wifi_conn = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        _wifi_conn.settimeout(5)
        _wifi_conn.connect((ESP32_IP, ESP32_PORT))

        print(f"เชื่อมต่อ ESP32 ผ่าน Wi-Fi สำเร็จ: {ESP32_IP}:{ESP32_PORT}")
        return True

    except OSError as exc:
        _wifi_conn = None
        print(f"[WARN] เชื่อมต่อ ESP32 ที่ {ESP32_IP}:{ESP32_PORT} ไม่ได้: {exc}")
        print("       - คอมต้องต่อ Wi-Fi วงเดียวกับ ESP32 (hotspot เดียวกัน)")
        print("       - ESP32_IP ต้องตรงกับบรรทัด 'ESP32 IP:' ใน Serial Monitor (กดปุ่ม EN บนบอร์ดเพื่อดูใหม่)")
        return False


# =========================================================
# โปรแกรมหลัก
# =========================================================

def main() -> None:
    cap = open_camera()

    # เปิดการเชื่อมต่อ Wi-Fi ไปยัง ESP32 ครั้งเดียวตอนเริ่มโปรแกรม
    # ถ้าเชื่อมต่อไม่สำเร็จ (เช่น ยังไม่เปิดบอร์ด/ผิด IP) โปรแกรมยังรันได้ปกติ
    # แค่คำสั่งจะไปโผล่เป็น print ใน console แทนการส่งออกจริง
    connect_wifi()

    print("Camera started — กด Q เพื่อออก")

    last_timestamp_ms = -1
    prev_time = time.perf_counter()
    fps = 0.0

    # ตัวแปรสำหรับ debounce: นับว่าท่าทางปัจจุบันซ้ำติดกันมากี่เฟรม
    # และจำคำสั่งล่าสุดที่ส่งออกไปแล้ว จะได้ไม่ส่งซ้ำถ้าคำสั่งไม่เปลี่ยน
    pending_gesture = ""
    pending_count = 0
    last_sent_command = ""

    try:
        with create_landmarker() as landmarker:
            while True:
                ok, frame = cap.read()
                if not ok:
                    print("ERROR: อ่านภาพจากกล้องไม่ได้")
                    break

                # กลับภาพซ้าย-ขวาให้เหมือนมองกระจก
                frame = cv2.flip(frame, 1)
                height, width = frame.shape[:2]

                # MediaPipe ต้องการภาพ RGB และเป็น array แบบต่อเนื่อง
                rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                mp_image = mp.Image(
                    image_format=mp.ImageFormat.SRGB,
                    data=np.ascontiguousarray(rgb),
                )

                # VIDEO mode ต้องใช้ timestamp หน่วยมิลลิวินาที และต้องเพิ่มขึ้นเสมอ
                timestamp_ms = max(
                    int(time.perf_counter() * 1000),
                    last_timestamp_ms + 1,
                )
                last_timestamp_ms = timestamp_ms

                result = landmarker.detect_for_video(mp_image, timestamp_ms)

                # วาดผลลัพธ์ + ตรวจจับท่าทางของทุกมือที่เจอ
                # (แสดงคำสั่งลอยเหนือมือทุกมือ แต่ใช้แค่มือแรกในการคุมรถจริง)
                current_gesture = ""
                for index, landmarks in enumerate(result.hand_landmarks):
                    label = ""
                    if index < len(result.handedness):
                        raw_label = result.handedness[index][0].category_name
                        # สลับป้าย เพราะภาพถูก flip ก่อนส่งเข้าโมเดล (ดูคอมเมนต์ที่ HANDEDNESS_DISPLAY_FIX)
                        label = HANDEDNESS_DISPLAY_FIX.get(raw_label, raw_label)

                    points = to_pixels(landmarks, width, height)
                    hand_gesture = classify_gesture(points)
                    hand_command = gesture_to_command(hand_gesture)
                    draw_hand(frame, points, label, hand_command)

                    # ตอนนี้ใช้แค่มือแรก (index == 0) ในการควบคุมจริง
                    # ถ้าจะใช้สองมือพร้อมกัน (เช่น มือซ้ายคุมความเร็ว มือขวาคุมทิศ)
                    # ให้ขยาย logic ตรงนี้แยกตาม label ว่าเป็น Left หรือ Right
                    if index == 0:
                        current_gesture = hand_gesture

                if current_gesture:
                    # --- Debounce: ต้องเจอท่าเดิมติดกันครบจำนวนเฟรมก่อนค่อยส่งจริง ---
                    # กันมือสั่นเล็กน้อยทำให้ท่าเปลี่ยนสลับไปมา ส่งคำสั่งรัวจนรถกระตุก
                    if current_gesture == pending_gesture:
                        pending_count += 1
                    else:
                        pending_gesture = current_gesture
                        pending_count = 1

                    if pending_count >= GESTURE_DEBOUNCE_FRAMES:
                        command = gesture_to_command(current_gesture)
                        if command != last_sent_command:
                            send_command_to_car(command)
                            last_sent_command = command

                # คำนวณ FPS แบบเฉลี่ยลื่น ๆ
                now = time.perf_counter()
                delta = now - prev_time
                prev_time = now
                if delta > 0:
                    fps = 0.9 * fps + 0.1 * (1.0 / delta)

                draw_hud(frame, len(result.hand_landmarks), fps, current_gesture)
                cv2.imshow(WINDOW_NAME, frame)

                if cv2.waitKey(1) & 0xFF in (ord("q"), ord("Q"), 27):  # Q หรือ Esc
                    break

                # ถ้าผู้ใช้กดกากบาทปิดหน้าต่าง ให้ตรวจจับแล้วออกจากลูปด้วย
                if cv2.getWindowProperty(WINDOW_NAME, cv2.WND_PROP_VISIBLE) < 1:
                    break

    except KeyboardInterrupt:
        print("\nหยุดโดยผู้ใช้")
    finally:
        cap.release()
        cv2.destroyAllWindows()
        if _wifi_conn is not None:
            _wifi_conn.close()
        print("ปิดโปรแกรมเรียบร้อย")


if __name__ == "__main__":
    main()