#include <InEngMotor.h>

// รับคำสั่งจาก Python
String command = "";

void setup() {

  // เริ่มต้น Motor Library
  inengmotor.begin();

  // เริ่ม Serial ที่ความเร็วเดียวกับ Python
  Serial.begin(19200);

  // ตอนเริ่มต้นให้รถหยุด
  inengmotor.stop();
}

void loop() {
  
  // มีข้อมูลส่งมาจาก Python หรือไม่
  if (Serial.available()) {

  Serial.println("มีข้อมูลเข้า Serial");

  command = Serial.readStringUntil('\n');

  Serial.print("Command ก่อน trim: ");
  Serial.println(command);

  command.trim();

  Serial.print("Command หลัง trim: ");
  Serial.println(command);

  if (command == "FORWARD") {

    Serial.println("เข้า FORWARD");
    inengmotor.forward(200, 200);
  }

  else if (command == "BACKWARD") {

    Serial.println("เข้า BACKWARD");
    inengmotor.backward(200, 200);
  }

  else if (command == "TURN_LEFT") {

    Serial.println("เข้า TURN_LEFT");
    inengmotor.turnLeft(80, 180);
  }

  else if (command == "TURN_RIGHT") {

    Serial.println("เข้า TURN_RIGHT");
    inengmotor.turnRight(180, 80);
  }

  else if (command == "GRAB") {

    Serial.println("เข้า GRAB");
    inengmotor.stop();
  }

  else if (command == "STOP") {

    Serial.println("เข้า STOP");
    inengmotor.stop();
  }

  else {

    Serial.println("ไม่รู้จักคำสั่ง");
  }
}
}