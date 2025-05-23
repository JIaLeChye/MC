import smbus
import time
import board 
import busio 
import adafruit_ssd1306 
from PIL import Image, ImageDraw, ImageFont
import math
import RPi.GPIO as GPIO
from PIL import ImageDraw

class RobotController:
    
    def __init__(self, wheel_diameter=97, OLED_addr=0x3c, debug=False,):  # diameter in mm
        # Setup I2C communication
        self.address = 0x09
        self.bus = smbus.SMBus(1)

        self.OLED_addr = OLED_addr 
        self.i2c = busio.I2C(board.SCL, board.SDA) 
        self.disp = adafruit_ssd1306.SSD1306_I2C(128, 64, self.i2c, addr=self.OLED_addr)
        self.disp.fill(0) 
        self.image = Image.new("1", (self.disp.width, self.disp.height)) 
        self.draw = ImageDraw.Draw(self.image)
        self.font = ImageFont.load_default()

        self.debug = debug 
        self.rpm_init = False 
        
        # Robot physical parameters
        self.WHEEL_DIAMETER = wheel_diameter / 1000.0  # Convert to meters
        self.WHEEL_CIRCUMFERENCE = math.pi * self.WHEEL_DIAMETER
        self.GEAR_RATIO = 30
        self.ENCODER_PPR = 13
        self.TICKS_PER_REV = self.ENCODER_PPR * self.GEAR_RATIO
        self.calibration_factor = 1.0
        
        # Register addresses
        self.REG_MOTOR_RF = 1
        self.REG_MOTOR_RB = 2
        self.REG_MOTOR_LF = 3
        self.REG_MOTOR_LB = 4
        self.REG_ENCODER_RF_LOW = 5
        self.REG_ENCODER_RF_HIGH = 6
        self.REG_ENCODER_RB_LOW = 7
        self.REG_ENCODER_RB_HIGH = 8
        self.REG_ENCODER_LF_LOW = 9
        self.REG_ENCODER_LF_HIGH = 10
        self.REG_ENCODER_LB_LOW = 11
        self.REG_ENCODER_LB_HIGH = 12
        self.REG_SERVO_1 = 13
        self.REG_SERVO_2 = 14
        self.REG_LINE_SENSOR = 15
        self.REG_LINE_ANALOG = 16
        self.REG_VOLTAGE = 17
        self.REG_ENCODER_RESET = 18
        self.REG_SYSTEM_RESET = 19
        self.lib_ver= "1.0.0"

    def __version__(self):
        print(f"RPi_Robot_Hat_Lib Version: {self.lib_ver}")


    ##-- Communication section----##
    def _read_byte(self, reg):
        """Read a byte from an I2C register"""
        try:
            value = self.bus.read_byte_data(self.address, reg)
            return value
        except Exception as e:
            print(f"Error reading from register {reg}: {e}")
            return 0

    def _write_byte(self, reg, value):
        """Write a byte to an I2C register"""
        try:
            self.bus.write_byte_data(self.address, reg, value)
        except Exception as e:
            print(f"Error writing to register {reg}: {e}")

    def reset_encoders(self):
        """Reset all encoder counts to zero"""
        try:
            self._write_byte(self.REG_ENCODER_RESET, 0xA5)
            time.sleep(0.1)  # Give the coprocessor time to process the reset
            return True
        except Exception as e:
            print(f"Error resetting encoders: {e}")
            return False
        
    def reset_system(self):
        """
        Perform a complete reset of the RP2040 coprocessor.
        This will restart all systems and reset all registers to default values.
        """
        try:
            print("Initiating system reset...")
            self._write_byte(self.REG_SYSTEM_RESET, 0xA5)
            time.sleep(1)  # Give time for the reset to complete
            print("System reset complete. Re-initializing connection...")
            # Re-initialize I2C bus after reset
            self.bus = smbus.SMBus(1)
            return True
        except Exception as e:
            print(f"Error during system reset: {e}")
            return False
        
    ####################################



    ##---------Movement Section-------##
    def Forward(self, speed):
        """Move forward with specified speed (0-100)"""
        self.move(speed)  # Positive speed for forward

    def Backward(self, speed):
        """Move backward with specified speed (0-100)"""
        self.move(-speed)  # Negative speed for backward

    def move(self, speed=0, turn=0):
        """
        Basic movement control
        speed: -100 to 100 (negative for backward, positive for forward)
        turn: -100 to 100 (negative for right, positive for left)
        """
        left_speed = speed + turn
        right_speed = speed - turn
        
        left_speed = max(-100, min(100, left_speed))
        right_speed = max(-100, min(100, right_speed))
        
        # Convert to byte values (0-127 for forward, 128-255 for backward)
        self.set_motor('LF', left_speed)
        self.set_motor('LB', left_speed)
        self.set_motor('RF', right_speed)
        self.set_motor('RB', right_speed)

    def Brake(self):
        """Stop all motors"""
        self.stop()

    def Horizontal_Left(self, speed):
        """Move Horizontal Left with specified spedd (0 - 100)"""
        self.set_motor('LF', -abs(speed))
        self.set_motor('RF', abs(speed))
        self.set_motor('LB', abs(speed))
        self.set_motor('RB', -abs(speed))
    

    def Horizontal_Right(self, speed):
        """Move Horizontal Right with specified spedd (0 - 100)"""
        self.set_motor('LF', abs(speed))
        self.set_motor('RF', -abs(speed))
        self.set_motor('LB', -abs(speed))
        self.set_motor('RB', abs(speed))
    

    def set_motor(self, motor, speed):
       """Set motor speed (-100 to 100)"""
       motor_registers = {
           'RF': self.REG_MOTOR_RF,
           'RB': self.REG_MOTOR_RB,
           'LF': self.REG_MOTOR_LF,
           'LB': self.REG_MOTOR_LB
       }
       
       speed = max(-100, min(100, speed))
       if speed >= 0:
           byte_value = int(speed * 127 / 100)
       else:
           byte_value = 256 + int(speed * 127 / 100)
           
       try:
           self._write_byte(motor_registers[motor], byte_value)
       except Exception as e:
           print(f"Error setting motor speed: {e}")
           self.stop() # Stop all Motor
    ############################################


    ##-----Motor Encoder Section------##
    
    def get_encoder(self, motor, debug=False):
        """Get encoder count for a specific motor"""
        encoder_registers = {
            'RF': (self.REG_ENCODER_RF_LOW, self.REG_ENCODER_RF_HIGH),
            'RB': (self.REG_ENCODER_RB_LOW, self.REG_ENCODER_RB_HIGH),
            'LF': (self.REG_ENCODER_LF_LOW, self.REG_ENCODER_LF_HIGH),
            'LB': (self.REG_ENCODER_LB_LOW, self.REG_ENCODER_LB_HIGH)
        }
        
        try:
            reg_low, reg_high = encoder_registers[motor]
            low = self._read_byte(reg_low)
            high = self._read_byte(reg_high)
            value = (high << 8) | low
            if debug == True or self.debug ==True:
                print("##################\n DEBUG STATEMENT FOR get_encoder() \n##################")
                print(f"Encoder value for {motor}: {value}")
                print(f"Encoder low: {low}")
                print (f"Encoder high: {high}")
                print(f"Encoder reg_low: {reg_low}")
                print(f"Encoder reg_high: {reg_high}")
                print("##################\n DEBUG STATEMENT FOR get_encoder() \n##################")
            return value if value < 32768 else value - 65536
        except Exception as e:
            print(f"Error reading encoder: {e}")
            return 0
    
    def get_rpm(self,motor, debug=False):
        
        if self.rpm_init is False:
            self._previous_data = {
                'RF': {'ticks':self.get_encoder('RF'), 'time':time.time()},
                'RB': {'ticks':self.get_encoder('RB'), 'time':time.time()},
                'LF': {'ticks':self.get_encoder('LF'), 'time':time.time()},
                'LB': {'ticks':self.get_encoder('LB'), 'time':time.time()}
            }
            self.rpm_init = True

        try: 
            current_ticks = self.get_encoder(motor) 
            current_time = time.time() 

            prev_ticks = self._previous_data[motor]['ticks']
            prev_time = self._previous_data[motor]['time'] 


            delta_time = current_time - prev_time 
            delta_ticks = current_ticks - prev_ticks

            if debug ==True or self.debug == True:
                print("##############################")
                print("DEBUG STATEMENT FOR get_rpm()")
                print("##############################")
                print(f"Encoder value for {motor}: {current_ticks}")
                print(f"Previous encoder value for {motor}: {prev_ticks}")
                print(f"Delta ticks: {delta_ticks}") 
                print(f"Delta time: {delta_time}")
                # print(f"Previous data: {self._previous_data}")
                for key, value in self._previous_data.items():
                    motor_data = value
                    print(f"  {key}: Ticks = {motor_data['ticks']}, Time = {motor_data['time']:.6f}")
                print("#############################")
                

            if delta_time == 0: 
                if self.debug == True:
                    print(f"Warning: Delta time is zero for {motor}")
                return 0 
            if delta_ticks == 0 :
                if self.debug == True: 
                    print(f"Warning: Delta ticks is zero for {motor}")
                return 0
            
            else: 
                self._previous_data = {
                'RF': {'ticks':self.get_encoder('RF'), 'time':time.time()},
                'RB': {'ticks':self.get_encoder('RB'), 'time':time.time()},
                'LF': {'ticks':self.get_encoder('LF'), 'time':time.time()},
                'LB': {'ticks':self.get_encoder('LB'), 'time':time.time()}
            }
                rpm = (delta_ticks / self.TICKS_PER_REV) / delta_time * 60 
                if motor == 'RF' or motor == 'RB':
                    return rpm  
                if motor =='LF' or motor == 'LB':
                    return -rpm
        
            
        except Exception as e :
            print(f"Error calculating RPM for {motor}: {e}")
            return None

    def get_distance(self, motor, debug=False):
        """Calculate calibrated distance traveled by a specific motor in meters"""
        try:
            ticks = self.get_encoder(motor)
            
            # Check for unreasonable encoder values
            if abs(ticks) > 10000:  # Limit for reasonable encoder values
                if debug == True or self.debug == True:
                    print(f"Warning: Unusual encoder value for {motor}: {ticks}")
                
            revolutions = ticks / self.TICKS_PER_REV
            distance = revolutions * self.WHEEL_CIRCUMFERENCE * self.calibration_factor
            return abs(distance)  # Return absolute distance
        except Exception as e:
            print(f"Error calculating distance for {motor}: {e}")
            return 0
        
    def move_distance(self, distance, speed=0):
        """Move the robot a specific distance in meters with error checking"""
        print(f"\nMoving {distance:.2f} meters at speed {speed}")
        
        # Determine direction
        direction = 1 if distance >= 0 else -1
        speed *= direction
        target_distance = abs(distance)
        
        # Get initial distances
        start_dist_left = self.get_distance('LF')
        start_dist_right = self.get_distance('RF')
        
        # Start moving
        self.move(speed=speed)
        
        # Variables for movement monitoring
        last_valid_left = 0
        last_valid_right = 0
        consecutive_errors = 0
        
        while True:
            try:
                # Get current distances
                current_dist_left = self.get_distance('LF') - start_dist_left
                current_dist_right = self.get_distance('RF') - start_dist_right
                
                # Validate readings
                if abs(current_dist_left - last_valid_left) > 0.1:  # Sudden jump > 10cm
                    current_dist_left = last_valid_left
                    consecutive_errors += 1
                else:
                    last_valid_left = current_dist_left
                    consecutive_errors = 0
                    
                if abs(current_dist_right - last_valid_right) > 0.1:  # Sudden jump > 10cm
                    current_dist_right = last_valid_right
                    consecutive_errors += 1
                else:
                    last_valid_right = current_dist_right
                    consecutive_errors = 0
                
                # Safety check
                if consecutive_errors > 5:
                    print("Too many consecutive errors. Stopping for safety.")
                    self.stop()
                    break
                
                # Calculate average distance traveled
                avg_distance = abs(current_dist_left + current_dist_right) / 2
                
                # Print progress
                print(f"Distance traveled: {avg_distance*100:.1f}cm target: {target_distance*100:.1f}cm")
                print(f"Left: {abs(current_dist_left)*100:.1f}cm Right: {abs(current_dist_right)*100:.1f}cm")
                
                # Check if we've reached the target
                if avg_distance >= target_distance:
                    self.stop()
                    break
                
                time.sleep(0.1)
                
            except Exception as e:
                print(f"Error during movement: {e}")
                consecutive_errors += 1
                if consecutive_errors > 5:
                    print("Too many errors. Stopping for safety.")
                    self.stop()
                    break
                    
        print("Movement completed.")
    #################################################

    

    ##--------Servo Movement section--------## 
    def set_servo(self, servo_num, angle):
        """
        Set servo position (0-180 degrees)
        servo_num: 1 or 2
        angle: 0-180
        """
        if servo_num not in [1, 2]:
            print("Servo number must be 1 or 2")
            return
            
        # Clamp angle to valid range
        angle = max(0, min(180, angle))
        
        # Select the correct register
        reg = self.REG_SERVO_1 if servo_num == 1 else self.REG_SERVO_2
        
        try:
            self._write_byte(reg, angle)
        except Exception as e:
            print(f"Error setting servo angle: {e}")


    ##########################################



    ##----Line Following sensor section-----##
    def read_line_sensors(self):
        """Read the digital line sensors (5 bits)"""
        try:
            return self._read_byte(self.REG_LINE_SENSOR)
        except Exception as e:
            print(f"Error reading line sensors: {e}")
            return 0

    def read_line_analog(self):
        """Read the analog line sensor value"""
        try:
            return self._read_byte(self.REG_LINE_ANALOG)
        except Exception as e:
            print(f"Error reading analog line sensor: {e}")
            return 0
        
    ##########################################



    ##------------Battery Section-----------## 
    def get_battery(self):
        """Read battery voltage"""
        try:
            value = self._read_byte(self.REG_VOLTAGE)
            return value / 10.0  # Convert to actual voltage
        except Exception as e:
            print(f"Error reading voltage: {e}")
            return 0
    
    #############################################



    ##-------Encoder Calibration Section-------## 
    def calibrate_distance(self):
        """Run calibration procedure"""
        print("\nDistance Calibration Tool")
        print("The robot will move forward for 5 seconds.")
        print("Please measure the actual distance traveled.")
        
        input("Press Enter to start calibration...")
        
        # Reset encoders by reading them
        self.get_distance('LF')
        self.get_distance('RF')
        
        # Move forward for 5 seconds
        print("\nMoving forward...")
        self.Forward(50)
        time.sleep(5)
        self.stop()
        
        # Get reported distances
        left_dist = self.get_distance('LF')
        right_dist = self.get_distance('RF')
        avg_dist = (left_dist + right_dist) / 2
        
        print(f"\nReported distances:")
        print(f"Left wheel: {left_dist*100:.1f}cm")
        print(f"Right wheel: {right_dist*100:.1f}cm")
        print(f"Average: {avg_dist*100:.1f}cm")
        
        actual = float(input("\nPlease enter the actual distance traveled in cm: "))
        actual = actual / 100.0  # Convert to meters
        
        if avg_dist != 0:
            self.calibration_factor = actual / avg_dist
            print(f"\nNew calibration factor: {self.calibration_factor:.3f}")
    ##########################################



    ##-------Buzzer and Sound Section-------##        
    def play_tone(self, frequency, duration):
        """
        Play a tone on the buzzer
        frequency: in Hz
        duration: in seconds
        """
        try:
            if not hasattr(self, 'buzzer_pwm'):
                # Initialize buzzer if not already done
                GPIO.setmode(GPIO.BCM)
                GPIO.setup(12, GPIO.OUT)  # Using GPIO 12 for buzzer
                self.buzzer_pwm = GPIO.PWM(12, 440)  # Start with 440Hz
                self.buzzer_pwm.start(0)
            
            if frequency > 0:
                self.buzzer_pwm.ChangeFrequency(frequency)
                self.buzzer_pwm.ChangeDutyCycle(50)
                time.sleep(duration)
                self.buzzer_pwm.ChangeDutyCycle(0)
                time.sleep(0.1)
                # GPIO.cleanup(12)  # Cleanup buzzer GPIO
            else:
                time.sleep(duration)
            
                
        except Exception as e:
            print(f"Error playing tone: {e}")

    #############################################


    ##--------Clean Up anb Stop Section--------##
    def stop(self):
        """Stop all motors"""
        for motor in ['RF', 'RB', 'LF', 'LB']:
            self.set_motor(motor, 0)

    def cleanup(self):
        """Clean up resources"""
        self.stop()
        # Center servos
        self.set_servo(1, 90)
        self.set_servo(2, 90)
        # Cleanup buzzer
        if hasattr(self, 'buzzer_pwm'):
            self.buzzer_pwm.stop()
            GPIO.cleanup(12)  # Cleanup buzzer GPIO

    def disp_fwd_enc(self):
        """Read the Forward encoder data (Left and Right) and display it on the OLED Screen"""
        self.disp.fill(0)
        self.disp.show()

        LF_distance =  abs(self.get_distance('LF')) 
        RF_distance = abs(self.get_distance('RF') )
        LF_RPM = abs(self.get_rpm('LF'))
        RF_RPM = abs(self.get_rpm('RF'))

        image = Image.new("1",(self.disp.width, self.disp.height))
        draw = ImageDraw.Draw(image)

        # Display motor 1 data at the top of the screen
        draw.text((0, 0), f"Motor: LF", font=self.font, fill=255)
        draw.text((0, 10), f"Dist: {LF_distance:.2f} cm", font=self.font, fill=255)
        draw.text((0, 20), f"RPM: {LF_RPM:.2f}", font=self.font, fill=255)

        draw.line((0, 33, 128, 33), width=2, fill=255)  # Draw a horizontal line

        # Display motor 2 data at the bottom of the screen
        draw.text((0, 35), f"Motor: RF", font=self.font, fill=255)
        draw.text((0, 45), f"Dist: {RF_distance:.2f} cm", font=self.font, fill=255)
        draw.text((0, 55), f"RPM: {RF_RPM:.2f}", font=self.font, fill=255)

        self.disp.image(image) 
        self.disp.show()

    
    def disp_bwd_enc(self):
        """Read the Forward encoder data (Left and Right) and display it on the OLED Screen"""
        self.disp.fill(0)
        self.disp.show()

        LB_distance =  abs(self.get_distance('LB')) 
        RB_distance = abs(self.get_distance('RB') )

        LB_RPM = abs(self.get_rpm('LB'))
        RB_RPM = abs(self.get_rpm('RB'))

        image = Image.new("1",(self.disp.width, self.disp.height))
        draw = ImageDraw.Draw(image)

        # Display motor 1 data at the top of the screen
        draw.text((0, 0), f"Motor: LB", font=self.font, fill=255)
        draw.text((0, 10), f"Dist: {LB_distance:.2f} cm", font=self.font, fill=255)
        draw.text((0, 20), f"RPM: {LB_RPM:.2f}", font=self.font, fill=255)

        draw.line((0, 33, 128, 33), width=2, fill=255)  # Draw a horizontal line

        # Display motor 2 data at the bottom of the screen
        draw.text((0, 35), f"Motor: RB", font=self.font, fill=255)
        draw.text((0, 45), f"Dist: {RB_distance:.2f} cm", font=self.font, fill=255)
        draw.text((0, 55), f"RPM: {RB_RPM:.2f}", font=self.font, fill=255)

        self.disp.image(image) 
        self.disp.show()


    def clear_disp(self):
        self.disp.fill(0)
        self.disp.show()


def test():
    """Simple test function"""
    robot = RobotController(wheel_diameter=97)
    robot.calibration_factor = -0.162
    
    try:
        # Test battery voltage
        voltage = robot.get_battery()
        print(f"Battery Voltage: {voltage:.1f}V")
        
        # Test servos
        print("\nCentering servos...")
        robot.set_servo(1, 90)
        robot.set_servo(2, 90)
        time.sleep(1)
        
        # Test movement
        print("\nMoving forward...")
        robot.Forward(50)
        time.sleep(2)
        robot.stop()
        
        # Test line sensors
        print("\nReading line sensors...")
        digital = robot.read_line_sensors()
        analog = robot.read_line_analog()
        print(f"Digital sensors: {bin(digital)[2:]:>05}")
        print(f"Analog value: {analog}")

        # Test buzzer
        print("\nPlaying a tone...")
        robot.play_tone(1000, 1) 
        
    except KeyboardInterrupt:
        print("\nTest interrupted by user")
    finally:
        robot.cleanup()
        print("\nTest completed")

if __name__ == "__main__":
    test()