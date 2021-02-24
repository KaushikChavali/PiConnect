#!/usr/bin/env/python3

"""
The capture script handles the measurement initiation and logging.
"""

__author__ = "Kaushik Chavali"
__licence__ = "GPL"
__version__ = "2.0"
__status__ = "Developement"

# Standard library imports.
import datetime
import itertools
import math
import multiprocessing
import os
import random
import threading
import time

# Local application/library specific imports.
import calibrate
import helper

# Related third party imports.
import serial

"""
    baudRate : integer
        The baud rate of the data channel
	samplingRate : integer
		The sampling rate of the sensor in samples per second
	sampleSize : integer
		The sample size of the data
    sensitivity : float
        The sensitivity of the sensor
    fileBuffer : integer
        The file buffer size for file writes
"""

baudRate = 375000
samplingRate = 15000
sampleSize = 2
sensitivity = 0.08
fileBuffer = 65536

def writeFileToDisk(name, sensData, offset, startByte, start, end):
    """
    A function to process the samples and write it to the disk
    from the memory after the measurement is complete.

    Parameters
    ----------
    name : string
        The user defined sensor name for the file
    sensData : bytearray
        A bytearray which contains raw sensor data.
    offset : float
        The calibrated sensor offset.
    startByte : integer
        The sensor start byte.
    start : object
        The start time of the measurement.
    end : object
        The end time of the measurement.

    Returns
    -------
    None

    Attributes
    ----------
    startDate : string
        The start time of the measurement formated as date.
    startTime : string
        The start time of the measurement formated as time.
    path : string
        The local folder which stores measurement files.
    filename : string
        The filename in the format sensorName_date_time.txt
    offset : float
        The sensor offset.
    startByte : float
        The sensor start byte.
    ctr : integer
        A counter to keep track of start byte.
    sb : integer
        A variable which stores the correct start byte in the
        list.
    """

    # Generate file name with timestamp
    startDate = start.strftime("%d%m%Y")
    startTime = start.strftime("%H%M%S")
    path = "./samples/"
    filename = str(name) + "_" + startDate + "_" + startTime +  ".txt"

    offset = float(offset)
    startByte = int(startByte)

    ctr, sb = 0, 0

    # Detect the correct start of the list
    while ctr < 100:
        if sensData[ctr] == startByte:
            sb = ctr
            break
        ctr = ctr + 1

    #open file for writes
    with open(path + filename, "w", buffering=fileBuffer) as f:
        # Add a header
        f.write("start time, end time\n") # Add label
        f.write(
            start.strftime('%H:%M:%S.%f') + ", "
            + end.strftime('%H:%M:%S.%f') + "\n") # Add timestamp
        f.write(
            "raw data in hex" + ", "
            + "acceleration in dec" + ", "
            + "acceleration in g" + "\n") # Add label

        # Loop over the bytearray, process the data and write it
        # to a file.
        # Iterate over length of bytearray with 2B interval(sampleSize)
        for i in range(sb, len(sensData), sampleSize):
            # Access two bytes, i.e. sample size
            sd = sensData[i:i+sampleSize]
            # Convert it in hex
            acc_raw_hex = sd.hex()
            # Convert hex to dec
            acc_raw_dec = int(acc_raw_hex, 16)
            # Adjust for sensitivity
            acc_g_dec = acc_raw_dec * sensitivity
            # Perform offset correction (rounded to 2 decimal places)
            acc_in_g = acc_g_dec - offset
            # Record the sample in a line
            data = (str(acc_raw_hex)
                + ",%.2f" % round(acc_g_dec, 2)
                + ",%.2f" % round(acc_in_g, 2)
                + "\n")
            # Append line to file
            f.write(data)
            # Add delay between writes to reduce CPU usage
            time.sleep(0.000001)

def handleSerialComm(ser, name, offset, startByte, duration):
    """
    A function to handle serial communication. It calls the serial
    library's read function with a pre-computed sample size from the
    duration of the measurement. The serial reads are blocking reads.
    After the capture, the data is processed and written to a file.

    Parameters
    ----------
    ser : object
        A serial object for data reads
    name : string
        The user defined name
    offset : float
        The sensor offset
    startByte : integer
        The start byte
    duration : integer
        The interval of measurement

    Returns
    -------
    None

    Attributes
    ----------
    samples : integer
		The number of samples to be captured in bytes.
    byteData : bytearray
        A bytearray to store the raw sensor data in memory.
        The data structure is chosen since it has the least memory
        footprint to store bytes in Python when compared to a python
        list. It enables longer measurement sessions.
    t_s : object
        The start time of the measurement timestamped to the file.
    t_e : object
        The end time of the measurement timestamped to the file.
    acc_raw : bytes
        The raw acceleration data in bytes returned from the library.
    acc_raw_hex : string
        The raw acceleration value in bytes converted to a hex string.
		The step is required to correctly store the first nibble in the
        bytearray when it is 0.
    """

    byteData = bytearray()
    samples = int(duration) * samplingRate * sampleSize

    # Generate start timestamp for the data file
    t_s = datetime.datetime.now()
    # Start recording data samples
    acc_raw = ser.read(samples)
    # Generate end timestamp for the data file
    t_e = datetime.datetime.now()

    # Initial post-processing
    acc_raw_hex = acc_raw.hex()
    byteData += bytearray.fromhex(acc_raw_hex)

    print("Recorded samples: ", int(len(byteData)/sampleSize))

    # Write the captured data to a file
    print("Writing file to disk")
    writeFileToDisk(name, byteData, offset, startByte, t_s, t_e)
    print("File write complete")

	# Clean up
    ser.close()

def multiProc(z):
    """
    Performance optimization
    A function to add multiprocessing support.

    Parameters
    ----------
    z : list
        A list of iterables which contain measurement parameters

    Returns
    -------
    None
    """

    # Creates a new process for each sensor
    with multiprocessing.Pool() as pool:
        pool.starmap(handleSerialComm, z)

def startCapture(paths, names, offsets, startBytes, interval):
    """
    A function to start the measurement called from server script

    Parameters
    ----------
    paths : list
        A list of user selected sensor paths
    names : list
        A list of user defined sensor names
    offsets : list
        A list of calibrated sensor offsets
    startBytes : list
        A list of calibrated start bytes
    interval : string
        The duration of measurement

    Returns
    -------
    status : string
        The status of the measurement sent to the client

    Attributes
    ----------
    ports : list
        A list of serial objects for measurement
    ser : object
        A serial object generated using sensor path
    z : list
        A list of iterables which contain measurement parameters
    status : string
        The status of the measurement sent to the client
    """

    ports = []

    for path in paths:
        ser = serial.Serial(path, baudRate, timeout=None)
        ports.append(ser)

	# Call a function to map each serial object to a new process
    z = list(zip(ports, names, offsets, startBytes, interval))
    multiProc(z)

	# Return measurement status
    status = "Measurement complete."

    return status
