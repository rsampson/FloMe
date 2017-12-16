/*
  Inspired by -DIYhacking.com Arvind Sanjeev
  https://diyhacking.com/arduino-flow-rate-sensor/
  Measure the liquid/water flow rate using this code.
  Connect Vcc(red) and Gnd (black) of sensor to arduino, and the
  signal (yellow) line to arduino digital pin 2.
*/

#include <ESP8266WiFi.h>
#include <PubSubClient.h>
#include <ESP8266mDNS.h>
#include <WiFiUdp.h>
#include <ArduinoOTA.h>
#include "password.h" 

// defined in password.h
//const char* ssid = "xxxx";
//const char* password = "xxxx";

// These need to be configured for each installation
//const char* mqtt_server = "iot.eclipse.org";
// raspberrypi ip address
const char* mqtt_server = "192.168.0.106";
const char* topic = "yard/water/flow2";
const char* host_name = "flowmeter2";

WiFiClient espClient;
PubSubClient client(espClient);

byte sensorPin    = D2; //D2 on esp12, GPIO 4

// The hall-effect flow sensor outputs approximately 7.5 pulses per second per
// litre/minute of flow or 450 pulses per liter, 1703.4 pulses per gallon
volatile byte pulseCount;
unsigned long oldTime;

void setup()
{
  // Initialize a serial connection for reporting values to the host
  Serial.begin(19200);

  pinMode(sensorPin, INPUT_PULLUP);
  //digitalWrite(sensorPin, HIGH);

  // We start by connecting to a WiFi network
  Serial.println();
  Serial.print("Connecting to ");
  Serial.println(ssid);

  WiFi.begin(ssid, password);

  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }

  Serial.println("");
  Serial.println("WiFi connected");
  Serial.println("IP address: ");
  Serial.println(WiFi.localIP());

  client.setServer(mqtt_server, 1883);
  ArduinoOTA.setHostname(host_name);  // change this for different installations
  ArduinoOTA.begin(); 
  // The Hall-effect sensor is Configured to trigger on a FALLING state
  // change (transition from HIGH state to LOW state)
  attachInterrupt(digitalPinToInterrupt(sensorPin), pulseCounter, FALLING);
}

char message[20];

// RAS need to investigate why flow is passed to this
void reconnect(int flow) {
  // Loop until we're reconnected
  while (!client.connected()) {
    //Serial.print("Attempting MQTT connection...");
    // Create a random client ID
    String clientId = "ESP8266Client-";
    clientId += String(random(0xffff), HEX);
    // Attempt to connect
    if (client.connect(clientId.c_str())) {
       client.publish(topic, "connected");
    } else {
      Serial.print("failed, rc=");
      Serial.print(client.state());
      //Serial.println(" try again in 5 seconds");
      // Wait 5 seconds before retrying
      delay(5000);
    }
  }
}

void loop()
{
  ArduinoOTA.handle();
  if ((millis() - oldTime) > 2000) // Only process once per 2 second
  {
    // Disable the interrupt while calculating flow rate and sending the value to
    // the host
    detachInterrupt(sensorPin);

    // Note the time this processing pass was executed. Note that because we've
    // disabled interrupts the millis() function won't actually be incrementing right
    // at this point so keep the processing short.
    oldTime = millis();


    if (!client.connected()) {
      reconnect(pulseCount);
    }
    //client.loop();
    sprintf(message, "%d", pulseCount);   
    client.publish(topic, message);
    //Serial.print("Pulses: ");
    Serial.println(pulseCount);
    // Reset the pulse counter so we can start incrementing again
    pulseCount = 0;

    // Enable the interrupt again now that we've finished sending output
    attachInterrupt(digitalPinToInterrupt(sensorPin), pulseCounter, FALLING);
  }
}

//Interrupt Service Routine
void pulseCounter()
{
  pulseCount++;
}
