#!/usr/bin/env python3

"""
The client script implements the GUI and associated functionality.
"""

__author__ = "Kaushik Chavali"
__licence__ = "GPL"
__version__ = "2.0"
__status__ = "Developement"

# Standard library imports.
from datetime import datetime
import itertools
import json
import pickle
import socket
import subprocess
import threading
import time
import tkinter as tk
from tkinter import filedialog

# Related third party imports.
import matplotlib
matplotlib.use("TkAgg") # Use Tk backend
from matplotlib.backends.backend_tkagg import (
    FigureCanvasTkAgg, NavigationToolbar2Tk
)
# Implement the default Matplotlib key bindings.
from matplotlib.backend_bases import key_press_handler
from matplotlib.figure import Figure
import matplotlib.pyplot as plt
import matplotlib.animation as animation
import numpy as np
# Library to handle file transfers
import paramiko
from scp import SCPClient

class Sensor:
    """
    Helper class to parse the user selection.
    """

    def __init__(self, path, name, offset, startByte, duration):
        """
        Parameters
        ----------
        path : string
            The device path of the sensor.
        name : string
            The user defined name for the sensor.
        offset : string
            The offset generate after sensor calibration.
        startByte : string
            The start byte detected for each sensor.
        duration : string
            The user defined duration of the measurement.
        """

        self.path = path
        self.name = name
        self.offset = offset
        self.startByte = startByte
        self.duration = duration

class ScrollableFrame(tk.Frame):
    """
    Helper class to enable scrollbar inside the sensor list frame.
    Inherits the tkinter Frame class.
    """

    def __init__(self, container, *args, **kwargs):
        """
        Parameters
        ----------
        container : object
            The parent frame.
        *args : list
            A variable number of positional arguments.
        **kwargs : list
            A variable number of keyword arguments.

        Attributes
        ----------
        canvas : object
            A tkinter canvas to place the sensor list.
        scrollbar : object
            A scrollbar attached to the canvas.
        """

        super().__init__(container, *args, **kwargs)

        canvas = tk.Canvas(self)
        # Initialize the scrollbar object and bind it to the canvas
        scrollbar = tk.Scrollbar(
            self,
            orient='vertical',
            command=canvas.yview
        )
        self.scrollable_frame = tk.Frame(canvas)
        # Configure the scrollabe frame
        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(
                scrollregion=canvas.bbox("all"),
                highlightcolor="white",
                height=75,
                width=600
            )
        )
        # Place the scrollable frame as a window object inside the
        # canvas
        canvas.create_window(
            (0, 0),
            window=self.scrollable_frame,
            anchor='nw'
        )
        # Attach the scrollbar to the canvas
        canvas.configure(yscrollcommand=scrollbar.set)
        # Place the canvas and scrollbar using grid geomertry manager
        canvas.grid(row=0, column=0, sticky='nsew')
        scrollbar.grid(row=0, column=1, sticky='nsew', padx=(40,0))

class ListSensorBoards(tk.Frame):
    """
    Helper class to dynamically populate the connected sensor list.
    On the press of the Update Sensor button, the client requests the
    list of sensors from the Pi and the returned response is parsed
    in a tabular format as one frame per sensor.
    """

    def __init__(self, master, id, path, ser, off, **options):
        """
        The header is generated for the table in the below format,
        Header : Checkbox, ID, Path, Serial Number, Name, Offset.

        Parameters
        ----------
        master : object
            The parent frame in which the list is populated.
        id : integer
            The client side id generated for each sensor in the list.
        path : string
            The device path parsed from the server response.
        ser : string
            The serial number of the connected sensor board,
            parsed from the server.
        off : string
            The sensor offset returned from the server after.
            calibration
        **options : list
            A list of options specified for the frame.

        Attributes
        ----------
        state : object
            Keeps tracks of the state of the checkbox.
        cb_sel : object
            A checkbox widget to keep track of user selection.
        lbl_id, lbl_path, lbl_ser : object
            A tkinter Label widget to display seonsor id, serial,
            and path.
        ent_name : object
            A tkinter Entry widget for the user to tag sensors.
        lbl_cal : object
            A tkinter Label widget to display the offset values.
        """

        tk.Frame.__init__(self, master, **options)

        # Define a single row with the following widgets
        self.state = tk.IntVar()
        self.cb_sel = tk.Checkbutton(self, variable=self.state,
                                     anchor="e")
        self.lbl_id = tk.Label(self, text=id, width=5)
        self.lbl_path = tk.Label(self, text=path, width=15)
        self.lbl_ser = tk.Label(self, text=ser, width=15)
        self.ent_name = tk.Entry(self, width=15)
        self.lbl_cal = tk.Label(self, text=off, width=15)

        # Add widgets to the frame using grid geomertry manager
        self.cb_sel.grid(row=0, column=0)
        self.lbl_id.grid(row=0, column=1)
        self.lbl_path.grid(row=0, column=2)
        self.lbl_ser.grid(row=0, column=3)
        self.ent_name.grid(row=0, column=4)
        self.lbl_cal.grid(row=0, column=5)

