// FIWARE Made Simple - Date and time over NTP on the ESP32
//
// Synchronizes the ESP32 clock with an NTP server and prints:
//   - the local time, already in the configured time zone;
//   - the UTC instant in ISO 8601 format (e.g., 2026-10-07T22:15:03Z),
//     the same format used by Orion and STH-Comet.
//
// Note: the IoT Agent already records when each measurement arrives
// (TimeInstant attribute). NTP is useful when the device itself needs to
// know the time: scheduling actions, logging events, or showing the time on a display.
//
// Author: Fábio Henrique Cabrini
// Revisions:
//   Rev1: 2023 Initial version - Fábio Henrique Cabrini
//   Rev2: 2026-10-07 Time zone with configTzTime (fixes the date around
//                    midnight) and ISO 8601 UTC output - Fábio Henrique Cabrini

#include <WiFi.h>
#include <time.h>

// ============================== Configuration ==============================
const char* WIFI_SSID     = "your_wifi_network";
const char* WIFI_PASSWORD = "your_wifi_password";

const char* NTP_SERVER = "pool.ntp.org";  // or your institution's NTP server
// Time zone in POSIX format. Examples:
//   UTC "UTC0" · New York "EST5EDT,M3.2.0,M11.1.0" · Los Angeles "PST8PDT,M3.2.0,M11.1.0"
//   London "GMT0BST,M3.5.0/1,M10.5.0" · Berlin "CET-1CEST,M3.5.0,M10.5.0/3" · Sao Paulo "<-03>3"
const char* TIME_ZONE = "UTC0";
// ===========================================================================

void setup() {
  Serial.begin(115200);
  Serial.printf("Connecting to Wi-Fi %s", WIFI_SSID);
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
  while (WiFi.status() != WL_CONNECTED) {
    delay(250);
    Serial.print(".");
  }
  Serial.printf("\nWi-Fi connected. IP: %s\n", WiFi.localIP().toString().c_str());

  configTzTime(TIME_ZONE, NTP_SERVER);
  Serial.print("Synchronizing with NTP");
  struct tm now;
  while (!getLocalTime(&now, 1000)) Serial.print(".");
  Serial.println(" ok");
}

void loop() {
  struct tm local;
  if (!getLocalTime(&local)) {
    Serial.println("Clock not synchronized yet");
    delay(1000);
    return;
  }

  time_t instant = time(nullptr);
  struct tm utc;
  gmtime_r(&instant, &utc);

  char localText[32], utcText[32];
  strftime(localText, sizeof(localText), "%Y-%m-%d %H:%M:%S", &local);
  strftime(utcText, sizeof(utcText), "%Y-%m-%dT%H:%M:%SZ", &utc);
  Serial.printf("Local: %s  |  UTC (ISO 8601): %s\n", localText, utcText);

  delay(1000);
}
