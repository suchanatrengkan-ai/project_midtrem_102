#include "HUSKYLENS.h"
#include "Wire.h"

HUSKYLENS huskylens;

// ================================
// กำหนดชื่อสีตาม ID
// ================================
String getColorName(int id)
{
    if (id == 1)
    {
        return "CYAN";
    }
    else if (id == 2)
    {
        return "ORANGE";
    }
    else if (id == 3)
    {
        return "GREEN";
    }
    else if (id == 4)
    {
        return "RED";
    }
    else if (id == 5)
    {
        return "PURPLE";
    }
    else if (id == 6)
    {
        return "BLUE";
    }
    {
        return "UNKNOWN";
    }
}

// ================================
// SETUP
// ================================
void setup()
{
    Serial.begin(115200);

    // ESP32
    // SDA = GPIO 21
    // SCL = GPIO 22
    Wire.begin(21, 22);

    Serial.println();
    Serial.println("==============================");
    Serial.println("HUSKYLENS COLOR SORTER");
    Serial.println("==============================");

    Serial.println("Connecting to HUSKYLENS...");

    while (!huskylens.begin(Wire))
    {
        Serial.println("HUSKYLENS connection failed!");
        Serial.println("Check I2C cable, protocol and power");
        delay(1000);
    }

    Serial.println("HUSKYLENS connected!");
    Serial.println();

    Serial.println("ID 1 = ORANGE");
    Serial.println("ID 2 = PURPLE");
    Serial.println("ID 3 = RED");
    Serial.println("ID 4 = GREEN");
    /*Serial.println("ID 5 = PURPLE");
    Serial.println("ID 6 = BLUE");

    Serial.println();
    Serial.println("Waiting for object...");*/
}

// ================================
// LOOP
// ================================
void loop()
{
    // ขอข้อมูลจาก HUSKYLENS
    if (!huskylens.request())
    {
        Serial.println("Request failed!");
        delay(200);
        return;
    }

    // ตรวจสอบว่าเรียนรู้สีแล้วหรือยัง
    if (!huskylens.isLearned())
    {
        Serial.println("No color has been learned.");
        delay(500);
        return;
    }

    // ตรวจสอบว่ามีวัตถุหรือไม่
    if (!huskylens.available())
    {
        Serial.println("No color detected.");
        delay(200);
        return;
    }

    // อ่านข้อมูล
    while (huskylens.available())
    {
        HUSKYLENSResult result = huskylens.read();

        int id = result.ID;
        String color = getColorName(id);

        int x = result.xCenter;
        int y = result.yCenter;

        int width = result.width;
        int height = result.height;

        // ================================
        // แสดงข้อมูล
        // ================================

        Serial.println("------------------------------");

        Serial.print("ID       : ");
        Serial.println(id);

        Serial.print("COLOR    : ");
        Serial.println(color);

        Serial.print("X        : ");
        Serial.println(x);

        Serial.print("Y        : ");
        Serial.println(y);

        Serial.print("WIDTH    : ");
        Serial.println(width);

        Serial.print("HEIGHT   : ");
        Serial.println(height);

        // ================================
        // ตรวจสอบตำแหน่ง
        // ================================

        if (x < 100)
        {
            Serial.println("DIRECTION: LEFT");
        }
        else if (x > 220)
        {
            Serial.println("DIRECTION: RIGHT");
        }
        else
        {
            Serial.println("DIRECTION: CENTER");
        }

        // ================================
        // เลือกช่องตามสี
        // ================================

        if (id == 1)
        {
            Serial.println("TARGET BIN: ORANGE");
        }
        else if (id == 2)
        {
            Serial.println("TARGET BIN: PURPLE");
        }
        else if (id == 3)
        {
            Serial.println("TARGET BIN: RED");
        }
        else if (id == 4)
        {
            Serial.println("TARGET BIN: GREEN");
        }
        /*else if (id == 5)
        {
            Serial.println("TARGET BIN: PURPLE");
        }else if (id == 6)
        {
            Serial.println("TARGET BIN: BLUE");
        }
        else
        {
            Serial.println("TARGET BIN: UNKNOWN");
        }

        Serial.println("------------------------------");*/
    }

    delay(100);
}