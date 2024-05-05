#include <Wire.h>
#include <Adafruit_GFX.h>
#include <Adafruit_SSD1306.h>
#include <ETH.h>
#include "time.h"
#include <Ethernet.h>  
#include <NTPClient.h>
#include <EthernetUdp.h> // For Ethernet NTP
#include <EthernetUdp.h>
#include "SD_MMC.h"

#define SCREEN_WIDTH 128
#define SCREEN_HEIGHT 64
#define OLED_RESET    -1 // Reset pin # (or -1 if sharing Arduino reset pin)
Adafruit_SSD1306 display(SCREEN_WIDTH, SCREEN_HEIGHT, &Wire, OLED_RESET);

#define LED_PIN 1 // Change this to the pin where your LED is connected
#define BUTTON_PIN 34 // PIN 34 IS BUT1 ON THE ESP
#define SENSOR_PIN 35 // PIN FOR THE SENSOR
#define NTP_SERVER "pool.ntp.org"
boolean isLedState = true;

// Timing
const long blinkInterval = 1000; 
const long NTP_UPDATE_INTERVAL = 15000; // Update NTP every 15 seconds
unsigned long lastNTPUpdate = 0;

//Delay
const int delayArraySize = 5;
int sensorDataCount = 0;
float mean = 0.0;
float stdDev = 0.0;
int delayArr[delayArraySize];//delay array
time_t timestamps[delayArraySize];//timestamp array, timestamp per array
// *** Ethernet Configuration ***
/*PLACEHOLDER
byte mac[] = { 0xDE, 0xAD, 0xBE, 0xEF, 0xFE, 0xED }; 
IPAddress gateway(192, 168, 1, 1); // Gateway IP address
IPAddress ip(192, 168, 1, 10);
IPAddress subnet(255, 255, 255, 0); 
*/
// NTP Settings
EthernetUDP ntpUDP;
NTPClient timeClient(ntpUDP, "pool.ntp.org"); 

time_t current_time;

void setup() {
  Serial.begin(115200);

  pinMode(LED_PIN, OUTPUT); // Set the LED pin as an output
  pinMode(BUTTON_PIN, INPUT_PULLUP); // Set the button pin as input with pull-up resistor

  Wire.begin();
  if (!display.begin(SSD1306_SWITCHCAPVCC, 0x3C)) {
    Serial.println(F("SSD1306 allocation failed"));
    for (;;);
  }
  display.clearDisplay();
  display.setTextSize(1);
  display.setTextColor(SSD1306_WHITE);
  //NTP setup
  // Initialize Ethernet
  /* 
  Ethernet.begin(mac, ip, subnet);
  if (Ethernet.linkStatus() == LinkON) {
    Serial.println("Ethernet connected");
  } else {
    Serial.println("Ethernet connection failed");
  }*/
  //SD CARD PREP
   if(!SD_MMC.begin("/sdcard", true)) {
    Serial.println("SD Card Mount Failed");
   return;
    }
  Serial.println("Card Mounted");

  

  //STARTS THE NTP TASK, NEEDS TO BE CORRECTLY IMPLEMENTED.
  /*xTaskCreatePinnedToCore(
    ntpUpdateTask,      // Task function
    "ntpUpdateTask",    // Task name
    10000,              // Stack size (bytes)
    NULL,               // Task parameters
    1,                  // Task priority (1 is the highest priority)
    NULL,               // Task handle (optional)
    1                   // Core to run the task on (0 or 1)
  );*/
}

