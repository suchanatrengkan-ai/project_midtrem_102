#include <WiFi.h>
#include <ESP32Servo.h>
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
// ยกโครงมาจาก Servo.ino ของหุ่น URG2025
// มุมทั้งหมดยกมาจากหุ่นตัวเดิม ซึ่งเป็นคนละกลไก ต้องหามุมจริงด้วย ServoCalibrate() ก่อนใช้งาน

#define GripPin 32  // เซอร์โวตัวที่ 1 หนีบ
#define ArmPin 33   // เซอร์โวตัวที่ 2 ยกขึ้นลง

#define ServoMinUs 500   // ความกว้างพัลส์ที่มุม 0 องศา
#define ServoMaxUs 2400  // ความกว้างพัลส์ที่มุม 180 องศา

#define GripClose 55  // หนีบ
#define GripHalf 75   // อ้าเล็กน้อยให้ของหล่น
#define GripOpen 120  // อ้าสุด

#define ArmUp 60      // ยกแขนขึ้นสุด
#define ArmDown 150   // ลดแขนต่ำสุด
#define ArmDown2 120  // ลดแขนระดับ 2
#define ArmDown3 110  // ลดแขนระดับ 3
#define ArmDown4 105  // ลดแขนระดับ 4
#define ArmDown5 95   // ลดแขนระดับ 5

#define GripWait 300  // เวลารอให้คีมหนีบเสร็จ (ms)
#define PutWait 200   // เวลารอให้คีมอ้าเสร็จ (ms)
#define ArmWait 300   // เวลารอให้แขนขยับเสร็จ (ms)

Servo GripServo;  // ตัวที่ 1 หนีบ
Servo ArmServo;   // ตัวที่ 2 ยกขึ้นลง


// =====================================================
// ฟังก์ชันควบคุม Servo
// =====================================================

// ระดับ 2-5 ต้องอยู่ระหว่าง ArmUp กับ ArmDown เสมอ พอจูน ArmDown ใหม่แล้วลืมแก้ระดับอื่น
// ระดับที่เกินจะถูกตัดให้เท่าขอบ ไม่ปล่อยให้เซอร์โวดันกลไกค้างจนร้อน
void ArmWrite(int Angle) {
  int Lo = (ArmUp < ArmDown) ? ArmUp : ArmDown;
  int Hi = (ArmUp < ArmDown) ? ArmDown : ArmUp;
  ArmServo.write(constrain(Angle, Lo, Hi));
}

void InitServo() {
  // InEngMotor ยึดช่อง PWM 0-3 ไปแล้ว ถ้าไม่จองแยกไว้ เซอร์โวจะไปแย่งช่อง 0 ของล้อซ้าย
  ESP32PWM::allocateTimer(2);
  ESP32PWM::allocateTimer(3);

  GripServo.setPeriodHertz(50);
  ArmServo.setPeriodHertz(50);
  int GripCh = GripServo.attach(GripPin, ServoMinUs, ServoMaxUs);
  int ArmCh = ArmServo.attach(ArmPin, ServoMinUs, ServoMaxUs);

  Serial.print("Servo PWM channel : grip=");
  Serial.print(GripCh);
  Serial.print(" arm=");
  Serial.println(ArmCh);  // ถ้าขึ้นเลข 0-3 แปลว่าชนกับมอเตอร์

  ServoGripDown();
  delay(2000);

  ServoGripUp();
  ServoPut();
}

// ---------- สั่งมุมอย่างเดียว ไม่รอ ไม่หยุดล้อ ----------
void ServoGrip() {
  GripServo.write(GripClose);
}
void ServoPut0() {
  GripServo.write(GripHalf);
}  // อ้าเล็กน้อยให้ของหล่น
void ServoPut() {
  GripServo.write(GripOpen);
}
void ServoGripUp() {
  ArmWrite(ArmUp);
}
void ServoGripDown() {
  ArmWrite(ArmDown);
}  // ลดแขนต่ำสุด
void ServoGripDown2() {
  ArmWrite(ArmDown2);
}
void ServoGripDown3() {
  ArmWrite(ArmDown3);
}
void ServoGripDown4() {
  ArmWrite(ArmDown4);
}
void ServoGripDown5() {
  ArmWrite(ArmDown5);
}

// ---------- หยุดล้อ สั่งมุม แล้วรอให้กลไกขยับเสร็จ ----------
void Grip() {
  inengmotor.stop();
  ServoGrip();
  delay(GripWait);
}
void Put() {
  inengmotor.stop();
  ServoPut();
  delay(PutWait);
}
void Put0() {
  inengmotor.stop();
  ServoPut0();
  delay(PutWait);
}
void GripUp() {
  inengmotor.stop();
  ServoGripUp();
  delay(ArmWait);
}
void GripDown() {
  inengmotor.stop();
  ServoGripDown();
  delay(ArmWait);
}
void GripDown2() {
  inengmotor.stop();
  ServoGripDown2();
  delay(ArmWait);
}
void GripDown3() {
  inengmotor.stop();
  ServoGripDown3();
  delay(ArmWait);
}
void GripDown4() {
  inengmotor.stop();
  ServoGripDown4();
  delay(ArmWait);
}
void GripDown5() {
  inengmotor.stop();
  ServoGripDown5();
  delay(ArmWait);
}


// =====================================================
// ท่าคีบ (GRAB) — สั่งจากท่ามือ "คีบ" ที่ Python ตรวจจับได้
// =====================================================
// 1. อ้าคีม
// 2. ลดแขนลง
// 3. หนีบของ
// 4. ยกแขนขึ้น
// ไม่ได้เปลี่ยนการทำงานของมอเตอร์รถ (แค่หยุดรถชั่วคราวระหว่างคีบ)
void grabObject() {
  Serial.println("========== GRAB START ==========");

  Put();       // 1. อ้าคีมก่อน
  GripDown();  // 2. ลดแขนลงเพื่อเตรียมหยิบของ
  Grip();      // 3. หนีบของ
  GripUp();    // 4. ยกของขึ้น

  Serial.println("========== GRAB DONE ==========");
}


void setup() {

  Serial.begin(115200);

  // เริ่ม Motor Library
  inengmotor.begin();

  // ตอนเริ่มให้รถหยุด
  inengmotor.stop();

  // เตรียมเซอร์โว (attach ขา + ตั้งท่าเริ่มต้น: อ้าคีม, ยกแขนขึ้น)
  InitServo();

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

      inengmotor.forward(185, 182);
    }

    // =============================
    // ถอยหลัง
    // =============================
    else if (command == "BACKWARD") {

      inengmotor.backward(185, 185);
    }

    // =============================
    // เลี้ยวซ้าย
    // =============================
    else if (command == "TURN_LEFT") {

      // inengmotor.turnLeft(120, 180);
      inengmotor.drive(-150, 150); 
      delay(800);
      inengmotor.stop();

    }

    // =============================
    // เลี้ยวขวา
    // =============================
    else if (command == "TURN_RIGHT") {

      inengmotor.drive(150, -150); 
      delay(800);
      inengmotor.stop();

    }

    // =============================
    // GRAB (ท่าคีบ: อ้าคีม -> ลดแขน -> หนีบ -> ยกแขนขึ้น)
    // =============================
    else if (command == "GRAB") {

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