def createSSHClient(server, port, user, password):
    """
    A helper function to create a ssh client using paramiko library.

    Parameters
    ----------
    server : string
        The ip address of the raspberry pi.
    port : integer
        The ftp port to be used.
    user : string
    password : string
        The credentials for the raspberry pi.

    Returns
    -------
    client : object
        The ssh client object to initiate secure copy(scp).

    Attributes
    ----------
    client : object
        The ssh client object configured with server parameters.
    """

    client = paramiko.SSHClient()

    client.load_system_host_keys()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(server, port, user, password)

    return client

def timestampOp():
    """
    A function to generate a timestamp to be displayed with
    each log message.

    Parameters
    ----------
    None

    Returns
    -------
    timestamp : strings
        A timestamp formatted as string.

    Attributes
    ----------
    t : string
        It stores the current time as string.
    timestamp : string
        Formatted time to be displayed as log message.
    """

    t = datetime.now().strftime("%H:%M:%S")
    timestamp = "\n " + t + " : "

    return timestamp

def connectPi():
    """
    A function to create a socket connection to the server.

    Attributes
    ----------

    sock : object
        A global socket object used to send and receive client
        messages. It is initialized with the local socket object
        on client connection for access from other functions.
    s : object
        A local socket object to establish client connection.
    ipAddr : string
        The address of the connected peer socket, i.e., the server.
    """

    global host, sock

    # Attempt manual connection in case of user input.
    manualAddr = ent_ipaddr.get()
    if manualAddr:
        host = manualAddr
    else:
        host = 'raspberrypi.local'

    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(1)
        s.connect((host, port))
        s.settimeout(None)
        ipAddr = s.getpeername()[0]
        ent_status.delete(0, tk.END)
        ent_status.insert(0, "Connected")
        ent_ipaddr.delete(0, tk.END)
        ent_ipaddr.insert(0, ipAddr)
        ent_ipaddr['fg'] = "black"
        btn_conn['state'] = tk.DISABLED
        btn_disc['state'] = tk.NORMAL
        can_status.itemconfig(led, fill="green", outline="green")
        txt_log.insert(tk.END,
                       timestampOp()
                       + "Raspberry Pi connected at IP "
                       + ipAddr)
        txt_log.see("end")
        sock = s
    except Exception as e:
        txt_log.insert(tk.END,
                       timestampOp()
                       + str(e)
                       + ". Please check your connection.")
        txt_log.see("end") # Set view to the last message

def disconnectPi():
    """
    A function to disconnect the client from the server
    and close the socket connection.
    """

    try:
        # Send a connection kill command to the server
        sock.sendall(str.encode('killsrv'))
        sock.shutdown(socket.SHUT_RDWR)
        sock.close()
        ent_status.delete(0, tk.END)
        ent_status.insert(0, "Disconnected")
        ent_ipaddr['fg'] = "grey"
        can_status.itemconfig(led, fill="red", outline="red")
        txt_log.insert(tk.END,
                       timestampOp()
                       + "Raspberry Pi disconnected")

    except:
        txt_log.insert(tk.END,
                       timestampOp()
                       + "No device connected")
    finally:
        txt_log.see("end") # Set view to the last message
        btn_conn['state'] = tk.NORMAL
        cleanup()

def getSensorList():
    """
    A function to get the list of connected sensors from the server.

    Attributes
    ----------
    sensorList : lists
        A global variable to store the list of connected sensors parsed
        from the server.
    sensorCount : integer
        The number of sensors connected to the Raspberry Pi.
    line : bytestring
        The sensor list received from the socket.
    devices : object
        A JSON object which stores the decoded bytestring.
    dev_lst : object
        A python object parsed from the json object.
    """

    global sensorList, sensorCount

    try:
        # Send  a list sensor command to the server
        # and parse the results
        sock.sendall(str.encode('lstsens'))
        line = sock.recv(socksize)
        txt_log.insert(tk.END,
                       timestampOp()
                       + "Sensor List: ")
        devices = line.decode()
        dev_lst = json.loads(devices)
        sensorCount = len(dev_lst)
        # Check if sensors are connected
        if len(dev_lst) == 0:
            cleanup()
            txt_log.insert(tk.END,
                           timestampOp()
                           + "No sensors connected.")
        else:
            # Call function to print the list of connected sensors
            printDevList(dev_lst)
        sensorList = dev_lst
    except Exception as e:
        txt_log.insert(tk.END, timestampOp() + str(e))
    finally:
        txt_log.see("end")

def printDevList(devList):
    """
    A function to populate device description and display it in as
    a row in the table.

    Parameters
    ----------
    devList : list
        A python object that contains sensor description.

    Returns
    -------
    None

    Attributes
    ----------
    deviceList : string
        The sensor description packed for display in the log window.
    """

    cleanup()

    for idx, dev in enumerate(devList):
        deviceList = (
            str(idx+1) + " "
            + dev["path"] + " "
            + dev["name"] + dev["serial"]
        )
        states.append(0)
        ids.append(idx+1)
        paths.append(dev["path"])
        serials.append(dev["serial"])
        names.append("") # Default value
        offsets.append(0) # Default value
        startBytes.append(0) # Default value
        txt_log.insert(tk.END, timestampOp() + deviceList)
        txt_log.see("end")

    # Populate sensor list
    for id in range(len(ids)):
        ListSensorBoards(
            fr_sens.scrollable_frame,
            ids[id],
            paths[id],
            serials[id],
            '{:.2f}'.format(offsets[id])
        ).grid(
            row=id,
            column=0,
            sticky='nsew'
        )