void loop() {
    
  time(&current_time);
  struct tm time_info;
  localtime_r(&current_time, &time_info);
    //display.setTextSize(1);
    
    // Check if the button is pressed
    if (digitalRead(BUTTON_PIN) == LOW) {
        display.clearDisplay();
        // If the button is pressed, toggle the LED state
        isLedState = !isLedState;
        delay(500); // Add a small delay to debounce the button
    }
   
    if (isLedState==true) {  
      display.clearDisplay();
      display.setCursor(0, 18);
      display.println(current_time);
      if(current_time % 2 == 0){
        digitalWrite(LED_PIN, HIGH); // Turn on the LED
      }else{
        digitalWrite(LED_PIN, LOW); // Turn on the LED
      }
      display.setCursor(0, 0);
      display.println(F("SYNC STATUS:---"));
      display.setCursor(0, 9);
      display.println(F("CURRENT STATE:LED"));
    }else if (isLedState == false){
      
       //Reset the screen
      display.clearDisplay();
      display.display();
      //Defines the sum of delays
      int sumOfDelays = 0;
      //sets both mean and standard deviation to 0, these will be recalculated with each loop
      mean = 0;
      stdDev = 0;
      display.setCursor(0, 0);
      display.println(F("SYNC STATUS:---"));
      display.setCursor(0, 9);
      display.println(F("CURRENT STATE:SENSOR"));
      //SENSOR CODE GOES HERE, replace the random generation
      //int randomNumber = 0;
        int randomNumber = random(2000001); // random() generates numbers from 0 to n-1, so we use 2000001
        delayArr[sensorDataCount]=randomNumber;
        //Serial.print(sensorDataCount);
        timestamps[sensorDataCount] = time(nullptr); //gets a timestamp to when the sensor picked up that signal
      //Replace the code above with the sensor code

      display.setCursor(0, 18);
      display.print(F("DELAY:"));
      display.println(delayArr[sensorDataCount]);
      sensorDataCount += 1;
      //Calculate mean
      for (int i = 0; i < sensorDataCount; i++) {
        sumOfDelays += delayArr[i];
      }
      mean = sumOfDelays / sensorDataCount;
      display.setCursor(0, 27);
      display.print(F("MEAN:"));
      display.println(mean);
      // Calculate standard deviation
      for (int i = 0; i < sensorDataCount; i++) {
        stdDev += pow(delayArr[i] - mean, 2);
      }
      stdDev = sqrt(stdDev / sensorDataCount);
      display.setCursor(0, 36);
      display.print(F("STD DEV:"));
      display.println(stdDev);
      display.setCursor(0, 45);
      
      if (sensorDataCount == delayArraySize) {
        //save the data to sd card before reset
        writeToFile(SD_MMC, "/data.txt", delayArr, timestamps, mean, stdDev);
        display.setCursor(0, 45);
        display.println(F("SAVED TO SD CARD:"));
        display.display();  
        // Reset sensor data count and delayArr
        sensorDataCount = 0;
        randomNumber = 0;
        memset(delayArr, 0, sizeof(delayArr));
        memset(timestamps, 0, sizeof(timestamps));
        mean = 0;
        stdDev = 0.0;
        
        delay(2000);
      }else{
        display.display();
        delay(2000);
      }

    }
  

 
  
  display.display();
  //delay(1000);
  
  //delay(2000);
}
void blinkLed() {
    digitalWrite(LED_PIN, HIGH); // Turn on the LED
    delay(1000);
    digitalWrite(LED_PIN, LOW); // Turn off the LED
}
void ntpUpdateTask(void *pvParameters) {
  // HERE GOES THE CODE FOR UPDATING TIME WITH NTP SERVER
  /*THIS IS A PLACE HOLDER
  Ethernet.begin(mac, ip, gateway, gateway, subnet);
  timeClient.begin();
  timeClient.update(); // Get initial time
  //lastNTPUpdate = millis();
  
  
   THIS IS A PLACE HOLDER
  for (;;) {
    
      timeClient.update();
      
      vTaskDelay(pdMS_TO_TICKS(NTP_UPDATE_INTERVAL));
      
    }*/
    
  }


void writeToFile(fs::FS &fs, const char * path, int delayArr[], time_t timestamps[], float mean, float stdDev){
    Serial.printf("Writing to file: %s\n", path);

    // Get current timestamp
    time_t current_time = static_cast<time_t>(timeClient.getEpochTime());
    struct tm timeinfo;
    gmtime_r(&current_time, &timeinfo);

    char filename[32]; // Buffer to hold filename
    sprintf(filename, "/logfile_%04d%02d%02d_%02d%02d%02d.txt", 
            timeinfo.tm_year + 1900, timeinfo.tm_mon + 1, timeinfo.tm_mday,
            timeinfo.tm_hour, timeinfo.tm_min, timeinfo.tm_sec);

    File file = fs.open(filename, FILE_WRITE);
    if(!file){
        Serial.println("Failed to open file for writing");
        return;
    }
   // Write header
    file.println("Delays");

    // Write data
    char timestampStr[20];
    for (int i = 0; i < delayArraySize; i++) {
        strftime(timestampStr, sizeof(timestampStr), "%Y-%m-%d %H:%M:%S", localtime(&timestamps[i]));
        file.println(timestampStr);
        file.println(delayArr[i]);
        //file.print(",");
    }
    file.println("Mean");
    file.println(mean);
    file.println("Standard deviation");
    file.println(stdDev);
    delay(1000);
    file.close();
    Serial.println("Data written to file.");
}
