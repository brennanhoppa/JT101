#include <AccelStepper.h>

#define X_STEP_PIN 2
#define X_DIR_PIN 3
#define X_ENABLE_PIN 4
#define Y_STEP_PIN 5
#define Y_DIR_PIN 6
#define Y_ENABLE_PIN 7
#define X_LIMIT_SWITCH_MIN A5  // Limit switch for X-axis
#define Y_LIMIT_SWITCH_MIN A0  // Limit switch for Y-axis
#define X_LIMIT_SWITCH_MAX A3
#define Y_LIMIT_SWITCH_MAX A2
#define MOTOR_INTERFACE_TYPE AccelStepper::DRIVER
#define DEBOUNCE_DELAY 20  // milliseconds

struct LimitSwitch {
  uint8_t pin;
  bool stableState;
  bool lastRawState;
  unsigned long lastChangeTime;
};

struct HomingResult {
    int stepsX;
    int stepsY;
};

AccelStepper stepperX(MOTOR_INTERFACE_TYPE, X_STEP_PIN, X_DIR_PIN);
AccelStepper stepperY(MOTOR_INTERFACE_TYPE, Y_STEP_PIN, Y_DIR_PIN);

LimitSwitch xMin = {X_LIMIT_SWITCH_MIN, false, false, 0};
LimitSwitch xMax = {X_LIMIT_SWITCH_MAX, false, false, 0};
LimitSwitch yMin = {Y_LIMIT_SWITCH_MIN, false, false, 0};
LimitSwitch yMax = {Y_LIMIT_SWITCH_MAX, false, false, 0};

// Variables to track cumulative positions
long cumulativeTargetX = 0;
long cumulativeTargetY = 0;

int motorSpeed = 15000; // 5000 for microscope, 15000 for camera
int motorAcceleration = 22000; // 2000 for microscope, 22000 for camera

bool homeSetX = false;
bool homeSetY = false;

bool verboseMode = false;

void setup() {
  Serial.begin(500000);
  
  pinMode(X_ENABLE_PIN, OUTPUT);
  pinMode(Y_ENABLE_PIN, OUTPUT);
  pinMode(xMin.pin, INPUT_PULLUP);
  pinMode(xMax.pin, INPUT_PULLUP);
  pinMode(yMin.pin, INPUT_PULLUP);
  pinMode(yMax.pin, INPUT_PULLUP);

  digitalWrite(X_ENABLE_PIN, LOW);
  digitalWrite(Y_ENABLE_PIN, LOW);
  
  stepperX.setMaxSpeed(motorSpeed);
  stepperY.setMaxSpeed(motorSpeed);
  stepperX.setAcceleration(motorAcceleration);
  stepperY.setAcceleration(motorAcceleration);
}

void loop() {
  if (Serial.available()) {
    processCommand(Serial.readStringUntil('\n'));
  }

  checkLimitSwitches();  // Prevents moves into switches

  stepperX.run();
  stepperY.run();
}

void processCommand(String command) {
  char direction = command[0];
  int steps = command.substring(1).toInt();

  switch(direction) {
    case 'U': {
      cumulativeTargetY += steps;
      stepperY.moveTo(cumulativeTargetY);
      break;}
    case 'D': { 
      cumulativeTargetY -= steps;
      stepperY.moveTo(cumulativeTargetY);
      break;}
    case 'L': { 
      cumulativeTargetX -= steps;
      stepperX.moveTo(cumulativeTargetX);
      break;}
    case 'R': { 
      cumulativeTargetX += steps;
      stepperX.moveTo(cumulativeTargetX);
      break;}
    case 'H':{ 
      homeAxis();
      return;}
    case 'E':{ 
      int firstUnderscore = command.indexOf('_');
      int secondUnderscore = command.indexOf('_', firstUnderscore + 1);
      // Extract x_pos and y_pos from the string
      int x_pos = command.substring(firstUnderscore + 1, secondUnderscore).toInt();
      int y_pos = command.substring(secondUnderscore + 1).toInt();
      errorAxis(x_pos, y_pos);
      return;}
    case 'V': { 
      verboseFunc();
      return;}
    case 'X':{
      verboseMode = false;
    }
  }
}

void verboseFunc(){
  verboseMode = !verboseMode;
  Serial.print("Verbose mode ");
  Serial.println(verboseMode ? "ON" : "OFF");
}

// Call every loop
void checkLimitSwitches() {
  checkSwitch(xMin, stepperX, cumulativeTargetX, "X Min");
  checkSwitch(xMax, stepperX, cumulativeTargetX, "X Max");
  checkSwitch(yMin, stepperY, cumulativeTargetY, "Y Min");
  checkSwitch(yMax, stepperY, cumulativeTargetY, "Y Max");
}