def parseSelection():
    """
    A helper function to parse user selection during calibration and
    measurement activities.

    Attributes
    ----------
    ctr : integer
        It keeps track of user selection, i.e., whether any sensor
        are selected or not.
    duration : string
        The duration of the measurement.
    """

    global selection, duration

    # Parse user selection by reading the checkbox state
    ctr = 0
    selection.clear()
    duration = ent_duration.get()
    for idx, child in enumerate(
        fr_sens.scrollable_frame.children.values()
    ):
        if child.state.get() == 1:
            paths[idx] = str(child.lbl_path["text"])
            names[idx] = str(child.ent_name.get())
            # Create sensor objects and store it in a python list
            selection.append(
                Sensor(
                    paths[idx],
                    names[idx],
                    offsets[idx],
                    startBytes[idx],
                    duration
                )
            )
            ctr = ctr + 1

    # Return if no selection is made
    if not ctr:
        txt_log.insert(tk.END, timestampOp() + "No selection made.")
        txt_log.see("end")

def identifySensors():
    """
    A function to plot the sensor data for tagging.

    Attributes
    ----------
    lst_ids : list
        A list of JSON objects.
    duration : integer
        The duration of the plot in seconds.
    lbl : string
        The sensor path to label the plot.
    """
    parseSelection()

    if not selection:
        return
    if len(selection) > 1:
        txt_log.insert(tk.END,
            timestampOp()
            + "Only one selection can be made.")
        txt_log.see("end")
        return

    lbl = selection[0].path
    configureAxes(label=lbl)

    try:
        duration = 30
        lst_ids = json.dumps([obj.__dict__ for obj in selection])

        # Send plot sensor command to the server
        sock.sendall(str.encode('pltsens'))
        sock.sendall(lst_ids.encode())
        btn_pltData['state'] = tk.DISABLED
        txt_log.insert(tk.END, timestampOp() + "Plot initiated.")
        txt_log.see("end")
        sock.settimeout(0.10)
        plotMeasurement()
        threading.Thread(
            target=printStatus,
            args=(duration, )
        ).start()
    except Exception as e:
        txt_log.insert(tk.END, timestampOp + str(e))
    finally:
        txt_log.see("end")

def plotMeasurement():
    """
    A function to set up matplotlib animation function to poll the
    server for data and update the plot in near real-time.

    Attributes
    ----------
    ani : object
        The matplotlib animation object.
    duration : integer
        The duration of the plot in seconds.
    samplingRate : integer
        The number of samples polled from the server in a second.
    frames : integer
        The total frames generated during the plotting session.
    """

    global ani
    duration = 30
    samplingRate = 30
    frames = duration * samplingRate

    print("Plotting Data")

    try:
        # Setup a plot to call animate() function periodically
        ani = animation.FuncAnimation(
            fig,
            animate,
            fargs=(ys, ),
            frames=frames,
            interval=1,
            blit=True,
            repeat=False)
        canvas.draw()
    except Exception as e:
        print(str(e))

def animate(i, ys):
    """
    A function to read the data from the socket and update the line
    in the plot. It uses pickle module to de-serialize data.

    data : bytestring
        The data block received from the client.
    values : list
        A list to store the processed samples.
    sensitivity : integer
        The sensitivity of the sensor.
    offset : integer
        The sensor offset extracted from selection.
    value : integer
        A single data point for plotting.
    """

    # Unpickle the received data
    try:
        data = sock.recv(socksize)
        lst = pickle.loads(data)
    except:
        print("Timeout")
        return line,

    # Skip update if no data received
    if len(lst) == 0:
        return line,

    values = [] # List to store processed data
    sensitivity = 0.08 # Sensitivity

    # Sensor offset
    offset = selection[0].offset
    offset = float(offset)

    # Iterate over the list with a step size of 100.
    for val in range(0, len(lst)):
        # Do post-processing
        # Read acceleration in hex
        acc_raw_hex = lst[val]
        # Convert it into decimal
        acc_in_dec = int(acc_raw_hex, 16)
        # Perform sensitivity adjustment
        acc_in_g = round(acc_in_dec * sensitivity, 2)
        # Perform offset correction
        acc_in_g = acc_in_g - offset
        # Append processed values to the list
        values.append(round(acc_in_g, 2))

    # Select the first value in the list to plot.
    value = values[0]
    # (Optional) Average values from the list to plot.
    # Does not yield a good plot.
    #value = np.average(values)
    ys.append(value)
    ys = ys[-x_len:]

    # Update line in the plot with the received values.
    # Append y-values (acceleration) to the list.
    line.set_ydata(ys)

    return line,

