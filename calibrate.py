#!/usr/bin/env python3

"""
The calibration script to perform offset correction and start-byte
detection on the sensors.
"""

#    PiConnect - Intelligent Wireless Sensor Measurement Platform
#    Copyright (C) 2021  Kaushik Chavali
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <https://www.gnu.org/licenses/>.

__author__ = "Kaushik Chavali"
__licence__ = "GPL"
__version__ = "2.0"
__status__ = "Developement"

# Standard library imports.
from collections import Counter
import statistics
import time

# Related third party imports.
import serial
import numpy as np

"""
Attributes

sensitivity : float
	The sensitivity of the sensor
"""

sensitivity = 0.08

class Calibrate:
	"""
	Helper class to parse calibration results
	"""

	def __init__(self, path, name, offset, startByte):
		"""
		Parameters
		----------
		path : string
			The sensor path
		name : string
			The user defined sensor name
		offset : float
			The calibrated offset
		startByte : integer
			The calibrated start byte
		"""

		self.path = path
		self.name = name
		self.offset = offset
		self.startByte = startByte

def processData(sensData, startByte):
	"""
	A function to enforce the start byte and do post processing on the
	captured sensor samples.

	Parameters
	----------
	sensData : bytearray
		A bytearray that contains the raw samples read from the serial port.
	start_byte : integer
		The start byte of the sensor generated after calibration.

	Returns
	-------
	measurement : list
		A list which contains processed samples.

	Attributes
	----------
	measurement : list
		A list to store measurement values
	ctr : integer
		A counter to keep track of start of the bytearray
	sb : integer
		The position of the start byte in the captured list
	sd : bytes
		A single raw acceleration sample of size 2B
	acc_raw_hex : string
		The acceleration value in hex stored as string
	acc_raw_dec : integer
		The acceleration value in decimal, i.e., base 10
	acc_g_dec : float
		The acceleration value after sensitivity adjustment
	"""

	ctr, sb = 0, 0
	measurement = []

	# Detect the correct start of the list
	while True:
		if sensData[ctr] == int(startByte):
			sb = ctr
			break
		ctr = ctr + 1

	# Iterate over bytearray and do post-processing
	for i in range(sb, len(sensData), 2):
		sd = sensData[i:i+2]
		acc_raw_hex = sd.hex()
		acc_raw_dec = int(acc_raw_hex, 16)
		acc_g_dec = acc_raw_dec * sensitivity
		measurement.append(acc_g_dec)

	return measurement

def computeOffset(ser, startByte):
	"""
	A function to compute the sensor offsets. It captures 1000 samples
	from the sensor and stores it in a list. Then it uses the calibrated
	start byte to process the data and append it to the measurement list.
	The computed offset is the median of the samples stored in the list.

	Parameters
	----------
	ser : object
		The serial object passed to the function for serial reads.
	start_byte : integer
		The start byte of the samples

	Returns
	-------
	offset : float
		The computed offset corrected to 2 decimal places.

	Attributes
	----------
	byte_data : bytearray
		A bytearray to store the raw samples read from the serial port.
	samples : integer
		The number of samples to capture in bytes.
	acc_raw : bytes
		The bytes read from the port
	acc_raw_hex : string
		The raw acceleration values in bytes converted to a hex string.
		It is required because the first nibble is often 0 and not correctly
		stored in the bytearray without proper pre-processing.
	measurement : list
		A list which contains processed samples.
	offset : float
		The computed offset is the median of values stored in the measurement
		list.
	"""

	samples = 2000
	byte_data = bytearray()

	# Capture a 1000 samples for processing
	acc_raw = ser.read(samples)
	acc_raw_hex = acc_raw.hex()
	byte_data += bytearray.fromhex(acc_raw_hex)

	# Process the captured data
	measurement = processData(byte_data, startByte)

	# Compute the median in the list
	offset = statistics.median(measurement)

	return offset

def sbDetect(ser):
	"""
	The function implements the start byte detection algorithm.
	It captures a short stream of data and stores it in a list.
	The start byte is determined as the list element, i.e., the
	byte with most common occurance.

	Parameters
	----------
	ser : object
		The serial object passed to the function for serial reads.

	Returns
	-------
	start_byte : integer
		The start byte of the samples

	Attributes
	----------
	measurement : list
		A list to store measurement values
	end_t : float
		The stop time of the capture in seconds
	acc_raw : bytes
		The raw acceleration values
	occurances : dict
		A dictionary containing the bytes as key
		and its count as value
	start_byte : integer
		Stores the most common byte as integer
	"""

	measurement = []
	end_t = time.time() + 0.125

	while time.time() < end_t:
		# Read 1B of raw sensor data
		acc_raw = ser.read(1)
		measurement.append(acc_raw)

	occurances = Counter(measurement)
	start_byte = occurances.most_common(1)[0][0]
	start_byte = int(start_byte.hex(), 16)

	return start_byte

def performOffsetCorrection(lst):
	"""
	A function to perform offset correction on the selected
	sensors

	Parameters
	----------
	lst : list
		The user selected list of sensors sent by the client

	Returns
	-------
	result : list
		A list of objects with calibrated values

	Attributes
	----------
	name : string
		The user defined name of the sensors
	path : string
		The user selected sensor path
	ser : object
		The serial object created for the sensor
	startByte : integer
		The start byte generated after calibration
	offset : float
		The offset value generated after calibration
	result : list
		The list of Calibrate objects to be returned
		to the client
	"""

	result = []

	print("Calibration in progress")

	for i in range(len(lst)):
		path = lst[i]["path"]
		name = lst[i]["name"]
		# Create a serial object
		ser = serial.Serial(path, 375000)
		# Call the start-byte detection function
		startByte = sbDetect(ser)
		# Call the offset correction function
		offset = computeOffset(ser, startByte)
		# Store the result as a list of objects
		result.append(Calibrate(path, name, offset, startByte))

	return result