void checkSwitch(LimitSwitch &sw, AccelStepper &stepper, long &cumulativeTarget, const char* name) {
  bool rawState = digitalRead(sw.pin) == LOW; // active LOW
  unsigned long now = millis();

  // If raw reading changed, reset the timer
  if (rawState != sw.lastRawState) {
    sw.lastChangeTime = now;
    sw.lastRawState = rawState;
  }

  // Only update stable state if the reading has been stable for DEBOUNCE_DELAY
  if ((now - sw.lastChangeTime) > DEBOUNCE_DELAY && sw.stableState != rawState) {
    sw.stableState = rawState;

    if (sw.stableState) {
      // Switch pressed
      stepper.stop();
      stepper.setCurrentPosition(0);
      stepper.moveTo(0);
      cumulativeTarget = 0;
      stepper.runToPosition();
      stepper.disableOutputs();
      Serial.print(name);
      Serial.println(" Hit");
    } else {
      // Switch released
      stepper.enableOutputs();
      Serial.print(name);
      Serial.println(" Clear");
    }
  }
}

HomingResult homeAxis() {
  HomingResult result = {0, 0};
  homeSetX = false;
  homeSetY = false;

  // Set speed, acceleration, and step size for homing process
  int homingSpeed = 20000;       // Max speed during homing
  int homingAcceleration = 22000; // Acceleration during homing
  int homingSteps = 1000;         // Steps to move during homing

  // Apply homing settings to both steppers
  stepperX.setMaxSpeed(homingSpeed);
  stepperX.setAcceleration(homingAcceleration);
  stepperY.setMaxSpeed(homingSpeed);
  stepperY.setAcceleration(homingAcceleration);

  Serial.println("Homing started");
  int startX = stepperX.currentPosition(); // Get starting position
  int startY = stepperY.currentPosition(); // Get starting position
  int endX = 0;
  int endY = 0;
  
   // Pre-check for already pressed switches
  if (digitalRead(X_LIMIT_SWITCH_MIN) == LOW) {
    Serial.println("X-axis already on limit switch");
    homeSetX = true;
    stepperX.setCurrentPosition(0);
    cumulativeTargetX = 0;
    endX = 0;
  }

  if (digitalRead(Y_LIMIT_SWITCH_MIN) == LOW) {
    Serial.println("Y-axis already on limit switch");
    homeSetY = true;
    stepperY.setCurrentPosition(0);
    cumulativeTargetY = 0;
    endY = 0;
  }
  
  // Continuously move both axes until their respective limit switches are hit
  while (!homeSetX || !homeSetY) {
    // If the X-axis hasn't reached the limit switch, move it
    if (!homeSetX) {
      cumulativeTargetX -= homingSteps;
      stepperX.moveTo(cumulativeTargetX);
      stepperX.run();
      if (digitalRead(X_LIMIT_SWITCH_MIN) == LOW) {
        delay(1); // Wait 1ms for stability
        if (digitalRead(X_LIMIT_SWITCH_MIN) == LOW) { 
          endX = stepperX.currentPosition(); // Get final position
          stepperX.setCurrentPosition(0);
          cumulativeTargetX = 0;
          Serial.println("X-axis limit switch hit");
          homeSetX = true;
          stepperX.stop();
        }
      }
    }
    // If the Y-axis hasn't reached the limit switch, move it
    if (!homeSetY) {
      cumulativeTargetY -= homingSteps;
      stepperY.moveTo(cumulativeTargetY);
      stepperY.run();
      if (digitalRead(Y_LIMIT_SWITCH_MIN) == LOW) {
        delay(1); // Wait 1ms for stability
        if (digitalRead(Y_LIMIT_SWITCH_MIN) == LOW) { 
          endY = stepperY.currentPosition(); // Get final position
          stepperY.setCurrentPosition(0);
          cumulativeTargetY = 0;
          Serial.println("Y-axis limit switch hit");
          homeSetY = true;
          stepperY.stop();
        }
      }
    }
  }
  result.stepsX += abs(endX - startX); // Count only actual steps taken
  result.stepsY += abs(endY - startY); // Count only actual steps taken
  return result; // Return step counts
}

void errorAxis(int x_pos, int y_pos) {
  HomingResult homeSteps = homeAxis();
  int errorX = abs(homeSteps.stepsX - x_pos);
  int errorY = abs(homeSteps.stepsY - y_pos);

  // Send response 
  Serial.println("ERRORCHECK_RESULT ");
  Serial.print("X Error in Motor Steps: ");
  Serial.println(errorX);
  Serial.print("Y Error in Motor Steps: ");
  Serial.println(errorY);
  Serial.println("Error check complete.");
}