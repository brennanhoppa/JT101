#include <AccelStepper.h>

#define X_STEP_PIN 2
#define X_DIR_PIN 3
#define X_ENABLE_PIN 4
#define Y_STEP_PIN 5
#define Y_DIR_PIN 06
#define Y_ENABLE_PIN 7
#define X_LIMIT_SWITCH_PIN A1  // Limit switch for X-axis
#define Y_LIMIT_SWITCH_PIN A0  // Limit switch for Y-axis

#define MOTOR_INTERFACE_TYPE 1

AccelStepper stepperX(MOTOR_INTERFACE_TYPE, X_STEP_PIN, X_DIR_PIN);
AccelStepper stepperY(MOTOR_INTERFACE_TYPE, Y_STEP_PIN, Y_DIR_PIN);

// Variables to track cumulative positions
long cumulativeTargetX = 0;
long cumulativeTargetY = 0;

int motorSpeed = 15000; // 5000 for microscope, 15000 for camera
int motorAcceleration = 22000; // 2000 for microscope, 22000 for camera

bool homeSetX = false;
bool homeSetY = false;

struct HomingResult {
    int stepsX;
    int stepsY;
};

void setup() {
  Serial.begin(500000);
  
  pinMode(X_ENABLE_PIN, OUTPUT);
  pinMode(Y_ENABLE_PIN, OUTPUT);
  pinMode(X_LIMIT_SWITCH_PIN, INPUT_PULLUP);  // Set limit switch pins as input with pull-up resistor
  pinMode(Y_LIMIT_SWITCH_PIN, INPUT_PULLUP);
  
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
  stepperX.run();
  stepperY.run();
}

void processCommand(String command) {
  char direction = command[0];
  int steps = command.substring(1).toInt();

  switch(direction) {
    case 'U': 
      cumulativeTargetY += steps;
      stepperY.moveTo(cumulativeTargetY);
      break;
    case 'D': 
      cumulativeTargetY -= steps;
      stepperY.moveTo(cumulativeTargetY);
      break;
    case 'L': 
      cumulativeTargetX -= steps;
      stepperX.moveTo(cumulativeTargetX);
      break;
    case 'R': 
      cumulativeTargetX += steps;
      stepperX.moveTo(cumulativeTargetX);
      break;
    case 'H':
      homeAxis();
      return;
    case 'E':
      int firstUnderscore = command.indexOf('_');
      int secondUnderscore = command.indexOf('_', firstUnderscore + 1);
      // Extract x_pos and y_pos from the string
      int x_pos = command.substring(firstUnderscore + 1, secondUnderscore).toInt();
      int y_pos = command.substring(secondUnderscore + 1).toInt();
      errorAxis(x_pos, y_pos);
      return;
  }
}

HomingResult homeAxis() {
  HomingResult result = {0, 0};
  homeSetX = false;
  homeSetY = false;

  // Set speed, acceleration, and step size for homing process
  int homingSpeed = 40000;       // Max speed during homing
  int homingAcceleration = 22000; // Acceleration during homing
  int homingSteps = 2000;         // Steps to move during homing

  // Apply homing settings to both steppers
  stepperX.setMaxSpeed(homingSpeed);
  stepperX.setAcceleration(homingAcceleration);
  stepperY.setMaxSpeed(homingSpeed);
  stepperY.setAcceleration(homingAcceleration);

  Serial.println("Homing mode started");
  int startX = stepperX.currentPosition(); // Get starting position
  int startY = stepperY.currentPosition(); // Get starting position
  // Continuously move both axes until their respective limit switches are hit
  while (!homeSetX || !homeSetY) {
    // If the X-axis hasn't reached the limit switch, move it
    if (!homeSetX) {
      cumulativeTargetX -= homingSteps;
      stepperX.moveTo(cumulativeTargetX);
      stepperX.run();
      if (digitalRead(X_LIMIT_SWITCH_PIN) == LOW) {
        delay(1); // Wait 1ms for stability
        if (digitalRead(X_LIMIT_SWITCH_PIN) == LOW) { 
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
      if (digitalRead(Y_LIMIT_SWITCH_PIN) == LOW) {
        delay(1); // Wait 1ms for stability
        if (digitalRead(Y_LIMIT_SWITCH_PIN) == LOW) { 
          stepperY.setCurrentPosition(0);
          cumulativeTargetY = 0;
          Serial.println("Y-axis limit switch hit");
          homeSetY = true;
          stepperY.stop();
        }
      }
    }
  }
  int endX = stepperX.currentPosition(); // Get final position
  result.stepsX += abs(endX - startX); // Count only actual steps taken
  int endY = stepperY.currentPosition(); // Get final position
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