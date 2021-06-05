# SIT210 Final Project
# 
# An embedded system to check for car spaces at the front of your house.
# This is the Python code for the components that are at your house, checking for car spaces.

import serial
import time
import requests

# Constants
# your particle access token
ACCESS_TOKEN = "your access token goes here"
# your particle device id
WHISPERING_GIANT = "your device id goes here"
# the particle url
PARTICLE_BASE_URL = "https://api.particle.io/v1/devices/"
# the particle function or variable as a url string
PARTICLE_URL_MIDDLE_LOOKING = "/home"
PARTICLE_URL_PARKING_STATUS = "/parkingStatus"
# constructing the full urls
LOOKING_URL = PARTICLE_BASE_URL + WHISPERING_GIANT + PARTICLE_URL_MIDDLE_LOOKING
PARKING_STATUS_URL = PARTICLE_BASE_URL + WHISPERING_GIANT + PARTICLE_URL_PARKING_STATUS
# distance from device to car stopped in traffic (ie. car space available, with traffic)
TRAFFIC_DISTANCE = 600
# distance from device to traffic on other side of the road (ie. car space available and no traffic on our side)
NOTHING_DISTANCE = 800
# if the mobile component is in zone, how often (in seconds) should we perform the car space check
RECHECK_TIME = 5
# whether the mobile component is in zone or not, how often (in seconds) should we check if the car is in zone,
# and if there are any spots
LOOP_TIME = 20

# serial port used for the lidar
ser = serial.Serial('/dev/ttyS0', 115200)

# checks the car space
# firstCall is a bool indicating whether the function has been recursively called yet.
# most errors are handled by recalling the function after half a second
# if that doesn't clear the error, the function returns and will be called again in due time
def checkSpace(firstCall):
    # open the serial port for the lidar if it is not already open
    if (ser.is_open == False):
        ser.open()
        while (ser.is_open == False):
            time.sleep(0.1)

    # see how many bits are waiting in the buffer
    count = ser.in_waiting
    # 9 bits is a full read
    while (count < 9):
        ser.reset_input_buffer()
        count = ser.in_waiting
    
    # get the info from the buffer and clear it
    liDarData = ser.read(9)
    ser.reset_input_buffer()

    # checks the frame header to make sure we've got good data
    if liDarData[0] == 0x59 and liDarData[1] == 0x59:
        # distance in cm
        distance = liDarData[2] + liDarData[3] * 256
        ser.reset_input_buffer()

        return distance
    elif (firstCall):
        time.sleep(0.5)
        checkSpace(False)

# main function for the program that will loop
def main():
    while (True):
        # request the variable home from the mobile component. True is in zone looking for a park, false is out
        # of zone
        response = requests.get(LOOKING_URL, params = {'access_token': ACCESS_TOKEN})
        # check response before continuing
        if (response):
            # extract the variable from the reponse
            responseData = response.json()
            if ('result' in responseData):
                inZone = responseData['result']
            else:
                inZone = False

            # loop while the mobile component is in zone
            while (inZone):
                # check the distance from the device to the nearest object
                carDistance = checkSpace(True)
                # switch on the result
                if (carDistance > NOTHING_DISTANCE):
                    # send space available
                    requests.post(PARKING_STATUS_URL, data = {'arg': 'NOTHING', 'access_token': ACCESS_TOKEN})
                elif (carDistance > TRAFFIC_DISTANCE):
                    # send space available, but with traffic 
                    requests.post(PARKING_STATUS_URL, data = {'arg': 'TRAFFIC', 'access_token': ACCESS_TOKEN})
                else: 
                    # send no space available
                    requests.post(PARKING_STATUS_URL, data = {'arg': 'NO_PARK', 'access_token': ACCESS_TOKEN})
                
                # delay before looping. In testing it was found that if you make too many requests to particle
                # it becomes unhappy.
                time.sleep(RECHECK_TIME)

                # update the inZone status
                response = requests.get(LOOKING_URL, params = {'access_token': ACCESS_TOKEN})
                while (response == False): 
                    time.sleep(5)
                    response = requests.get(LOOKING_URL, params = {'access_token': ACCESS_TOKEN})
                responseData = response.json()
                if ('result' in responseData):
                    inZone = responseData['result']
        
        # we probably don't need to continually check, so small delay here for machine empathy
        time.sleep(LOOP_TIME)

# main entry point
if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        if ser != None:
            ser.close()
