#include <WiFi.h>
#include <InEngMotor.h>

// =============================
// Wi-Fi
// =============================
const char* ssid = "Carcarroboterer";
const char* password = "00000111";

// เปิด TCP Server ที่ port 5000
WiFiServer server(5000);

WiFiClient client;

// จำไว้ว่าเคยมี Python ต่ออยู่ไหม จะได้รู้ตอนที่มันหลุด
bool clientWasConnected = false;


// =====================================================
// เซอร์โว
// =====================================================

// มุมทั้งหมดยกมาจากหุ่น URG2025
// ซึ่งเป็นคนละกลไก ต้องหามุมจริงด้วย ServoCalibrate() ก่อนใช้งาน

#define GripPin           32    // เซอร์โวตัวที่ 1 หนีบ
#define ArmPin            33    // เซอร์โวตัวที่ 2 ยกขึ้นลง

#define ServoMinUs        500   // ความกว้างพัลส์ที่มุม 0 องศา
#define ServoMaxUs        2400  // ความกว้างพัลส์ที่มุม 180 องศา

#define GripClose         55    // หนีบ
#define GripHalf          75    // อ้าเล็กน้อยให้ของหล่น
#define GripOpen          120   // อ้าสุด

#define ArmUp             60    // ยกแขนขึ้นสุด
#define ArmDown           150   // ลดแขนต่ำสุด
#define ArmDown2          120   // ลดแขนระดับ 2
#define ArmDown3          110   // ลดแขนระดับ 3
#define ArmDown4          105   // ลดแขนระดับ 4
#define ArmDown5          95    // ลดแขนระดับ 5

#define GripWait          300   // เวลารอให้คีมหนีบเสร็จ (ms)
#define PutWait           200   // เวลารอให้คีมอ้าเสร็จ (ms)
#define ArmWait           300   // เวลารอให้แขนขยับเสร็จ (ms)


// =====================================================
// สร้าง Servo
// =====================================================

Servo gripServo;
Servo armServo;


// =====================================================
// ฟังก์ชันควบคุม Servo
// =====================================================

// -----------------------------
// เปิดคีม
// -----------------------------
void gripOpen() {

  gripServo.write(GripOpen);

  delay(PutWait);
}


// -----------------------------
// อ้าคีมเล็กน้อย
// -----------------------------
void gripHalf() {

  gripServo.write(GripHalf);

  delay(PutWait);
}


// -----------------------------
// หนีบ
// -----------------------------
void gripClose() {

  gripServo.write(GripClose);

  delay(GripWait);
}


// -----------------------------
// ยกแขนขึ้น
// -----------------------------
void armUp() {

  armServo.write(ArmUp);

  delay(ArmWait);
}


// -----------------------------
// ลดแขนลงต่ำสุด
// -----------------------------
void armDown() {

  armServo.write(ArmDown);

  delay(ArmWait);
}


// -----------------------------
// ลดแขนระดับ 2
// -----------------------------
void armDown2() {

  armServo.write(ArmDown2);

  delay(ArmWait);
}


// -----------------------------
// ลดแขนระดับ 3
// -----------------------------
void armDown3() {

  armServo.write(ArmDown3);

  delay(ArmWait);
}


// -----------------------------
// ลดแขนระดับ 4
// -----------------------------
void armDown4() {

  armServo.write(ArmDown4);

  delay(ArmWait);
}


// -----------------------------
// ลดแขนระดับ 5
// -----------------------------
void armDown5() {

  armServo.write(ArmDown5);

  delay(ArmWait);
}


// =====================================================
// หลักการ GRAB
// =====================================================
//
// 1. เปิดคีม
// 2. ลดแขนลง
// 3. หนีบของ
// 4. ยกแขนขึ้น
//
// ไม่ได้เปลี่ยนการทำงานของมอเตอร์รถ
// =====================================================

void grabObject() {

  Serial.println("========== GRAB START ==========");

  // 1. เปิดคีมก่อน
  gripOpen();

  // 2. ลดแขนลงเพื่อเตรียมหยิบของ
  armDown();

  // 3. หนีบของ
  gripClose();

  // 4. ยกของขึ้น
  armUp();

  Serial.println("========== GRAB DONE ==========");
}


void setup() {

  Serial.begin(115200);

  // เริ่ม Motor Library
  inengmotor.begin();

  // ตอนเริ่มให้รถหยุด
  inengmotor.stop();

  // =============================
  // เชื่อม Wi-Fi
  // =============================
  WiFi.begin(ssid, password);

  Serial.print("กำลังเชื่อม Wi-Fi");

  int tries = 0;
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");

    // ทุก ๆ 10 วินาทีที่ยังต่อไม่ได้ ให้บอกสาเหตุที่พบบ่อย
    tries++;
    if (tries % 20 == 0) {
      Serial.println();
      Serial.println("ยังต่อ Wi-Fi ไม่ได้ - เช็คว่า hotspot เปิดอยู่, ชื่อ/รหัสถูก และเป็นคลื่น 2.4GHz (ESP32 ต่อ 5GHz ไม่ได้)");
    }
  }

  Serial.println();
  Serial.println("Wi-Fi Connected!");

  // แสดง IP ของ ESP32
  Serial.print("ESP32 IP: ");
  Serial.println(WiFi.localIP());

  // เริ่ม Server
  server.begin();

  Serial.println("TCP Server started (port 5000) - รอ Python เชื่อมต่อ...");
}

void loop() {

  // ถ้ายังไม่มี Client ให้รอ
  if (!client || !client.connected()) {

    // Python หลุด/ปิดโปรแกรม ให้หยุดรถไว้ก่อน ไม่งั้นรถจะทำคำสั่งสุดท้ายค้างไปเรื่อย ๆ
    if (clientWasConnected) {
      inengmotor.stop();
      Serial.println("Python หลุดการเชื่อมต่อ -> STOP");
      clientWasConnected = false;
    }

    // ESP32 core 3.x เปลี่ยนชื่อ server.available() เป็น server.accept()
    client = server.accept();

    if (client) {
      Serial.print("Python เชื่อมต่อแล้ว จาก ");
      Serial.println(client.remoteIP());
      clientWasConnected = true;
    }

    return;
  }

  // มีข้อมูลจาก Python
  if (client.available()) {

    String command = client.readStringUntil('\n');

    command.trim();

    Serial.print("Received: ");
    Serial.println(command);

    // =============================
    // เดินหน้า
    // =============================
    if (command == "FORWARD") {

      inengmotor.forward(200, 200);
    }

    // =============================
    // ถอยหลัง
    // =============================
    else if (command == "BACKWARD") {

      inengmotor.backward(200, 200);
    }

    // =============================
    // เลี้ยวซ้าย
    // =============================
    else if (command == "TURN_LEFT") {

      inengmotor.turnLeft(80, 180);
    }

    // =============================
    // เลี้ยวขวา
    // =============================
    else if (command == "TURN_RIGHT") {

      inengmotor.turnRight(180, 80);
    }

    // =============================
    // GRAB
    // =============================
    else if (command == "GRAB") {

      inengmotor.stop();
       // เริ่มกระบวนการหยิบ
      grabObject();
    }

    // =============================
    // STOP
    // =============================
    else if (command == "STOP") {

      inengmotor.stop();
    }

    else {

      Serial.println("ไม่รู้จักคำสั่ง");
    }
  }
}