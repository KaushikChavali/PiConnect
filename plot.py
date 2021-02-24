#!/usr/bin/env python3
"""
A script to stream real-time acceleration data from the sensor
to the client for tagging.
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
__version__ = "3.0"
__status__ = "Developement"

# Standard library imports.
import pickle
import serial
import socket
import threading
import time

"""
baudRate : integer
	The baud rate of the data channel.
duration : integer
	The duration of the plot in seconds.
samples : integer
	Number of bytes to read in a single blocking call.
sampleSize : integer
	The sample size of the data.
samplingInterval : integer
	The sampling interval to sample captured data.
"""

baudRate = 375000
duration = 30
samples = 1000
sampleSize = 2
samplingInterval = 200

def sendDataToClient(lst, startByte):
    """
    A function to enforce start byte and parse the sensor data from a
    bytearray to a list of samples to be send over the network.
    It samples 5 measurement points fron the list of 500 samples at a
    uniform interval to reduce the load on the network as well as the
    data processing time on the client to ensure a near real-time plot.
    The algorithm optimizes the plot while preserving the statistical
    value of the data.

    Parameters
    ----------
    lst : bytearray
        A bytearray which stores 500 data samples
    startByte : integer
        The start byte of the selected sensor

    Returns
    -------
    sampleList : list
        A list of 500 processed sensor samples

    Attributes
    ----------
    sb : integer
        A counter to store correct start byte in the bytearray
    ctr : integer
        A counter keep track of the start byte in the bytearray
    sampleList : list
        A list which storess 500 processed sensor samples
    """

    if not lst:
        return

    sb, ctr = 0, 0
    # Enforce start byte
    while ctr < 10:
            if lst[ctr] == startByte:
                sb = ctr
                break
            ctr = ctr + 1

    # Sample 5 measurement points from the data with a step size of 200
    sampleList = [
		lst[i:i+sampleSize].hex()
		for i in range(sb, len(lst), samplingInterval)
	]

    return sampleList

def remotePlot(conn, path, sb):
	"""
	A function that handles serial data capture and transfer over the
	network.
	It reads serial data and incrementally sends the client 500 data
	sample blocks for plotting.

	Parameters
	----------
	conn : object
		The socket connection object to send data to the client
	path : string
		The selected sensor path for serial reads
	sb : integer
		The start byte of the selected sensor

	Returns
	-------
	status : string
		A message which indicates the completion of the plot.

	Attributes
	----------
	ctr : integer
		A counter to keep track of samples sent
	t_end : float
		The end time of the capture. The function runs for 30 seconds
		from the user selection.
	byte_data : bytearray
		The bytearray which stores the raw sensor data to be read and
		sent over the network.
	ser : object
		The serial object created for data reads
	lst : list
		A list to store the sample blocks to be serialized and sent
		over the network. Pickle module is used for serialization.
	data : bytes/string
		A single data chunk read from the serial port in bytes
	"""

	ctr = 0
	t_end =  time.time() + duration
	byte_data = bytearray()

	ser = serial.Serial(path, baudRate)

	# Read 30 seconds of data and stream it to the client
	while time.time() < t_end:
		# Incrementally send 500 samples(2B) of data at fixed step size
		data = ser.read(samples)
		byte_data = bytearray.fromhex(data.hex())
		lst = sendDataToClient(byte_data, sb)
		conn.send(pickle.dumps(lst))
		ctr = ctr + 1

	print("Samples sent: ", ctr)

	# Close connections
	ser.close()

	time.sleep(0.5)
	status = "Plot complete."

	return status
