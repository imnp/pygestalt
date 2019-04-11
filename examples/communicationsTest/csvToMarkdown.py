"""Converts Communications Test Results into a Markdown Table

April 9th, 2019
Ilan E. Moyer
"""

import csv

arduinoFile = open("commTestResults_arduinoNode.csv", 'rb')
gestaltFile = open("commTestResults_networkedGestalt.csv", 'rb')
arduinoReader = csv.reader(arduinoFile)
gestaltReader = csv.reader(gestaltFile)

arduinoData = [dataRow for dataRow in arduinoReader]
gestaltData = [dataRow for dataRow in gestaltReader]

payloadSize = [int(row[0]) for row in arduinoData[1:]] #payload sizes
arduinoRate = [int(round(float(row[2]))) for row in arduinoData[1:]] #arduino packet rates
gestaltRate = [int(round(float(row[2]))) for row in gestaltData[1:]] #gestalt packet rates

combinedData = zip(payloadSize, arduinoRate, gestaltRate)

print "|Payload (Bytes) |Arduino Uno |Networked Gestalt|"
print "|----------------|------------|-----------------|"
for size, arduino, gestalt in combinedData:
    print "|"+str(size) + "              |" + str(arduino) + "          |" + str(gestalt)+ "               |"
    print "|----------------|------------|-----------------|"