def calibrateSensors():
    """
    A function to perform offset correction on selected sensors.

    Attributes
    ----------
    selectedList : list
        A JSON list of selected sensors to be sent over the network.
    """

    parseSelection()

    if not selection:
        return

    selectedList = json.dumps([obj.__dict__ for obj in selection])
    sock.sendall(str.encode('calsens'))
    sock.sendall(selectedList.encode())

    txt_log.insert(tk.END, timestampOp() + "Calibration in progress.")
    txt_log.see("end")

    #start a new thread to parse returned results
    threading.Thread(target=parseCalResults).start()

def parseCalResults():
    """
    A function running on a new thread receives the calibrated sensor
    values from the server and updates the table.

    Attributes
    ----------
    data : bytestring
        The data received at the socket.
    calValues : object
        The returned sensor list with calibration values.
    devlst : object
        The python object converted from a JSON object.
    ctr : integer
        It keeps track of the ids of the selection.
    id : integer
        The local ID of the sensor in the lists parsed
        from the path string.
    """

    data = sock.recv(socksize)
    calValues = data.decode()
    devlst = json.loads(calValues)

    for path, device in itertools.product(paths, devlst):
        if path == device["path"]:
            id = paths.index(device["path"])
            paths[id] = device["path"]
            names[id] = device["name"]
            offsets[id] = device["offset"]
            startBytes[id] = device["startByte"]

    ctr = 0
    for idx, child in enumerate(
        fr_sens.scrollable_frame.children.values()
    ):
        child.lbl_cal["text"] = '{:.2f}'.format(offsets[ctr])
        ctr = ctr + 1

    txt_log.insert(tk.END, timestampOp() + "Calibrated.")
    txt_log.see("end")

def startMeasurement():
    """
    A function to start the Sensor Measurement on the Raspberry Pi

    Attributes
    ----------
    lst_ids : list
        A JSON list of selected sensors to be sent over the network.
    """

    parseSelection()

    if not selection:
        return
    if not duration:
        txt_log.insert(
            tk.END,
            timestampOp() + "No duration entered."

        )
        txt_log.see("end")
        return

    try:
        #convert python list to json list
        lst_ids = json.dumps([obj.__dict__ for obj in selection])
        #send start measurement command to the server
        sock.sendall(str.encode('stmsrmt'))
        #send json list to server
        sock.sendall(lst_ids.encode())
        txt_log.insert(
            tk.END,
            timestampOp() + "Measurement started."
        )
        window.focus_set()
        #plotMeasurement()
        threading.Thread(
            target=showProgress,
            args=(duration, )
        ).start()
        threading.Thread(
            target=printStatus,
            args=(duration, )
        ).start()
    except Exception as e:
        txt_log.insert(tk.END, timestampOp() + str(e))
    finally:
        txt_log.see("end")

def showProgress(interval):
    """
    A function display countdown timer for the measurement in the
    entry field. It runs on a new thread sperate from the GUI.

    Parameters
    ----------
    interval : string
        The duration of the measurement.

    Returns
    -------
    None

    Attributes
    ----------
    duration : integer
        The interval of the measurement in seconds.
    """

    duration = int(interval)

    for second in range(duration, -1, -1):
        ent_duration.delete(0, tk.END)
        ent_duration.insert(0, str(second))
        time.sleep(1)

def printStatus(interval):
    """
    A function to print the status of measurement after completion.
    It runs on a new thread. It starts listening for status message
    after the timeout is complete.

    Parameters
    ----------
    interval : string
        The duration of the measurement.

    Returns
    -------
    None

    Attributes
    ----------
    status : bytestring
        The response from the server.
    msg : string
        The status of the measurement.
    """

    global ani

    # Wait till the measurement is complete
    time.sleep(int(interval))

    # Pause the animation.
    if ani != None:
        ani.event_source.stop()
        time.sleep(0.25)

    # Set socket to blocking.
    sock.settimeout(None)

    # Start listening for the completion status
    while True:
        try:
            #receive status over socket
            status = sock.recv(socksize)
            msg = status.decode()
            if (msg == "Measurement complete."
                or msg == "Plot complete."):
                txt_log.insert(tk.END, timestampOp() + msg)
                txt_log.see("end")
                ent_duration.delete(0, tk.END)
                btn_pltData['state'] = tk.NORMAL
                break
        except:
            pass

