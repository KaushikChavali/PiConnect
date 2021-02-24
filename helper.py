#!/usr/bin/env/python3

"""
The helper script handles serialization of data to be sent
over the network
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
import itertools
import json

# Related third party imports.
import serial
import serial.tools.list_ports as lp

class Devices:
    """
    Helper class to parse connected sensor list and
    create a python object
    """

    def __init__(self, id, path, name, serial):
        """
        Parameters
        ----------
        id : interger
            The port number of the sensor
        path : string
            The device path of the sensor
        name : string
            The device name of the sensor
        serial : string
            The device serial of the sensor
        """

        self.id = id
        self.path = path
        self.name = name
        self.serial = serial

def recv(ser, size):
	"""
	A function which performs non-blocking PySerial reads.
	Parameters
	----------
	ser : object
		The serial object created for each sensor
	size : integer
		The sample size in bytes
	Returns
	-------
	value : bytes
		The bytes read from the port
	"""

	value = ser.read(max(1, min(size, ser.in_waiting)))

	return value

def getConnectedSensors():
    """
    A function to parse connected sensors as a list and
    return to main function

    Parameters
    ----------
    None

    Returns
    -------
    sListJson : list
        The sensor parameters as a list of JSON objects

    Attributes
    ----------
    sList : list
        The sensor parameters as a list of python objects
    sListJson : list
        The sensor parameters as a list of JSON objects
    """

    sList = []

	#iterate over device list and parse the data
    for p in ports:
        # Get serial number of the dev board. Set a
        # placeholder for direct connection.
        serialNo = p.serial_number
        if serialNo == None:
            serialNo = "-"

        sList.append(
            Devices(
                p[2][-1],   # Device ID
                p[0],   # Device path
                p[1],   # Device name
                serialNo # Device serial
            )
        )

    sListJson = json.dumps([obj.__dict__ for obj in sList])
    return sListJson

def getSelectedSensors(devlst):
    """
    A function to parse only requisite user selected sensor parameters
    for measurement and return to main function

    Parameters
    ----------
    devlst : list
        The user selected list of sensors parameters

    Returns
    -------
    paths : list
        A list of device paths of type string for measurement
    names : list
        A list of user-defined sensor names as strings
    offsets : list
        A list of calibrated offsets for measurement
    startBytes : list
        A list of calibrated start bytes
    duration : integer
        The duration of measurement

    Attributes
    ----------
    paths : list
        A list of device paths of type string for measurement
    names : list
        A list of user-defined sensor names as strings
    offsets : list
        A list of calibrated offsets for measurement
    startBytes : list
        A list of calibrated start bytes
    duration : integer
        A list of duration values in seconds
    """

    (paths, names, offsets,
    startBytes, duration) = ([] for i in range(5))

	#parse user selected sensor  paths
    for idx in range(len(devlst)):
        paths.append(devlst[idx]["path"])
        names.append(devlst[idx]["name"])
        offsets.append(devlst[idx]["offset"])
        startBytes.append(devlst[idx]["startByte"])
        duration.append(devlst[idx]["duration"])

    return paths, names, offsets, startBytes, duration

def main():
    """
    The main function initializes the list of connected sensors

    Attributes
    ----------
    ports : list
        A list of connected sensors as serial object parsed with the
        help of serial tools
    """

    global ports

    deviceList = list(lp.grep("/dev/tty[A-Za-z]*", True))
    deviceList.sort()

    # Append only those ports that can be opened and read.
    ports = []
    for dev in deviceList:
        try:
            path = dev[0]
            s = serial.Serial(path, 375000)

            ctr = 0
            byte_data = bytearray()
            while ctr < 10:
                byte_data += recv(s, 2)
                ctr = ctr + 1

            if len(byte_data) > 0:
                ports.append(dev)
        except Exception as e:
            pass

if __name__ == "__main__":
    main()
