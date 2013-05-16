/**
 * IR receiver module to translate Apple Remote codes 
 * into the simple serial port commands, like "up", "down", "left", "right", etc.
 *
 * @author Andy Karpov <andy.karpov@gmail.com>
 * @copyright 2013 Andy Karpov
 */

#include <IRremote.h>

int RECV_PIN = 11;

// apple silver remote keycodes
#define KEY_UP 2011287715
#define KEY_DOWN 2011279523
#define KEY_LEFT 2011238563
#define KEY_RIGHT 2011291811
#define KEY_OK 2011282083
#define KEY_MENU 2011250851
#define KEY_PLAY 2011265699

IRrecv irrecv(RECV_PIN);

decode_results results;

void setup()
{
  Serial.begin(9600);
  irrecv.enableIRIn(); // Start the receiver
}

void loop() {
  if (irrecv.decode(&results)) {
    switch (results.value) {
      case KEY_UP:
        Serial.println("up");
      break;
      case KEY_DOWN:
        Serial.println("down");
      break;
      case KEY_LEFT:
        Serial.println("left");
      break;
      case KEY_RIGHT:
        Serial.println("right");
      break;
      case KEY_OK:
        Serial.println("ok");
      break;
      case KEY_MENU:
        Serial.println("menu");
      break;
      case KEY_PLAY:
        Serial.println("play");
      break;
    }
    irrecv.resume(); // Receive the next value
  }
}
