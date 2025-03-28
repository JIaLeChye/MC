import cv2
import mediapipe as mp
from picamera2 import Picamera2
from libcamera import controls
from libcamera import Transform
from RPi_Robot_Hat_Lib import RobotController

  

def init(): 
        """
        Initialize motor controller, encoder, mediapipe hands and camera 
        """
        global mp_hands, hands, cap, mp_drawing, Motor, enc
        Motor = RobotController()
        # Initialize MediaPipe Hands
        mp_hands = mp.solutions.hands
        hands = mp_hands.Hands(static_image_mode=False, max_num_hands=1,
                                min_detection_confidence=0.5, min_tracking_confidence=0.5)
        mp_drawing = mp.solutions.drawing_utils

        # Start video capture
        cap = Picamera2(0)
        cap.configure(cap.create_preview_configuration( main={"format": 'XRGB8888', "size": (640, 480)},transform=Transform(vflip=1)))  # Flip both horizontally and vertically
        cap.start()
        cap.set_controls({"AfMode": controls.AfModeEnum.Continuous})
        vertical = 2
        horizontal = 1
        Motor.set_servo(vertical, 40)
        Motor.set_servo(horizontal, 92)

   
    
        
        
# Define function to control the robot car
def control_car(hand_landmarks):
        global mp_hands, hands, cap, mp_drawing, Motor
        # Extract the position of landmark 9
        landmark_9 = hand_landmarks.landmark[9]
            
        # Get normalized coordinates of landmark 9
        landmark_9_x = landmark_9.x
        landmark_9_y = landmark_9.y
            
        # Calculate direction and distance based on landmark 9 position
        # Example: Determine if landmark 9 is to the left, right, or center
        motorFreq = 30 # set the speed of the motor to 20 
        if landmark_9_x < 0.3:
                direction = "right"
                
        elif landmark_9_x > 0.7:
                direction = "left"

        else:
                direction = "center"
            
        # Example: Determine if landmark 9 is closer or farther away
        if landmark_9_y < 0.4:
                distance = "close"
        elif landmark_9_y > 0.6:
                distance = "far"
        else:
                distance = "medium"
            
        # Map direction and distance to control commands for the car
        # Example: Adjust speed and steering based on direction and distance
        
        if direction == "left":
                print("Turn left")
                Motor.move(speed= 0 , turn=-30)
        elif direction == "right":
                print("Turn right")
                Motor.move(speed=0, turn=30)
        else:
                # Move the car forward or stop based on distance
                if distance == "close":
                        print("Stop")
                        Motor.Brake()
                else:
                        print("Move forward")
                        Motor.Forward(motorFreq)


def main():
        init()
        global mp_hands, hands, cap, mp_drawing, Motor, enc 
        # Main loop for robot car control
        while True:
                # Read frame from video capture
                frame = cap.capture_array()

                # Convert the BGR frame to RGB 
                frame_bgr = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
                # Detect hand landmarks using MediaPipe Hands
                results = hands.process(frame_bgr)
                # enc.encoder()

                # Draw hand landmarks on the frame
                if results.multi_hand_landmarks:
                        for hand_landmarks in results.multi_hand_landmarks:
                            # Draw landmarks on the frame
                            mp_drawing.draw_landmarks(frame_bgr, hand_landmarks, mp_hands.HAND_CONNECTIONS)
                            
                            # Control the car based on hand landmarks
                            control_car(hand_landmarks)
                            frame = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
                else:
                        Motor.Brake()

                # Display the frame with hand landmarks
                cv2.imshow('Hand Gesture Control', frame)

                    # Exit loop on 'q' key press
                if cv2.waitKey(1) & 0xFF == ord('q'):
                        break
try:
        if __name__ == '__main__':
                main()
except KeyboardInterrupt:
        cv2.destroyAllWindows()
        Motor.cleanup()
        # enc.stop()


