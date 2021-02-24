#!/usr/bin/env python3

"""
The server script handles client connections and serves client requests
"""

__author__ = "Kaushik Chavali"
__licence__ = "GPL"
__version__ = "2.0"
__status__ = "Developement"

# Standard library imports.
import json
import os
import socket
import sys
import threading

# Local application/library specific imports.
import calibrate
import capture
import helper
import plot

"""
Attributes
----------
HOST : string
    The hostname or ip address of the server
PORT : integer
    The port on which the server is hosted
socksize : interger
    The receive buffer size of the opened socket
sock : socket object
    The socket object for network communication
"""

HOST = '0.0.0.0'
PORT = 50001
socksize = 1024

# Create a network socket
sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
# Bind it to the host and port
sock.bind((HOST, PORT))

print('Server running on port: %s' % PORT) # Status message

def clientHandler(conn):
    """Handles client requests

    Parameters
    ----------
    conn : object
        The connection object created after client connection

    Returns
    -------
    None
    """

    # Start listening to client requests
    while True:
        cmd = conn.recv(socksize) # Recieve client commands

        # Break the loop if no client requests are recieved
        if not cmd:
            break

        # List connected sensors
        elif cmd == b'lstsens':
            print(cmd) # Log client request
            # Call the helper module to get the connected sensor list
            # and send it over network
            helper.main()
            conn.sendall(helper.getConnectedSensors().encode())

        # Calibrate: perform offset correction
        elif cmd == b'calsens':
            print(cmd) # Log client request
            # Receive user selected list of sensor boards
            list = conn.recv(socksize)
            # Decode byte string to json object
            devices = list.decode()
            # Convert json object to python object
            deviceList = json.loads(devices)
            # Call calibrate module to compute offsets
            result = calibrate.performOffsetCorrection(deviceList)
            # Serialize the result
            deviceOffset = json.dumps([obj.__dict__ for obj in result])
            # Send the result to the client
            conn.sendall(deviceOffset.encode())

        # Plot graph
        elif cmd == b'pltsens':
            print(cmd) # Log client request
            # Receive user selected list of sensor boards
            list = conn.recv(socksize)
            # Decode byte string to json object
            devices = list.decode()
            # Convert json object to python object
            deviceList = json.loads(devices)
            # Parse the device path
            path = deviceList[0]["path"]
            sb = deviceList[0]["startByte"]
            # Call plot module to initiate real-time plot at the client
            status = plot.remotePlot(conn, path, sb)
            # Send the status of the plot to the client
            conn.sendall(status.encode())

        # Start measurement
        elif cmd == b'stmsrmt':
            print(cmd) # Log client request
			# Receive user selected list of sensor boards and duration
            # of the measurement
            list = conn.recv(socksize)
            # Decode byte string to json object
            devices = list.decode()
            # Convert json object to python object
            deviceList = json.loads(devices)
            # Call the helper modules to parse measurement parameters
            (path, name, offset, startByte,
            duration) = helper.getSelectedSensors(deviceList)
            # Call the capture module to start the measurement
            status = capture.startCapture(
                path, name, offset,
                startByte, duration
            )
            # Send the status of measurement back to the client
            conn.sendall(status.encode())

        # Start synchronization
        elif cmd == b'stsync':
            print(cmd) # Log client request
            # Get application path
            app_path = os.path.dirname(os.path.realpath(__file__))
            # Send path to client
            conn.sendall(app_path.encode())

        # Kill/close client connection
        elif cmd == b'killsrv':
            print(cmd) # Log client request
            # Close connection
            conn.close()
            # Log status
            sys.stdout.write("Terminated\n")
            sys.exit()

        # Print client requests
        else:
            print(cmd) # Log client request

def main():
    """
    Offers multi-threading support for the server to handle
    multiple client connections on the same socket

    Parameters
    ----------
    None

    Returns
    -------
    None
    """

    try:
        # Keep on listening for client connections
    	while True:
        	# Listen for client connections
    		sock.listen()
    		print('Listening...') # Log status
    		# Accept client connection
    		conn, addr = sock.accept()
    		print('Connected by', addr) # Log status
    		# Create a new thread for each client connection
    		threading.Thread(target=clientHandler, args=(conn, )).start()
    except KeyboardInterrupt:
    	print("\nCtlr+C pressed. Server shutting down.") # Log status
    	# Clean up connections
    	sock.shutdown(socket.SHUT_RDWR)
    	sock.close()
    	sys.exit(0)

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        pass
