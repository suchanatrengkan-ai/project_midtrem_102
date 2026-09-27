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