def openSettings():
    """
    A dialog to set Raspberry Pi credentials for secure file transfer.

    Attributes
    ----------
    popup : object
        A new tkinter window.
    txt_user : object
    txt_pass : object
        A tkinter label.
    ent_user : object
        A entry widget to input username.
    ent_pass : object
        A entry widget to input password.
    btn_confirm : object
        A button to confirm configuration.
    btn_cancel : object
        A button to cancel configuration.
    """

    def saveSettings():
        """
        A function to get the user input and save it to the global
        variables.

        Attributes
        ----------
        user : string
        pwd : string
            The raspberry pi credentials parsed from the user input.
        """

        global username, password

        user = ent_user.get()
        pwd = ent_pass.get()

        # Copy data to global variables
        username = user
        password = pwd

        popup.destroy()

    def cancelSettings():
        """
        A function to close the popup window.
        """

        popup.destroy()

    # Create a popup window.
    popup = tk.Toplevel(window)
    popup.focus_force()
    popup.title("Raspberry Pi Credentials")

    # Define widgets.
    txt_user = tk.Label(popup, text="Username", width=20)
    txt_pass = tk.Label(popup, text="Password", width=20)
    ent_user = tk.Entry(popup, width=20)
    ent_user.insert(tk.END, username)
    ent_pass = tk.Entry(popup, width=20, show="*")
    ent_pass.insert(tk.END, password)
    btn_confirm = tk.Button(popup,
                            text="Confirm",
                            command=saveSettings)
    btn_cancel = tk.Button(popup,
                           text="Cancel",
                           command=cancelSettings)

    # Add widgets to the window using grid geomertry manager.
    txt_user.grid(row=0,column=0,stick="nsew",padx=10,pady=5)
    txt_pass.grid(row=1,column=0,stick="nsew",padx=10,pady=5)
    ent_user.grid(row=0,column=1,stick="nsew",padx=10,pady=5)
    ent_pass.grid(row=1,column=1,stick="nsew",padx=10,pady=5)
    btn_confirm.grid(row=2,column=0,stick="nsew",padx=10,pady=5)
    btn_cancel.grid(row=2,column=1,stick="nsew",padx=10,pady=5)

    # Start event handler
    popup.mainloop()

def openFolder():
    """
    A function prompts user to select folder to store measurements.

    Attributes
    ----------
    folder_path : string
        The folder path selected by the user in the file dialog.
    """

    try:
        ent_sync.delete(0, tk.END)
        # Open a pop-up to select folder
        folder_path = filedialog.askdirectory()
        #write path to entry field
        ent_sync.insert(0, folder_path)
    except Exception as e:
        txt_log.insert(tk.END, timestampOp() + str(e))
        txt_log.see("end")

def startSync():
    """
    A function to start folder synchronization.

    app_path : string
        The application path on the raspberry pi.
    """

    global sock

    try:
        sock.sendall(str.encode('stsync'))
        data = sock.recv(socksize)
        app_path = data.decode()
    except Exception as e:
        txt_log.insert(tk.END, timestampOp() + str(e))
        txt_log.see("end")

    txt_log.insert(
        tk.END, timestampOp()
        + "Syncing folder. Please wait."
    )
    txt_log.see("end")

    #call syncFolder() function to start sync
    threading.Thread(target=syncFolder, args=(app_path,)).start()

def syncFolder(app_path):
    """
    The function uses scp utilily to synchronize captured measurement
    files from the Raspberry Pi onto the local client.
    It runs on a new thread so as to not block the main UI during sync.

    Parameters
    ----------
    app_path : string
        The application path polled from the raspberry pi(server).

    Attributes
    ----------
    ftpPort : integer
        The server port for file transfers.
    folder_path : string
        The user selected folder path parsed from the enrty field.
    pi_path : string
        The path at which the captured measurements are stored on the
        Raspberry Pi.
    ssh : object
        The ssh client object created using paramiko library.
    scp : object
        The scp protocol object to initiate file transfer.
    """

    ftpPort = 22

    folder_path = ent_sync.get()
    pi_path = app_path + "/samples"

    try:
        # Create a SSH client and use scp for file transfer
        ssh = createSSHClient(host, ftpPort, username, password)
        scp = SCPClient(ssh.get_transport())
        scp.get(pi_path,folder_path, recursive=True)

        txt_log.insert(
            tk.END,
            timestampOp() + "Synchronization complete."
        )
    except Exception as e:
        txt_log.insert(tk.END, timestampOp() + str(e))
    finally:
        txt_log.see("end")

def clearLog():
    """
    A function to clear the event log window.
    """

    txt_log.delete('1.0', tk.END)

def configureAxes(label):
    """
    A function to configure and update the plot axes.

    Parameters
    ----------
    label : string
        The label of the plot.

    Returns
    -------
    None

    Attributes
    ----------
    xs, ys : list
        A list that is populated in real-time for plotting.
        A pre-defined list makes the plot faster.
    line : object
        Plot y versus x as lines and/or markers.
    """

    global line, xs, ys

    # Set plot range
    ax.clear()
    ax.set_xlim(x_range)
    ax.set_ylim(y_range)

    # Add labels
    ax.set_title('Acceleration over Time')
    ax.set_xlabel('Samples')
    ax.set_ylabel('Acceleration (in g)')

    xs = list(range(0, 300))  # Data at x-axis (time/samples)
    ys = [0] * x_len # Data at y-axis (acceleration)

    # Initialize a line to update with sensor values later
    #line, = ax.plot(xs, ys)
    line, = ax.plot(xs, ys,
                    color=(np.random.uniform(0, 1),
                           np.random.uniform(0, 1),
                           np.random.uniform(0, 1))
            )
    line.set_label(label)

    ax.legend()

def cleanup():
    """
    A function to perform clean up actions upon application closure.
    The lists are de-initialized and the sensor list is cleared.
    """

    # Clear sensor lists
    states.clear()
    ids.clear()
    paths.clear()
    names.clear()
    serials.clear()
    offsets.clear()
    startBytes.clear()

    placeholder.destroy()   # Remove placeholder

    # Remove rows from the table
    for child in fr_sens.scrollable_frame.winfo_children():
        child.destroy()

