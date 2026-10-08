// FIWARE Made Simple - Smart Lamp (ESP32 DevKit V1)
//
// Measures luminosity with an LDR module and turns the onboard LED on and off
// using commands received from the IoT Agent UltraLight 2.0 over MQTT.
//
//   publishes  /<apikey>/<device_id>/attrs/l   luminosity (0 to 100)
//   publishes  /<apikey>/<device_id>/attrs     LED state: s|on or s|off
//   subscribes /<apikey>/<device_id>/cmd       commands: <device_id>@on| or <device_id>@off|
//   publishes  /<apikey>/<device_id>/cmdexe    confirmation: <device_id>@on|ok
//
// Libraries: WiFi (built into the ESP32 core) and PubSubClient (Nick O'Leary).
//
// Author: Fábio Henrique Cabrini
// Revisions:
//   Rev1: 2023-08-26 Port to the ESP32 and luminosity reading - Lucas Demetrius Augusto
//   Rev2: 2023-08-28 Adjustments for FIWARE Made Simple - Fábio Henrique Cabrini
//   Rev3: 2023-11-01 Code refinements - Fábio Henrique Cabrini
//   Rev4: 2026-10-07 Command confirmation (cmdexe), non-blocking publishing without
//                    delay(), state published only when it changes, unique client ID,
//                    and optional MQTT authentication - Fábio Henrique Cabrini

#include <WiFi.h>
#include <PubSubClient.h>

// ============================== Configuration ==============================
const char* WIFI_SSID     = "your_wifi_network";
const char* WIFI_PASSWORD = "your_wifi_password";

const char* MQTT_BROKER   = "fiware_server_ip";
const int   MQTT_PORT     = 1883;
const char* MQTT_USER     = "";  // fill in if Mosquitto requires authentication
const char* MQTT_PASSWORD = "";

const char* APIKEY    = "TEF";      // service group apikey (step 2.1 of the collection)
const char* DEVICE_ID = "lamp001";  // provisioned device_id (step 2.3 of the collection)

const int LED_PIN = 2;   // onboard LED of the DevKit V1
const int LDR_PIN = 34;  // AO output of the LDR module (ADC input)

const unsigned long LUMINOSITY_INTERVAL_MS = 5000;   // luminosity publishing
const unsigned long STATE_INTERVAL_MS      = 60000;  // periodic state republishing
const unsigned long RECONNECT_INTERVAL_MS  = 2000;   // new attempt to reach the broker
// ===========================================================================

WiFiClient wifiClient;
PubSubClient mqtt(wifiClient);

String attrsTopic, luminosityTopic, cmdTopic, cmdExeTopic, clientId;

bool ledOn = false;
unsigned long lastLuminosityPublish = 0;
unsigned long lastStatePublish = 0;
unsigned long lastMqttAttempt = 0;

void publishState() {
  const char* message = ledOn ? "s|on" : "s|off";
  mqtt.publish(attrsTopic.c_str(), message);
  lastStatePublish = millis();
  Serial.printf("-> %s %s\n", attrsTopic.c_str(), message);
}

void publishLuminosity() {
  int reading = analogRead(LDR_PIN);
  // If your module reports higher values in the dark, invert it: map(reading, 0, 4095, 100, 0)
  int luminosity = map(reading, 0, 4095, 0, 100);
  String message = String(luminosity);
  mqtt.publish(luminosityTopic.c_str(), message.c_str());
  Serial.printf("-> %s %s\n", luminosityTopic.c_str(), message.c_str());
}

void confirmCommand(const String& command, const char* result) {
  String message = String(DEVICE_ID) + "@" + command + "|" + result;
  mqtt.publish(cmdExeTopic.c_str(), message.c_str());
  Serial.printf("-> %s %s\n", cmdExeTopic.c_str(), message.c_str());
}

void setLed(bool on) {
  ledOn = on;
  digitalWrite(LED_PIN, on ? HIGH : LOW);
}

// Command messages in UltraLight 2.0 format: <device_id>@<command>|<parameters>
void onMessage(char* topic, byte* payload, unsigned int length) {
  String message;
  for (unsigned int i = 0; i < length; i++) message += (char)payload[i];
  Serial.printf("<- %s %s\n", topic, message.c_str());

  int at = message.indexOf('@');
  int bar = message.indexOf('|', at + 1);
  if (at < 0) return;
  String device = message.substring(0, at);
  String command = message.substring(at + 1, bar < 0 ? message.length() : bar);
  if (device != DEVICE_ID) return;

  if (command == "on") {
    setLed(true);
    confirmCommand(command, "ok");
  } else if (command == "off") {
    setLed(false);
    confirmCommand(command, "ok");
  } else {
    confirmCommand(command, "unknown command");
    return;
  }
  publishState();
}

void connectWiFi() {
  Serial.printf("Connecting to Wi-Fi %s", WIFI_SSID);
  WiFi.mode(WIFI_STA);
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
  while (WiFi.status() != WL_CONNECTED) {
    delay(250);
    Serial.print(".");
  }
  Serial.printf("\nWi-Fi connected. IP: %s\n", WiFi.localIP().toString().c_str());
}

// Non-blocking: tries once and returns to the loop, retrying every RECONNECT_INTERVAL_MS
void connectMqtt() {
  if (millis() - lastMqttAttempt < RECONNECT_INTERVAL_MS) return;
  lastMqttAttempt = millis();

  Serial.printf("Connecting to broker %s:%d as %s... ", MQTT_BROKER, MQTT_PORT, clientId.c_str());
  bool connected = strlen(MQTT_USER) > 0
                       ? mqtt.connect(clientId.c_str(), MQTT_USER, MQTT_PASSWORD)
                       : mqtt.connect(clientId.c_str());
  if (!connected) {
    Serial.printf("failed (state %d)\n", mqtt.state());
    return;
  }
  Serial.println("connected");
  mqtt.subscribe(cmdTopic.c_str());
  publishState();
  publishLuminosity();
  lastLuminosityPublish = millis();
}

void setup() {
  Serial.begin(115200);
  pinMode(LED_PIN, OUTPUT);
  for (int i = 0; i < 6; i++) {  // blink at startup
    digitalWrite(LED_PIN, i % 2 == 0 ? HIGH : LOW);
    delay(150);
  }
  setLed(false);

  String base = String("/") + APIKEY + "/" + DEVICE_ID;
  attrsTopic      = base + "/attrs";
  luminosityTopic = base + "/attrs/l";
  cmdTopic        = base + "/cmd";
  cmdExeTopic     = base + "/cmdexe";
  // Unique client ID per board: two clients with the same ID keep kicking each other off the broker
  clientId = String("fiware-") + DEVICE_ID + "-" + String((uint32_t)ESP.getEfuseMac(), HEX);

  connectWiFi();
  mqtt.setServer(MQTT_BROKER, MQTT_PORT);
  mqtt.setCallback(onMessage);
}

void loop() {
  if (WiFi.status() != WL_CONNECTED) {
    connectWiFi();
    return;
  }
  if (!mqtt.connected()) {
    connectMqtt();
    return;
  }
  mqtt.loop();

  unsigned long now = millis();
  if (now - lastLuminosityPublish >= LUMINOSITY_INTERVAL_MS) {
    lastLuminosityPublish = now;
    publishLuminosity();
  }
  if (now - lastStatePublish >= STATE_INTERVAL_MS) {
    publishState();
  }
}
