import json
import math
import time
from pathlib import Path

# ============================================================
# navigation.py
#
# อ่าน:
#   1. ตำแหน่งรถจาก test_readcode.py
#   2. ตำแหน่ง GEM + Drop Zone จาก find_colorcodeinground.py
#
# แล้วสร้างเส้นทางไป:
#   Robot -> GEM -> Drop Zone
#
# ตอนนี้เป็น "ระบบวางเส้นทางระดับพิกัด"
# ยังไม่ได้สั่ง ESP32 โดยตรง จนกว่าจะทดสอบเส้นทางให้ถูกก่อน
# ============================================================

DATA_FILE = Path("shared_data.json")

# ระยะที่ถือว่า "ถึงเป้าหมาย"
ARRIVE_DISTANCE = 35

# ============================================================
# อ่านข้อมูลกลาง
# ============================================================

def load_data():
    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return None


# ============================================================
# คำนวณระยะทาง
# ============================================================

def distance(a, b):
    return math.hypot(
        b[0] - a[0],
        b[1] - a[1]
    )


# ============================================================
# มุมจากรถไปหาเป้าหมาย
# ============================================================

def target_angle(robot, target):
    dx = target[0] - robot["x"]
    dy = target[1] - robot["y"]

    return math.degrees(math.atan2(dy, dx))


# ============================================================
# หาความต่างของมุม
# ============================================================

def angle_difference(target_angle_value, robot_angle):
    diff = target_angle_value - robot_angle

    while diff > 180:
        diff -= 360

    while diff < -180:
        diff += 360

    return diff


# ============================================================
# แปลงตำแหน่งเป้าหมายเป็นคำสั่งเบื้องต้น
#
# เป้าหมาย:
#   ด้านหน้า      -> FORWARD
#   ด้านซ้าย      -> LEFT
#   ด้านขวา       -> RIGHT
#   ใกล้มาก       -> STOP
#
# หมายเหตุ:
# ยังไม่ได้คุมความเร็ว/เวลาเลี้ยว
# ============================================================

def navigation_command(robot, target):

    d = distance(
        (robot["x"], robot["y"]),
        target
    )

    if d <= ARRIVE_DISTANCE:
        return "STOP"

    t_angle = target_angle(robot, target)

    diff = angle_difference(
        t_angle,
        robot["angle"]
    )

    # dead zone เพื่อไม่ให้ส่ายซ้ายขวา
    if abs(diff) < 20:
        return "FORWARD"

    if diff > 0:
        return "RIGHT"

    return "LEFT"


# ============================================================
# เลือก GEM ที่ใกล้รถที่สุด
# ============================================================

def nearest_gem(robot, gems):

    if not gems:
        return None

    robot_pos = (robot["x"], robot["y"])

    return min(
        gems,
        key=lambda g: distance(
            robot_pos,
            (g["x"], g["y"])
        )
    )


# ============================================================
# MAIN
# ============================================================

print("================================")
print(" Navigation System")
print("================================")

carrying_color = None
current_target = None

while True:

    data = load_data()

    if data is None:
        print("ยังไม่มี shared_data.json")
        time.sleep(0.5)
        continue

    robot = data.get("robot", {})
    gems = data.get("gems", [])
    drop_zones = data.get("drop_zones", {})

    if not robot or "x" not in robot:
        print("รอตำแหน่งรถจาก QR...")
        time.sleep(0.5)
        continue

    # --------------------------------------------------------
    # ถ้ายังไม่ได้ถือ GEM
    # --------------------------------------------------------

    if carrying_color is None:

        if current_target is None:

            gem = nearest_gem(robot, gems)

            if gem is None:
                print("ไม่พบ GEM")
                time.sleep(0.5)
                continue

            current_target = {
                "type": "GEM",
                "id": gem["id"],
                "color": gem["color"],
                "x": gem["x"],
                "y": gem["y"]
            }

            print(
                f"เลือก GEM ID={gem['id']} "
                f"COLOR={gem['color']} "
                f"POS=({gem['x']},{gem['y']})"
            )

        target = (
            current_target["x"],
            current_target["y"]
        )

        command = navigation_command(
            robot,
            target
        )

        print(
            f"Robot=({robot['x']},{robot['y']}) "
            f"Angle={robot['angle']:.1f} "
            f"Target=({target[0]},{target[1]}) "
            f"CMD={command}"
        )

        # ----------------------------------------------------
        # ถึง GEM แล้ว
        # ----------------------------------------------------
        if command == "STOP":
            print("ถึง GEM แล้ว -> รอคีบ")
            print(
                f"ควรตรวจสีจากกล้องหน้ารถ: "
                f"คาดว่า {current_target['color']}"
            )

            # สำหรับการทดสอบ:
            # ให้ใช้สีจากแผนที่เป็น carrying_color ก่อน
            carrying_color = current_target["color"]

            print(
                f"ถือ GEM สี {carrying_color}"
            )

            current_target = None

    # --------------------------------------------------------
    # ถ้าถือ GEM อยู่ -> ไป Drop Zone
    # --------------------------------------------------------

    else:

        if carrying_color not in drop_zones:
            print(
                f"ไม่พบ Drop Zone สำหรับ {carrying_color}"
            )
            time.sleep(1)
            continue

        target = tuple(
            drop_zones[carrying_color]
        )

        command = navigation_command(
            robot,
            target
        )

        print(
            f"ถือ={carrying_color} "
            f"Robot=({robot['x']},{robot['y']}) "
            f"Target={target} "
            f"CMD={command}"
        )

        # ----------------------------------------------------
        # ถึง Drop Zone
        # ----------------------------------------------------

        if command == "STOP":

            print(
                f"ถึง DROP ZONE {carrying_color}"
            )

            print("สั่ง Servo ปล่อย GEM")

            # ทดสอบเสร็จแล้ว
            carrying_color = None

    time.sleep(0.1)