# Function to handle toolbar events
def on_key_press(event):
    print("you pressed {}".format(event.key))
    key_press_handler(event, canvas, toolbar)

"""
Attributes
----------
host : string
    The hostname or ip address of the server,
    resolved by Multicast DNS.
port : integer
    The port on which the server is hosted
socksize : integer
    The receive buffer size of the opened socket
states : list
    A list which stores the state of the checkboxes.
ids : list
    A locally generated list of sensor ids
paths : list
    A list of sensor paths parsed from the server response
serials : list
    A list of sensor serial numbers parsed from the server
names : list
    A list of user-defined sensor names updated locally
offsets : list
    A list of sensor offset values stored after calibration
startBytes : list
    A list of start byte values stored after calibration
selection : list
    A list that stores user selection to be used by multiple
    functions
duration : string
    The duration  of the measurement
username : string
password : string
    The default credentials of a Raspberry Pi.
"""

host = 'raspberrypi.local'
port = 50001
socksize = 1024

(states, ids, paths, serials,
names, offsets, startBytes,
selection) = ([] for i in range(8))

duration = ""

username = "pi"
password = "raspberry"

"""
Create a GUI using Tkinter

Attributes
----------
window : object
    The Tk class instantiated without arguments. It creates a
    top level widget of Tk which is usually the main window of
    the application.
"""

window = tk.Tk()
window.title(
    "PiConnect - Intelligent Wireless Sensor Measurement Platform"
)
window.resizable(width=False, height=False)

"""
Tkinter frames offer logical seperation to the application.
The frames are classified as primary and secondary frames
so as to assign an appropriate layout for each frame using
geomertry managers. Primary frames use a grid layout whereas
secondary app frames use a mix of grid and pack layout.

Attributes
----------
fr_conn : object
    It encompasses GUI widgets to manage remote network
    connection with the Raspberry Pi.
fr_msmt : object
    It contains widgets to display connected sensor details
    and set measurement parameters.
fr_sync : object
    It contains widgets to syncronize recorded measurements.
fr_elog : object
    It contains widgets to display control and status messages.
fr_plot : object
    It contains widgets to plot the real-time sensor data.
"""

# Primary app frames encompassing specified functions
fr_conn = tk.LabelFrame(window, text="Connection", bd=1)
fr_msmt = tk.LabelFrame(window, text="Measurement", bd=1)
fr_sync = tk.LabelFrame(window, text="Synchronization", bd=1)
fr_elog = tk.LabelFrame(window, text="Log", bd=1)
fr_plot = tk.LabelFrame(window, text="Real-time plot", bd=1)

# Add primary frames to the window using grid geomertry manager
fr_conn.grid(row=0, column=0, sticky='nsew',
             padx=10, pady=5)
fr_msmt.grid(row=1, column=0, sticky='nsew',
             padx=10, pady=5)
fr_sync.grid(row=2, column=0, sticky='nsew',
             padx=10, pady=5)
fr_elog.grid(row=3, column=0, sticky='nsew', columnspan=2,
             padx=10, pady=5)
fr_plot.grid(row=0, column=1, sticky='nsew', rowspan=3,
             padx=10, pady=5)

# Secondary app frames containing widgets
fr_conn_child = tk.Frame(fr_conn)
fr_msmt_child = tk.Frame(fr_msmt)
fr_sync_child = tk.Frame(fr_sync)
fr_elog_child = tk.Frame(fr_elog)
fr_plot_child = tk.Frame(fr_plot)

# Add secondary frames to the window using pack geomertry manager
fr_conn_child.pack(fill='both', expand='yes')
fr_msmt_child.pack(fill='both', expand='yes')
fr_sync_child.pack(fill='both', expand='yes')
fr_elog_child.pack(fill='both', expand='yes')
fr_plot_child.pack(fill='both', expand='yes')

"""
Connection frame: Add widgets to the fr_conn_child frame

Attributes
----------
lbl_status, lbl_ipaddr : object
    A tkinter Label widget to display label.
ent_status, ent_ipaddr : object
    A tkinter Entry widget for user input.
can_status : object
    A tkinter Canvas widget to emulate LED by
    setting background colors.
led : integer
    The object id of the new oval object created
    on the canvas.
btn_conn, btn_disc : object
    A tkinter Button widget which performs
    defined actions on button press.
"""

# Initialize widgets
lbl_status = tk.Label(fr_conn_child, text ="Connection status",
                      anchor='w')
lbl_ipaddr = tk.Label(fr_conn_child, text="Enter IP address",
                      anchor='w')
ent_status = tk.Entry(fr_conn_child, width = 20)
ent_status.insert(0, "Disconnected") # Set default value
ent_ipaddr = tk.Entry(fr_conn_child, width=20)
can_status = tk.Canvas(fr_conn_child, width=25, height=20)
led = can_status.create_oval(5, 5, 17.5, 17.5,
                             fill="red", width=3, outline='red')
