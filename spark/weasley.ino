#define SERVO_MAX 140
#define SERVO_PIN A0
#define NUM_LOCATIONS 3
#define LOG

Servo servo;

// Angles for positions on clock face
int locations_pos[NUM_LOCATIONS] = {22, 70, 118};
String locations[NUM_LOCATIONS] = {
    "HOME",
    "TRAVELLING",
    "WORK"
};

int new_location(String location) {
    #ifdef LOGGING
        Serial.print("Received function call from cloud, new_location(\": ");
        Serial.print(location);
        Serial.print("\");");
        Serial.println();
    #endif // LOGGING
    
    short i;
    for (i = 0; i < NUM_LOCATIONS; i++) {
        if (location.compareTo(locations[i]) == 0) {
            servo.write(locations_pos[i]);
            
            #ifdef LOGGING
                Serial.print(locations[i]);
            #endif // LOGGING
        }
    }
    
    return 0;
}

void setup() {
    servo.attach(A0);
    
    // Move through all location positions
    short i;
    for (i = 0; i < NUM_LOCATIONS; i++) {
        servo.write(locations_pos[i]);
    }
    servo.write(0);
    
    // Expose "move" function to the Spark Cloud API
    Spark.function("new_location", new_location);
    
    #ifdef LOGGING
        Serial.begin(9600);
    #endif // LOGGING
}

void loop() {
}
