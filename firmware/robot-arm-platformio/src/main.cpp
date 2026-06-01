#include <Arduino.h>
#include <Wire.h>
#include <WiFi.h>
#include <Adafruit_PWMServoDriver.h>
#include <math.h>
#include <stdlib.h>
#include <string.h>

#if __has_include("config.h")
#include "config.h"
#else
#define WIFI_SSID ""
#define WIFI_PASSWORD ""
#define AP_SSID "ROBOT_ARM_PICO"
#define AP_PASSWORD "robot12345"
#endif

#ifndef SERIAL_BAUD
#define SERIAL_BAUD 115200
#endif

#ifndef TCP_PORT
#define TCP_PORT 7777
#endif

#ifndef I2C_SDA_PIN
#define I2C_SDA_PIN 4
#endif

#ifndef I2C_SCL_PIN
#define I2C_SCL_PIN 5
#endif

#ifndef PCA9685_ADDRESS
#define PCA9685_ADDRESS 0x40
#endif

#ifndef SERVO_EE_CHANNEL
#define SERVO_EE_CHANNEL 0
#endif

#ifndef SERVO_Q1_CHANNEL
#define SERVO_Q1_CHANNEL 1
#endif

#ifndef SERVO_Q2_CHANNEL
#define SERVO_Q2_CHANNEL 2
#endif

#ifndef SERVO_Q3_CHANNEL
#define SERVO_Q3_CHANNEL 3
#endif

#ifndef BUZZER_PIN
#define BUZZER_PIN 15
#endif

static constexpr uint16_t kServoMinUs = 500;
static constexpr uint16_t kServoMaxUs = 2500;
static constexpr uint16_t kServoFreqHz = 50;
static constexpr size_t kBufferSize = 128;
static constexpr uint32_t kWifiTimeoutMs = 15000;

Adafruit_PWMServoDriver pwm(PCA9685_ADDRESS);
WiFiServer tcpServer(TCP_PORT);
WiFiClient tcpClient;

struct ServoMove {
  uint8_t channel;
  float currentDeg;
  float startDeg;
  float targetDeg;
  uint32_t startMs;
  uint32_t durationMs;
  bool moving;
};

ServoMove servos[] = {
    {SERVO_EE_CHANNEL, 90.0f, 90.0f, 90.0f, 0, 0, false},
    {SERVO_Q1_CHANNEL, 90.0f, 90.0f, 90.0f, 0, 0, false},
    {SERVO_Q2_CHANNEL, 90.0f, 90.0f, 90.0f, 0, 0, false},
    {SERVO_Q3_CHANNEL, 90.0f, 90.0f, 90.0f, 0, 0, false},
};

struct MessageReader {
  char buffer[kBufferSize];
  size_t received;
  bool active;
  bool ready;
};

MessageReader serialReader = {{0}, 0, false, false};
MessageReader wifiReader = {{0}, 0, false, false};

char instruction[16] = "BUZZ";
float requestedAngles[4] = {90.0f, 90.0f, 90.0f, 90.0f};
uint32_t requestedTimes[4] = {1000, 1000, 1000, 1000};

uint16_t angleToPulseUs(float angle) {
  angle = constrain(angle, 0.0f, 180.0f);
  return static_cast<uint16_t>(kServoMinUs + ((kServoMaxUs - kServoMinUs) * angle / 180.0f));
}

void writeServo(uint8_t channel, float angle) {
  pwm.writeMicroseconds(channel, angleToPulseUs(angle));
}

float easeInOutCubic(float t) {
  if (t < 0.5f) {
    return 4.0f * t * t * t;
  }
  const float p = -2.0f * t + 2.0f;
  return 1.0f - (p * p * p) / 2.0f;
}

void startServoMove(ServoMove &servo, float targetDeg, uint32_t durationMs) {
  targetDeg = constrain(targetDeg, 0.0f, 180.0f);
  servo.startDeg = servo.currentDeg;
  servo.targetDeg = targetDeg;
  servo.startMs = millis();
  servo.durationMs = durationMs < 20 ? 20 : durationMs;
  servo.moving = fabsf(servo.targetDeg - servo.startDeg) > 0.1f;

  if (!servo.moving) {
    servo.currentDeg = servo.targetDeg;
    writeServo(servo.channel, servo.currentDeg);
  }
}

void updateServos() {
  const uint32_t now = millis();
  for (ServoMove &servo : servos) {
    if (!servo.moving) {
      continue;
    }

    const uint32_t elapsed = now - servo.startMs;
    if (elapsed >= servo.durationMs) {
      servo.currentDeg = servo.targetDeg;
      servo.moving = false;
    } else {
      const float t = static_cast<float>(elapsed) / static_cast<float>(servo.durationMs);
      const float eased = easeInOutCubic(t);
      servo.currentDeg = servo.startDeg + (servo.targetDeg - servo.startDeg) * eased;
    }
    writeServo(servo.channel, servo.currentDeg);
  }
}

void blinkLed(uint8_t count = 1) {
  for (uint8_t i = 0; i < count; i++) {
    digitalWrite(LED_BUILTIN, HIGH);
    delay(70);
    digitalWrite(LED_BUILTIN, LOW);
    delay(70);
  }
}

void playTone() {
  tone(BUZZER_PIN, 650, 160);
}