btn_conn = tk.Button(fr_conn_child, text = "Connect", width=10,
                     relief=tk.RAISED, command=connectPi)
btn_disc = tk.Button(fr_conn_child, text = "Disconnect", width=10,
                     relief=tk.RAISED, command=disconnectPi)

# Add widgets to the grid
lbl_status.grid(row=0, column=0, sticky='ew', padx=20, pady=5)
lbl_ipaddr.grid(row=1, column=0, sticky='ew', padx=20, pady=5)
ent_status.grid(row=0, column=1, sticky='ew', padx=5, pady=5)
can_status.grid(row=0, column=2, sticky='w', padx=5, pady=5)
ent_ipaddr.grid(row=1, column=1, sticky='ew', padx=5, pady=5)
btn_conn.grid(row=1, column=2, sticky='ew', padx=5, pady=5)
btn_disc.grid(row=1, column=3, sticky='ew', padx=5, pady=5)

"""
Measurement frame: Add widgets to the fr_msmt_child frame

Attributes
----------
titles : list
    A list of strings to label the sensor table.
titles_width : list
    A list of padding values to properly align the columns.
lbl_rfshLst, lbl_offset, lbl_duration, lbl_units : object
    A tkinter Label widget.
btn_rfshLst : object
    A tkinter Button widget to refresh connected sensor list.
btn_pltData : object
    A tkinter Button widget to initiate plot to identify sensors.
btn_offset : object
    A tkinter Button widget to perform offset correction for the
    user selected list of sensors.
ent_duration : object
    A Entry widget to enter the duration of the measurement.
btn_startMeasure : object
    A Button widget to start measurement for the selected sensons
    and specified duration.
fr_table : object
    A tkinter frame to display connected sensors in a tabular format.
fr_sens : object
    A tkinter frame inside fr_table that stores table and scrollbar.
fr_label : object
    A tkinter frame that dynamically populates sensor list.
placeholder : object
    A tkinter Label widget serves as a placeholder on initialization
    before the sensor list is parsed from the server.
"""

titles = [
    "", "ID", "Path", "Serial Number",
    "Name", "Offset"
]
titles_width = [3, 5, 15, 15, 15, 15]

# Initialize widgets
lbl_rfshLst = tk.Label(
    fr_msmt_child,
    text = "Select sensor board for measurement",
    anchor='w',
    padx=15
)
lbl_offset = tk.Label(
    fr_msmt_child,
    text="Perform offset correction on selected sensors",
    anchor='w',
    padx=15
)
lbl_duration = tk.Label(
    fr_msmt_child,
    text = "Enter duration of measurement",
    anchor='w',
    padx=15
)
lbl_units = tk.Label(fr_msmt_child, text = "seconds")
btn_rfshLst = tk.Button(fr_msmt_child, text = "Update List",
                        width = 10, relief = tk.RAISED,
                        command=getSensorList)
btn_pltData = tk.Button(fr_msmt_child, text = "Identify sensor",
                        width = 10, relief=tk.RAISED,
                        command=identifySensors)
btn_offset = tk.Button(fr_msmt_child, text="Calibrate",
                       width=10, relief=tk.RAISED,
                       command=calibrateSensors)
btn_startMeasure = tk.Button(fr_msmt_child, text = "Start Measurement",
                             width = 20, relief = tk.RAISED,
                             command=startMeasurement)
ent_duration = tk.Entry(fr_msmt_child, width = 10)

fr_table = tk.LabelFrame(fr_msmt_child, bd=1, padx=5, pady=5)
fr_sens = ScrollableFrame(fr_table)
fr_label = tk.LabelFrame(fr_msmt_child, bd=1)

fr_sens.grid(row=0, column=0, sticky='nsew')

# Populate titles
for title in range(len(titles)):
    tk.Label(
        fr_label,
        text=titles[title],
        width=titles_width[title],
        anchor='center'
    ).grid(
        row=0,
        column=title,
        sticky='nsew',
        padx=(1,0)
    )

placeholder = tk.Label(fr_sens.scrollable_frame, text="")
placeholder.grid(row=0, column=0, sticky="ew")

# Add widgets to the grid
lbl_rfshLst.grid(row = 0, column = 0, sticky = 'ew',
                 padx = 5, pady = 5)
btn_pltData.grid(row = 0, column = 1, sticky = 'ew',
                 padx = (15, 5), pady = 5)
btn_rfshLst.grid(row = 0, column = 2, sticky = 'ew',
                 padx = (5, 20), pady = 5)
fr_label.grid(row=1, column=0, sticky='nsew',
              columnspan=3, padx=20)
fr_table.grid(row = 2, column = 0, sticky = 'nsew',
              columnspan=3, padx = 20)
lbl_offset.grid(row = 3, column = 0, sticky = 'ew',
                padx = 5, pady=(10, 0))
btn_offset.grid(row = 3, column = 1, sticky = 'ew',
                padx = 5, pady=(10, 0))
lbl_duration.grid(row = 4, column = 0, sticky = 'ew',
                  padx = 5, pady = 5)
ent_duration.grid(row = 4, column = 1, sticky = 'ew',
                  padx = 5, pady = 5)
