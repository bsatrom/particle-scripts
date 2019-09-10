# Workshop updater script; Credit to David Middlecamp, et al.

import os
import sys
import glob
# import serial
import time
import csv
import argparse
from datetime import datetime
import subprocess

# configuration region:

systemPart1Filename = 'argon-system-part1-1.3.1.bin'
mainApplicationFilename = 'argon-tinker-1.3.1.bin'
bootloaderFilename = 'argon-bootloader-1.3.1.bin'
dfuDeviceID = "2b04:d00c"
systemPart1Address = '0x00030000'
userAppAddress = '0x000D4000'

serialPortPrefix = "/dev/"
isWindows = False

argonNCPUpdate = 'argon-ncp-firmware-0.0.5-ota.bin'


def getBaudCommand(p, baud):
    if isWindows:
        return "MODE " + p + ":baud=" + baud + "\n"
    else:
        return "stty -f " + p + " " + baud + "& "


def log_device_id():
    print('logging device id')
    command = ('particle identify')
    p = subprocess.Popen(command, universal_newlines=True,
                         shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    text = p.stdout.read()
    retcode = p.wait()

    # append text to a file
    f = open("devices.txt", "a+")
    f.write(text)
    f.close()

    return 0


def inspect():
    print('attempting to inspect device modules via serial')

    p = ports()
    if p == None:
        print("No ready serial ports detected... waiting a few seconds and trying again")
        time.sleep(5)

    p = ports()
    if p == None:
        print("No ready serial ports detected... waiting a few seconds and trying again")
        time.sleep(5)

    command = ('particle serial inspect')
    p = subprocess.Popen(command, universal_newlines=True,
                         shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    text = p.stdout.read()
    retcode = p.wait()

    # searchlines = text.splitlines()
    # if flag3==1 and flag2==1 and flag1==1:
    # flag1 = flag2 = flag3 = 0
    #
    # for line in searchlines:
    # 	if "Bootloader module #0 - version 201," in line:
    # 		flag1=1
    #
    # 	if "System module #1 - version 1002,"  in line:
    # 		flag2=1
    #
    # 	if "System module #1 - version 1002,"  in line:
    # 		flag3=1
    #
    #

    flag1 = "Bootloader module #0 - version 401," in text
    flag2 = "System module #1 - version 1321," in text
    flag3 = "UUID: E2F320994F576FE6463F9D6CFD40911B4750E8B071DED794EBC8CD0D2976D157" in text


# Platform: 12 - Argon
# Modules
#   Bootloader module #0 - version 311, main location, 49152 bytes max size
#     Integrity: PASS
#     Address Range: PASS
#     Platform: PASS
#     Dependencies: PASS
#   System module #1 - version 1213, main location, 671744 bytes max size
#     Integrity: PASS
#     Address Range: PASS
#     Platform: PASS
#     Dependencies: PASS
#       Bootloader module #0 - version 311
#   User module #1 - version 6, main location, 131072 bytes max size
#     UUID: CE20033C798A9F83A504B3FC464E7C80317124D7CAD32D68125CAB184014E558
#     Integrity: PASS
#     Address Range: PASS
#     Platform: PASS
#     Dependencies: PASS
#       System module #1 - version 1213
#   NCP module #0 - version 3, main location, 1536000 bytes max size
#     Integrity: PASS
#     Address Range: PASS
#     Platform: PASS
#     Dependencies: PASS

    allTrue = flag1 and flag2 and flag3
    return allTrue


def ports():
    try:
        print('looking for active serial ports')
        command = ('particle serial list')
        p = subprocess.Popen(command, universal_newlines=True,
                             shell=True, stdout=subprocess.PIPE,
                             stderr=subprocess.PIPE)

        # TODO: should this come later? or does this give us a stream or something?
        text = p.stdout.read()
        retcode = p.wait()

        searchlines = text.splitlines()

        for line in searchlines:
            if serialPortPrefix in line:
                # '/dev/tty.usbmodem1411 - Photon'

                if isWindows:
                    # this feels risky to me, split would be safer
                    return line[:5].rstrip(" ")
                else:
                    # I assume this would work for both, but I haven't tested it on windows yet.
                    # TODO: does this work on windows?
                    parts = line.split(' - ')
                    return parts[0]

        return None
    except:
        print("Unexpected error in ports:", sys.exc_info()[0])
        return None


def checkDFUMode():
    # with open(os.path.join(os.getcwd(), 'check_dfu.bat'), 'w') as OPATH:
    # 	OPATH.writelines([
    # 		"dfu-util --list\n"
    # 	])

    command = ('dfu-util --list')
    p = subprocess.Popen(command, universal_newlines=True,
                         shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    text = p.stdout.read()
    retcode = p.wait()

    # command output looks like this:
    # Found Runtime: [05ac:8289] ver=0118, devnum=7, cfg=1, intf=3, alt=0, name="UNKNOWN", serial="UNKNOWN"
    # Found DFU: [2b04:d006] ver=0250, devnum=25, cfg=1, intf=0, alt=1, name="@DCT Flash   /0x00000000/01*016Kg", serial="3a0036000247363333343435"
    # Found DFU: [2b04:d006] ver=0250, devnum=25, cfg=1, intf=0, alt=0, name="@Internal Flash   /0x08000000/03*016Ka,01*016Kg,01*064Kg,07*128Kg", serial="3a0036000247363333343435"

    testString = 'Found DFU: [' + dfuDeviceID + ']'
    return testString in text


#
# ---------------------------------

def requestDFUMode():
    try:
        print('attempting to put device in DFU mode')

        # do we have any ports?
        p = ports()
        if p == None:
            print(
                "No ready serial ports detected... waiting a few seconds and trying again")
            time.sleep(5)

        p = ports()
        if p == None:
            print("No ready serial ports detected... giving up")
            return False

        # with open(os.path.join(os.getcwd(), 'flashsys.bat'), 'w') as OPATH:
        # 	OPATH.writelines([
        # 		"MODE " + p + ":baud=14400\n"
        # 	])

        command = getBaudCommand(p, "14400")
        ret = subprocess.call(command, shell=True)
        if not isWindows:
            if ret is not 0:
                print('failed to call flashsys.bat')
                return False
        else:
            print('unable to check return code on windows')

        time.sleep(2)
        if checkDFUMode():
            return True

        # hmm, otherwise, lets wait a little longer and see
        time.sleep(2)

        # TODO: do we want to try triggering the mode again?
        return checkDFUMode()
    except:
        print("Unexpected error in requestDFUMode:", sys.exc_info()[0])
        return None


#
# ---------------------------------

def requestSETUPMode():
    print('attempting to put device in SETUP mode')

    # do we have any ports?
    p = ports()
    if p == None:
        print("No ready serial ports detected... waiting a few seconds and trying again")
        time.sleep(5)

    p = ports()
    if p == None:
        print("No ready serial ports detected... giving up")
        return False

    # with open(os.path.join(os.getcwd(), 'flashsetup.bat'), 'w') as OPATH:
    # 	OPATH.writelines([
    # 		"MODE " + p + ":baud=28800\n"
    # 	])

    command = getBaudCommand(p, "28800")

    ret = subprocess.call(command, shell=True)
    if ret is not 0:
        print('failed to call flashsetup.bat')
        return False

    time.sleep(2)

    # check to ensure device is in SETUP mode
    isInSetupMode = ports() is not None

    return isInSetupMode


def updateSystemFirmware():
    print('attempting to flash system firmware')

    if checkDFUMode() == False:
        if requestDFUMode() == False:
            print('Failed to put the device into DFU mode... bailing')
            sys.exit(1)

    # subprocess.call('particle flash --usb ' + systemPart1Filename, shell=True)
    subprocess.call('dfu-util -d '+dfuDeviceID+' -a 0 -s ' +
                    systemPart1Address+':leave -D ' + systemPart1Filename, shell=True)
    # subprocess.call('dfu-util -d '+dfuDeviceID+' -a 0 -s 0x8060000:leave -D ' + systemPart2Filename, shell=True)

    # TODO: we should just wait until the serial port becomes available, for some number of retries
    time.sleep(4)


def updateBootloader():
    print('attempting to put device in SETUP mode')
    if requestSETUPMode() == False:
        print('Failed to put the device into SETUP mode... bailing')
        sys.exit(1)

    isInSetupMode = ports() is not None
    if not isInSetupMode:
        print('Failed to put the device into SETUP mode... bailing')
        sys.exit(1)
        return False

    # with open(os.path.join(directory, 'flashboot.bat'), 'w') as OPATH:
    # 	OPATH.writelines([
    #		'particle flash --serial --yes bootloader.bin'
    # 	])

    command = 'particle flash --serial --yes ' + bootloaderFilename
    print('attempting to flash bootloader')
    subprocess.call(command, shell=True)
    time.sleep(5)


def updateMainFirmware():
    print('attempting to flash application firmware')

    if checkDFUMode() == False:
        if requestDFUMode() == False:
            print('Failed to put the device into DFU mode... bailing')
            sys.exit(2)

    subprocess.call('dfu-util -d '+dfuDeviceID+' -a 0 -s ' +
                    userAppAddress+':leave -D ' + mainApplicationFilename, shell=True)
    # subprocess.call('particle flash --usb ' + mainApplicationFilename, shell=True)
    time.sleep(2)


# def updateArgonShit():
# 	print('attempting to flash application firmware')
#
# 	if checkDFUMode() == False:
# 		if requestDFUMode() == False:
# 			print('Failed to put the device into DFU mode... bailing')
# 			sys.exit(2)
#
# 	#dfu-util -d 2b04:d00c -a 0 -s 0x30000:leave -D ncp_passthrough.bin
# 	subprocess.call('dfu-util -d '+dfuDeviceID+' -a 0 -s '+userAppAddress+':leave -D ' + argonNCPUpdate, shell=True)
# 	#subprocess.call('particle flash --usb ' + mainApplicationFilename, shell=True)
# 	time.sleep(2)

def updateArgonShit():
    print('attempting to put device in SETUP mode')
    if requestSETUPMode() == False:
        print('Failed to put the device into SETUP mode... bailing')
        sys.exit(1)

    isInSetupMode = ports() is not None
    if not isInSetupMode:
        print('Failed to put the device into SETUP mode... bailing')
        sys.exit(1)
        return False

    # with open(os.path.join(directory, 'flashboot.bat'), 'w') as OPATH:
    # 	OPATH.writelines([
    #		'particle flash --serial --yes bootloader.bin'
    # 	])

    command = 'particle flash --serial --yes ' + argonNCPUpdate
    print('attempting to flash argon esp32 update')
    subprocess.call(command, shell=True)
    time.sleep(5)


def determineSuccess():
    print('checking if updates were successful')
    result = inspect()

    if result:
        print("PASS")
        return 0
    else:
        print("FAIL")
        return 3


startTime = time.time()

#
# Flash System Firmware
#
updateSystemFirmware()


#
#	Flash Bootloader
#
updateBootloader()


#
#
#
updateArgonShit()


#
#	Flash Main Application
#
updateMainFirmware()


#
#	Check module info to make sure we won't boot in safe mode
#
resultCode = determineSuccess()

log_device_id()


endTime = time.time()
duration = str(endTime - startTime)
print('Device upgrade succeeded after ' + duration + ' seconds')

sys.exit(resultCode)
