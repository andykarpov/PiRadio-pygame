/*
 * Raspberry Pi internet radio project
 * Arduino based knob controller using serial communication and quad encoder
 *
 * @author Andrey Karpov <andy.karpov@gmail.com>
 * @copyright 2012 Andrey Karpov
 */
 
 #include <Encoder.h>
 #include <Button.h>
 #include <Led.h>
 
 Encoder enc(2, 3); // encoder pins A and B connected to D2 and D3 
 Button btn(4, PULLUP); // encoder's button connected to GND and D4
 Led led_red(5); // encoder's red led connected to GND and D5 via 470 Ohm resistor
 Led led_green(6); // encoder's green led connected to GND and D6 via 470 Ohm resistor
 
 const int buf_len = 128; 
 char buf[buf_len];
 byte index = 0;
 char sep = ':';
 bool buffering = true;
 int enc_value = 0;
  
 /**
  * Setup routines
  *
  * @return void
  */
 void setup() {
   Serial.begin(9600);
   Serial.flush();
   led_green.off();
   led_red.off();
 }
 
 /**
  * Main loop
  *
  * @return void
  */
 void loop() {

   int e = enc.read();
   int b = btn.isPressed();
   
   if (e != enc_value || b) {
     enc_value = e;
     Serial.print(enc_value);
     Serial.print(':');
     Serial.println(b ? '1' : '0');
     if (b) {
       delay(500);
     }
   }
   
   readLine();
   if (!buffering) {
     processInput();
     index = 0;
     buf[index] = '\0';
     buffering = true;
   }
   
   delay(100);
 }
 
 /**
  * Fill internal buffer with a single line from the serial port 
  *
  * @return void
  */
 void readLine() {
   if (Serial.available())  {
     while (Serial.available()) {
         char c = Serial.read();
         if (c == '\n' || c == '\r' || index >= buf_len) {
           buffering = false;
         } else {
           buffering = true;
           buf[index] = c;
           index++;
           buf[index] = '\0';
         }
     }
   }
 }
 
 /**
  * Routine to compare input line from the serial port and perform a response, if required
  *
  * @return void
  */
 void processInput() {
     String content = String(buf);
  
     int pos = content.indexOf(sep);
     if (content.length() == 0 || pos < 0) return;
  
     String cmd = content.substring(0, pos);
     String arg = content.substring(pos+1);
     
     // command SET_ENC:<some integer> will set internal encoder value to the specified one     
     if (cmd.compareTo("SET_ENC") == 0) {
         int32_t enc_int = stringToInt(arg);
         enc_value = enc_int;
         enc.write(enc_int);
     } 
     
     // command LED_RED:X will swith on a red led if X=1, otherwise switch off 
     if (cmd.compareTo("LED_RED") == 0) {
         if (arg == "1") {
           led_red.on();
         } else {
           led_red.off();
         }
     } 

     // command LED_GREEN:X will swith on a green led if X=1, otherwise switch off      
     if (cmd.compareTo("LED_GREEN") == 0) {
         if (arg == "1") {
           led_green.on();
         } else {
           led_green.off();
         }   
     }    
 }
 
 /**
  * Conver string object into a signed integer value
  *
  * @param String s
  * @return int
  */
 int stringToInt(String s) {
     char this_char[s.length() + 1];
     s.toCharArray(this_char, sizeof(this_char));
     int result = atoi(this_char);     
     return result;
 }
 
