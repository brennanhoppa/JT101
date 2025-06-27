#include <AccelStepper.h>

#define X_STEP_PIN 2
#define X_DIR_PIN 3
#define X_ENABLE_PIN 4
#define Y_STEP_PIN 5
#define Y_DIR_PIN 6
#define Y_ENABLE_PIN 7
#define X_LIMIT_SWITCH_MIN A1  // Limit switch for X-axis
#define Y_LIMIT_SWITCH_MIN A0  // Limit switch for Y-axis
#define X_LIMIT_SWITCH_MAX A3
#define Y_LIMIT_SWITCH_MAX A2

#define MOTOR_INTERFACE_TYPE AccelStepper::DRIVER

AccelStepper stepperX(MOTOR_INTERFACE_TYPE, X_STEP_PIN, X_DIR_PIN);
AccelStepper stepperY(MOTOR_INTERFACE_TYPE, Y_STEP_PIN, Y_DIR_PIN);

// Variables to track cumulative positions
long cumulativeTargetX = 0;
long cumulativeTargetY = 0;

int motorSpeed = 15000; // 5000 for microscope, 15000 for camera
int motorAcceleration = 22000; // 2000 for microscope, 22000 for camera

bool homeSetX = false;
bool homeSetY = false;

bool xMinHit = false;
bool xMaxHit = false;
bool yMinHit = false;
bool yMaxHit = false;

bool verboseMode = false;

struct HomingResult {
    int stepsX;
    int stepsY;
};

void setup() {
  Serial.begin(500000);
  
  pinMode(X_ENABLE_PIN, OUTPUT);
  pinMode(Y_ENABLE_PIN, OUTPUT);
  pinMode(X_LIMIT_SWITCH_MIN, INPUT_PULLUP);  // Set limit switch pins as input with pull-up resistor
  pinMode(Y_LIMIT_SWITCH_MIN, INPUT_PULLUP);
  pinMode(Y_LIMIT_SWITCH_MAX, INPUT_PULLUP);
  pinMode(X_LIMIT_SWITCH_MAX, INPUT_PULLUP);

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


void checkLimitSwitches() {
  const unsigned long debounceDelay = 50;
  unsigned long now = millis();

  // Persistent debounce and state variables
  static bool stableXMin = false, stableXMax = false, stableYMin = false, stableYMax = false;
  static unsigned long xMinLastChange = 0, xMaxLastChange = 0, yMinLastChange = 0, yMaxLastChange = 0;

  static bool wasXMinHit = false, wasXMaxHit = false, wasYMinHit = false, wasYMaxHit = false;
  static bool wasXMinVerbose = false, wasXMaxVerbose = false, wasYMinVerbose = false, wasYMaxVerbose = false;

  // Read raw pin states (active LOW)
  bool rawXMin = digitalRead(X_LIMIT_SWITCH_MIN) == LOW;
  bool rawXMax = digitalRead(X_LIMIT_SWITCH_MAX) == LOW;
  bool rawYMin = digitalRead(Y_LIMIT_SWITCH_MIN) == LOW;
  bool rawYMax = digitalRead(Y_LIMIT_SWITCH_MAX) == LOW;

  // Debounce logic
  if (rawXMin != stableXMin && (now - xMinLastChange > debounceDelay)) {
    stableXMin = rawXMin;
    xMinLastChange = now;
  }
  if (rawXMax != stableXMax && (now - xMaxLastChange > debounceDelay)) {
    stableXMax = rawXMax;
    xMaxLastChange = now;
  }
  if (rawYMin != stableYMin && (now - yMinLastChange > debounceDelay)) {
    stableYMin = rawYMin;
    yMinLastChange = now;
  }
  if (rawYMax != stableYMax && (now - yMaxLastChange > debounceDelay)) {
    stableYMax = rawYMax;
    yMaxLastChange = now;
  }

  // Assign debounced values to globals
  xMinHit = stableXMin;
  xMaxHit = stableXMax;
  yMinHit = stableYMin;
  yMaxHit = stableYMax;

  // Get current and target positions
  long curX = stepperX.currentPosition();
  long tarX = stepperX.targetPosition();
  long curY = stepperY.currentPosition();
  long tarY = stepperY.targetPosition();

  // Handle all 4 switches using helper
  handleLimitSwitch(xMinHit, wasXMinHit, wasXMinVerbose, curX, tarX, tarX < curX, "X Min", stepperX, cumulativeTargetX);
  handleLimitSwitch(xMaxHit, wasXMaxHit, wasXMaxVerbose, curX, tarX, tarX > curX, "X Max", stepperX, cumulativeTargetX);
  handleLimitSwitch(yMinHit, wasYMinHit, wasYMinVerbose, curY, tarY, tarY < curY, "Y Min", stepperY, cumulativeTargetY);
  handleLimitSwitch(yMaxHit, wasYMaxHit, wasYMaxVerbose, curY, tarY, tarY > curY, "Y Max", stepperY, cumulativeTargetY);
}


void handleLimitSwitch(bool hit, bool &wasHit, bool &wasVerbose, long cur, long tar, bool goingTowardSwitch, const char* name, AccelStepper& stepper, long &cumulativeTarget) {
  if (hit) {
    if (!wasHit && goingTowardSwitch) {
      stepper.stop();
      stepper.setCurrentPosition(0);       // Reset current position
      stepper.moveTo(0);                   // Match target to stop movement
      cumulativeTarget = 0;                // Reset tracking variable
      stepper.runToPosition(); 

      stepper.disableOutputs();
      Serial.print(name); Serial.println(" Hit");
      wasHit = true;
    }
    if (verboseMode && hit != wasVerbose) {
      Serial.print(name); Serial.println(" Switch: PRESSED");
      wasVerbose = hit;
    }
  } else {
    if (wasHit) {
      Serial.print(name); Serial.println(" Clear");
      stepper.enableOutputs();
      wasHit = false;
    }
    if (verboseMode && hit != wasVerbose) {
      Serial.print(name); Serial.println(" Switch: RELEASED");
      wasVerbose = hit;
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

  Serial.println("Homing mode started");
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

  Serial.println("Homing complete for both axes");
  Serial.println("Homing complete");
  return result; // Return step counts
}

void errorAxis(int x_pos, int y_pos) {
  Serial.println("error mode started");
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