lbl_units.grid(row = 4, column = 2, sticky = 'ew',
               padx = 5, pady = 5)
btn_startMeasure.grid(row = 5, column = 0, sticky = 'ew',
                      columnspan = 3, padx = 15, pady = (0,5))

"""
Synchronization frame: Add widgets to the fr_sync_child frame

Attributes
----------
lbl_sync : object
    A tkinter Label widget.
ent_sync : object
    A tkinter Entry widget to parse user selected file path.
btn_open : object
    A tkinter Button widget to open file dialog.
btn_sync : object
    A tkinter Button to initiate sync of the captured data files.
"""

# Initialize widgets
lbl_sync =  tk.Label(
    fr_sync_child,
    text="Select a folder on the local computer to sync measurements",
    anchor='w')
btn_cred = tk.Button(fr_sync_child, text="Settings",
                     width=15, relief=tk.RAISED,
                     command=openSettings)
ent_sync = tk.Entry(fr_sync_child, width = 40)
btn_open = tk.Button(fr_sync_child, text="Open",
                     width = 15, relief = tk.RAISED,
                     command=openFolder)
btn_sync = tk.Button(fr_sync_child, text="Sync",
                     width = 15, relief = tk.RAISED,
                     command=startSync)

# Add widgets to the grid
lbl_sync.grid(row=0, column=0, sticky='ew', padx=20, pady=5)
btn_cred.grid(row=0, column=1, sticky="ew", padx=5, pady=5)
ent_sync.grid(row=1, column=0, sticky='ew', padx=20, pady=5)
btn_open.grid(row = 1, column=1, sticky='ew', padx=5, pady=5)
btn_sync.grid(row = 1, column=2, sticky='ew', padx=5, pady=5)

"""
Log frame: Add widgets to the fr_elog_child frame

Attributes
----------
fr_ctl : object
    A tkinter frame to encapsulate control buttons.
fr_log : object
    A tkinter frame that encapsulates the event log as a Text widget.
lbl_log : object
    A tkinter Label widget
btn_clear : object
    A tkinter Button widget to clear log contents.
txt_log : object
    A tkinter Text widget to display multi-line control and error
    messages.
scrbar_log : object
    A tkinter Scrollbar widget attached to the log frame.
"""

# Secondary frames
fr_ctl = tk.Frame(fr_elog_child)
fr_log = tk.Frame(fr_elog_child)

# Initialize widgets
lbl_log = tk.Label(fr_ctl, text="Real-time Event Log", anchor='w')
btn_clear = tk.Button(fr_ctl, text="Clear Log", width=25,
                      relief = tk.RAISED, command=clearLog)
txt_log = tk.Text(fr_log, borderwidth=1,
                  relief=tk.GROOVE, spacing1=1, height=14)

# Initialize the scrollbar and attack it to the Text widget
scrbar_log = tk.Scrollbar(fr_log, orient = 'vertical',
                          command=txt_log.yview)
scrbar_log.pack(fill='y', side='right')
# Attach the Text widget to the scrollbar
txt_log.configure(yscrollcommand = scrbar_log.set)

# Add widgets to the frame using pack geomertry manager
fr_ctl.pack(fill='both', expand='yes', padx=5)
fr_log.pack(fill='both', expand='yes', padx=5)
lbl_log.pack(fill='both', expand='yes', side='left',
             padx=10, pady=5, anchor='w')
btn_clear.pack(fill='y', expand='yes', side='right',
               padx=10, pady=5, anchor='e')
txt_log.pack(fill='both', expand='yes', padx=10, pady=5)

"""
Plot frame: Add widgets to the fr_plot_child frame

Attributes
----------
x_len : integer
    The range of samples to be displayed on the x-axis.
x_range : list
    A list that stores the range of the x-axis.
y_range : list
    A list that stores the range of the y-axis.
xs, ys : list
    A list that is populated in real-time for plotting
    A pre-defined list makes the plot faster.
fig : object
    A tkinter Figure object.
ax : object
    Add a subplot to the current figure.
line : object
    Plot y versus x as lines and/or markers.
canvas : object
    Define a tkinter canvas widget to graph the plot.
toolbar : object
    Define matplotlib built-in toolbar.
cid : integer
    A connection id returned by the mpl_connect() function.
"""

# Parameters
x_len = 300
x_range = [0, 300]
y_range = [-5, 5]

# Create figure for plotting
fig = plt.Figure(figsize=(5, 4), dpi=100)
ax = fig.add_subplot(1, 1, 1)

xs, ys = ([] for i in range(2))
line = None
ani = None

configureAxes(label="sensorX")

canvas = FigureCanvasTkAgg(fig, master=fr_plot_child)
canvas.draw()
canvas.get_tk_widget().pack(side=tk.TOP, fill=tk.BOTH, expand=1)

toolbar = NavigationToolbar2Tk(canvas, fr_plot_child)
toolbar.update()
canvas.get_tk_widget().pack(side=tk.TOP, fill=tk.BOTH, expand=1)

cid = canvas.mpl_connect("key_press_event", on_key_press)

# Start event handler
window.mainloop()
