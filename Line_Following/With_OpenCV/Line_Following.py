from picamera2 import Picamera2
from libcamera import controls, Transform 
import cv2
import numpy as np
import time
from RPi_Robot_Hat_Lib import RobotController 

def init():
    """
    Initialize the Motor, Encoder, and camera preview.

    Returns
    -------
    picamera2.Picamera2
        The initialized Picamera2 object.
    """
    global picam2, horizontal, vertical, frame_center, Motor, enc
    # Initialise the Motor
    Motor = RobotController()
    


    # Set PanTilt and servo HAT
    vertical = 1
    horizontal = 2
    Motor.set_servo(vertical, 90)
    Motor.set_servo(horizontal,180 )

    # Set preview configuration (modify resolution as needed)
    picam2 = Picamera2()
    config = picam2.create_preview_configuration(main={"format": 'RGB888', "size": (640, 480)},transform=Transform(vflip=1))
    picam2.configure(config)
    picam2.start()  # Start camera preview
    ## Continous Auto Focus 
    picam2.set_controls({"AfMode": controls.AfModeEnum.Continuous})

    frame_center = (picam2.preview_configuration.main.size[0] // 2 ,
                    picam2.preview_configuration.main.size[1] // 2)


    return picam2

def main():
    """
    main fucntion is to perform object tracking and motor control 
    """
    global picam2, frame_center, Motor

    init()

    while True:
        frame = picam2.capture_array()
        
        
        hsv_frame = cv2.cvtColor(frame, cv2.COLOR_RGB2HSV)
        Black_lower = np.array([0,0,0], dtype = "uint8")
        Black_upper = np.array([179, 255, 118], dtype = "uint8")
        Blacklines = cv2.inRange(frame, Black_lower, Black_upper)
            
                                  
        canny_edges = cv2.Canny(Blacklines, 50, 150)
        
        contours, _  = cv2.findContours(Blacklines, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        if len(contours) > 0 :
            for contour in contours:
                cv2.drawContours(frame, [contour] , 0 , (0,255,0), 2)
                
            
        frame_offset = (0,0)
        if len(contours) > 0:
            largeset = max(contours, key = cv2.contourArea)
            cv2.drawContours(frame, largeset , 0 , (0,0,255), 5)
            
            M = cv2.moments(largeset)
            cx = int(M["m10"] / M["m00"]) if M["m00"] != 0 else 0
            cy = int(M["m01"] / M["m00"]) if M["m00"] != 0 else 0
#             frame_offset = (cx - frame_center[0], cy - frame_center[1])
            cv2.putText(frame, f" Offset: X = {cx}, Y: = {cy}",
                        (10,20), cv2.FONT_HERSHEY_COMPLEX, 0.7, (0,255,255), 2 )
            
            if cx >= 350:
                print("Going Left")
                Motor.move(speed=0, turn=-30)
            
            if cx < 350 and cx > 300:
                print("On track")
                Motor.Forward(40)
            if cx < 300:
                print("Going Right")
                Motor.move(speed =0 , turn=30)

      
            
            cv2.circle(frame, (cx,cy),5,(255,255,0),-1)
        else:
            Motor.Brake()
            print("Nothing Detected")


        cv2.imshow("Black Lines", Blacklines)
        cv2.imshow("Edge Detection", canny_edges)
        cv2.imshow("Main", frame) 
    
        key = cv2.waitKey(1) & 0xFF
        if key == ord('q'):
            break 

        
try:
    if __name__ == '__main__': 
        main()
        
except KeyboardInterrupt:
    Motor.Brake()
    Motor.cleanup()

finally:
    Motor.Brake()
    Motor.cleanup()
    cv2.destroyAllWindows()
    picam2.stop()
    exit()