bool parseIncomingMessage(char *message) {
  char *token = strtok(message, ",");
  if (token == nullptr) {
    return false;
  }
  strncpy(instruction, token, sizeof(instruction) - 1);
  instruction[sizeof(instruction) - 1] = '\0';

  for (float &angle : requestedAngles) {
    token = strtok(nullptr, ",");
    if (token == nullptr) {
      return false;
    }
    angle = atof(token);
  }

  for (uint32_t &moveTime : requestedTimes) {
    token = strtok(nullptr, ",");
    if (token == nullptr) {
      return false;
    }
    const int parsedTime = atoi(token);
    moveTime = static_cast<uint32_t>(parsedTime < 20 ? 20 : parsedTime);
  }

  return true;
}

void feedReader(MessageReader &reader, char c) {
  if (c == '<') {
    reader.received = 0;
    reader.active = true;
    reader.ready = false;
    return;
  }

  if (c == '>' && reader.active) {
    reader.buffer[reader.received] = '\0';
    reader.active = false;
    reader.ready = true;
    return;
  }

  if (reader.active && reader.received < kBufferSize - 1) {
    reader.buffer[reader.received++] = c;
  }
}

void receiveSerialData() {
  while (Serial.available() > 0 && !serialReader.ready) {
    feedReader(serialReader, static_cast<char>(Serial.read()));
  }
}

void receiveWifiData() {
  if (!tcpClient || !tcpClient.connected()) {
    tcpClient = tcpServer.accept();
    if (tcpClient) {
      tcpClient.setNoDelay(true);
      tcpClient.println("<HELLO robot-arm>");
    }
  }

  while (tcpClient && tcpClient.connected() && tcpClient.available() > 0 && !wifiReader.ready) {
    feedReader(wifiReader, static_cast<char>(tcpClient.read()));
  }
}

void runInstruction() {
  if (strcmp(instruction, "LED") == 0) {
    blinkLed(1);
  } else if (strcmp(instruction, "BUZZ") == 0) {
    playTone();
  }

  startServoMove(servos[0], requestedAngles[0], requestedTimes[0]);
  startServoMove(servos[1], requestedAngles[1], requestedTimes[1]);
  startServoMove(servos[2], requestedAngles[2], requestedTimes[2]);
  startServoMove(servos[3], requestedAngles[3], requestedTimes[3]);
}

void printReplyTo(Print &out, bool ok) {
  out.print('<');
  out.print(ok ? "OK" : "ERR");
  out.print(",msg=");
  out.print(instruction);
  out.print(",ee=");
  out.print(requestedAngles[0], 1);
  out.print(",q1=");
  out.print(requestedAngles[1], 1);
  out.print(",q2=");
  out.print(requestedAngles[2], 1);
  out.print(",q3=");
  out.print(requestedAngles[3], 1);
  out.print(",uptime=");
  out.print(millis());
  out.println('>');
}

void setupWifi() {
  WiFi.mode(WIFI_STA);

  if (strlen(WIFI_SSID) > 0) {
    Serial.print("Connecting to WiFi SSID: ");
    Serial.println(WIFI_SSID);
    WiFi.begin(WIFI_SSID, WIFI_PASSWORD);

    const uint32_t start = millis();
    while (WiFi.status() != WL_CONNECTED && millis() - start < kWifiTimeoutMs) {
      delay(250);
      Serial.print('.');
    }
    Serial.println();

    if (WiFi.status() == WL_CONNECTED) {
      Serial.print("WiFi connected. Robot IP: ");
      Serial.println(WiFi.localIP());
      tcpServer.begin();
      return;
    }

    Serial.println("WiFi station failed; starting access point.");
  }

  WiFi.mode(WIFI_AP);
  WiFi.softAP(AP_SSID, AP_PASSWORD);
  delay(250);
  Serial.print("Access point started. SSID: ");
  Serial.print(AP_SSID);
  Serial.print(" password: ");
  Serial.print(AP_PASSWORD);
  Serial.print(" IP: ");
  Serial.println(WiFi.softAPIP());
  tcpServer.begin();
}

void setup() {
  pinMode(LED_BUILTIN, OUTPUT);
  pinMode(BUZZER_PIN, OUTPUT);
  blinkLed(2);

  Serial.begin(SERIAL_BAUD);
  delay(1000);
  Serial.println();
  Serial.println("<Robot arm controller boot>");

  Wire.setSDA(I2C_SDA_PIN);
  Wire.setSCL(I2C_SCL_PIN);
  Wire.begin();

  pwm.begin();
  pwm.setOscillatorFrequency(27000000);
  pwm.setPWMFreq(kServoFreqHz);
  delay(10);

  for (ServoMove &servo : servos) {
    writeServo(servo.channel, servo.currentDeg);
  }

  setupWifi();
  playTone();
  Serial.println("<READY>");
}

void loop() {
  receiveSerialData();
  receiveWifiData();

  if (serialReader.ready) {
    const bool ok = parseIncomingMessage(serialReader.buffer);
    if (ok) {
      runInstruction();
    }
    printReplyTo(Serial, ok);
    serialReader.ready = false;
  }

  if (wifiReader.ready) {
    const bool ok = parseIncomingMessage(wifiReader.buffer);
    if (ok) {
      runInstruction();
    }
    printReplyTo(Serial, ok);
    if (tcpClient && tcpClient.connected()) {
      printReplyTo(tcpClient, ok);
    }
    wifiReader.ready = false;
  }

  updateServos();
}
