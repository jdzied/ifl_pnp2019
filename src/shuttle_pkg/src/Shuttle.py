#!/usr/bin/python

import PiMotor
import RPi.GPIO as GPIO                        #Import GPIO library
import time
from time import sleep
GPIO.setmode(GPIO.BOARD)                       #Set GPIO pin numbering

#Name of Individual MOTORS
m1 = PiMotor.Motor("MOTOR1",1) #Pallet Handling
m2 = PiMotor.Motor("MOTOR2",1) #Carrier Handling

#Switches
GPIO.setup(38,GPIO.IN,pull_up_down=GPIO.PUD_DOWN)
GPIO.setup(40,GPIO.IN,pull_up_down=GPIO.PUD_DOWN)
GPIO.setup(8,GPIO.IN,pull_up_down=GPIO.PUD_DOWN)
GPIO.setup(10,GPIO.IN,pull_up_down=GPIO.PUD_DOWN)

sw1=38 #group 1/4
sw2=40 #idle position
sw3=8 #group 2/5
sw4=10 #group 3/6

#Sensors
GPIO.setup(7,GPIO.IN,pull_up_down=GPIO.PUD_DOWN)
GPIO.setup(12,GPIO.IN,pull_up_down=GPIO.PUD_DOWN)

sick1=7
sick2=12

#time-outs (sec)
timeout_station = 10 #movement between two stations
timeout_pos_search = 10 #search own position
timeout_recieve_pallet = 10
timeout_handout_pallet =10

class Shuttle:

    def __init__(self):
        self.current_pos=0      # 0 -> position unknown ... 1..4 -> position 1-4
        self.error=False

    def getPosition(self):

        if self.error:
            return
        if GPIO.input(sw1):
            self.current_pos=1
        if GPIO.input(sw2):
            self.current_pos=2
        if GPIO.input(sw3):
            self.current_pos=3
        if GPIO.input(sw4):
            self.current_pos=4
        # if position unknown, go back until switch is hit
        if self.current_pos==0:
            m2.reverse(50)
            timeout = time.time() + timeout_pos_search
            while not GPIO.input(sw1) and not GPIO.input(sw2) and not GPIO.input(sw3) and not GPIO.input(sw4):
                sleep(0.005)
                if time.time()>timeout:
                    m2.stop()
                    print("Can't self-locate.")
                    self.error=True
                    return
            m2.stop()
            self.getPosition()

        return

    def goToStation(self,x):
        print("Going to position"+str(x))

        # get position number (0 -> idle)
        switch_pos = {
            1: 1,
            2: 3,
            3: 4,
            4: 1,
            5: 3,
            6: 4,
            0: 2
        }
        goal_pos=switch_pos.get(x,-1)
        if goal_pos==-1:
            return False
        switch_pin = {
            1: sw1,
            2: sw2,
            3: sw3,
            4: sw4
        }
        #get pin number
        pin = switch_pin.get(goal_pos, 0)
        if pin == 0:
            return False

        # get own position
        #self.getPosition()

        # check for error
        if self.error:
            return False

        # go to goal position
        if(goal_pos==self.current_pos):
            return True
        elif(goal_pos<self.current_pos):
            m2.reverse(100)
        elif(goal_pos>self.current_pos):
            m2.forward(100)

        #TODO: Check if the right buttons get pressed on the way

        passages = abs(self.current_pos-goal_pos)
        timeout = time.time() + timeout_station*passages
        while not GPIO.input(pin):
            sleep(0.005)
            if time.time() > timeout: #time limit reached
                m2.stop()
                print("Something went wrong.")
                self.error = True
                return

        m2.stop()
        self.getPosition()
        if self.current_pos==x:
            return True
        else:
            return False

    def recievePallet(self,num):
        if self.error:
            return False
        print("Recieving Pallet")
        # get required direction
        switcher = {
            1: -1,
            2: -1,
            3: -1,
            4: 1,
            5: 1,
            6: 1
            }
        direction = switcher.get(num, 0)

        #start motor
        if direction==1:
            m1.forward(100)
        elif direction==-1:
            m1.reverse(100)
        else:
            return False

        #check the sick sensors (pallet is recieved when both sensors are high)
        timeout = time.time() + timeout_recieve_pallet
        while not GPIO.input(sick1) or not GPIO.input(sick2):
            sleep(0.005)
            if time.time() > timeout: #time limit reached
                m1.stop()
                print("No pallet recieved.")
                self.error = True
                return False
        m1.stop()

        return True

    def handOutPallet(self,num):
        if self.error:
            return False
        print("Handing Out Pallet")
        # get required direction
        switcher = {
            1: 1,
            2: 1,
            3: 1,
            4: -1,
            5: -1,
            6: -1
            }
        direction = switcher.get(num, 0)

        #start motor
        if direction==1:
            m1.forward(100)
        elif direction==-1:
            m1.reverse(100)
        else:
            return False
        sleep(2) #run motor at least 2 sec

        #check the sick sensors (pallet is handed out when both sensors are low)
        timeout = time.time() + timeout_handout_pallet
        while GPIO.input(sick1) or GPIO.input(sick2):
            sleep(0.005)
            if time.time() > timeout: #time limit reached
                m1.stop()
                print("Pallet was not handed out.")
                self.recievePallet(num) # in case the pallet is in between
                self.error = True
                return False
        sleep(2) # run motor for another 2 sec

        if not GPIO.input(sick1) and not GPIO.input(sick2):
            m1.stop()
            return True
        else:
            m1.stop()
            self.recievePallet(num)
            return False

    def reset(self):
        self.error = False
        self.current_pos=0
        if not GPIO.input(sick1) and not GPIO.input(sick2):
            self.getPosition()
            self.goToStation(0)
        else:
            self.error = True
            print("Please remove pallet")
