#!/usr/bin/python2
import sys
import paho.mqtt.client as mqtt
import requests
import time
import password

global flowMeter1
global flowMeter2

'''This code subscribes to a mqtt broker that is delivering data from two
flowmeters. The flowmeter data is in raw counts or 'ticks' from the
hall effect sensors that detect the turning of a small magnetic turbine
int the flowmeter device. The counts are converted to flow rate and total
gallons / month, and then are forwarded to a "Thingspeak" channel for visual display.'''

'''Thingspeak channel parameters defined in password.py
APIKey = "xxxx"
MYCHANNEL = "xxxx"
'''
# mqtt subscription topics
subscriptions = [("yard/water/flow1" , 0) , ("yard/water/flow2" , 0)]


# The callback for when the client receives a CONNACK response from the server.
def on_connect(client, userdata, flags, rc):
    """initialize state on connection to broker"""
    if rc == 0:
        print("Connected to broker")
        global Connected  # Use global variable
        Connected = True  # Signal connection
        # Subscribing in on_connect() means that if we lose the connection and
        # reconnect then subscriptions will be renewed.
        client.subscribe (subscriptions)
    else:
        print("Connection failed" + str (rc))


# The callback for when a PUBLISH message is received from the server.
def on_message(client, userdata, msg):
    """handle incomming subscribed message"""
    global total_gallons
    global lasttime
    global flowMeter1
    global flowMeter2

    topic = msg.topic
    sys.stdout.write (topic + " ")
    if topic == 'yard/water/flow1':
        flowMeter1.accumulate (msg)
    if topic == 'yard/water/flow2':
        flowMeter2.accumulate (msg)

    t = time.time ()
    if t - lasttime > 15:  # report data to thingspeak max once per 30 sec
        dat = {'key': password.APIKey}
        gallons = flowMeter1.send ()
        if gallons != -1:  # check for 'send nothing' signal
            total_gallons += gallons
            dat['field1'] = gallons

        gallons = flowMeter2.send ()
        if gallons != -1:
            total_gallons += gallons
            dat['field2'] = gallons

            # total gallons must be persistent
        with open ("totalgallons", "w") as f:
            f.write (str (total_gallons))

            # if there is some data, send it
        if 'field1' in dat or 'field2' in dat:
            dat['field3'] = total_gallons
            print('sending')
            print(dat)
            lasttime = time.time ()
            requests.post ('https://api.thingspeak.com/update' , data=dat)
            # for debug, performance monitoring
            client.publish ("status" , "flow posted")

    # reset total ticks (therefore gallons) once per month
    day = time.localtime (t)[2]
    hour = time.localtime (t)[3]
    minute = time.localtime (t)[4]
    if day == 1 and hour == 1 and minute == 1:
        total_gallons = 0
        with open ("totalgallons", "w") as f:
            f.write (str (total_gallons))


class TsDataManager:
    """ take in mqtt message and emit gallons"""

    def __init__(self):
        self.ticks = 0
        self.ticks = 0
        self.valve_on = False

    def accumulate(self, mess):
        """accumulate flowmeter counts"""
        try:  # use parse library to extract flow meter ticks from message
            tic = int (mess.payload.decode ("utf-8"))
            print(tic)
            self.ticks += tic
        except  StandardError:
            print('message decode error {}'.format (mess.payload.decode ("utf-8")))

    def send(self):
        """COMPUTE GALLONS
        The hall-effect flow sensor outputs approximately 7.5 pulses per second per
        litre/minute of flow or 450 pulses per liter, 1703.4 pulses per gallon"""
        gallons = (self.ticks * 2) / 1703.4  # 2 factor because we report twice per minute
        '''The following raindance is done just to make the Thing Speak graphs look good.
        So if the valve is changing, override gallons with a dummy 0 so graph looks OK '''
        if self.valve_on == False and self.ticks != 0:  # valve has just turned on
            self.valve_on = True
            gallons = 0  # send start/stop marker
        elif self.valve_on == True and self.ticks == 0:  # valve has just turned off
            # check to see if the valves are shutting off
            self.valve_on = False
            gallons = 0  # send start/stop marker
        elif self.valve_on == False and self.ticks == 0:  # valve in steady state off
            gallons = -1  # signal to send nothing
        else:  # water is flowing
            self.ticks = 0  # quit accumulating, we are sending computed gallons
        return (gallons)


# noinspection PyPep8Naming
def main():
    global Connection
    Connected = False  # global variable for the state of the connection
    # ticks = one count from flow meter, about 2.5 ml
    global total_gallons  # total monthly gallons
    global lasttime
    global flowMeter1
    global flowMeter2
    print('Running FloMe')
    try:
        with open ("totalgallons", "r") as f:
            total_gallons = float(f.readlines()[0])
    except (OSError , IOError) as e:
        total_gallons = 0

    lasttime = time.time ()
    flowMeter1 = TsDataManager ()
    flowMeter2 = TsDataManager ()
    client = mqtt.Client ()
    client.on_connect = on_connect
    client.on_message = on_message
    client.connect ("raspberrypi.local")
    client.loop_start ()  # start the loop
    while Connected != True:  # Wait for connection
        time.sleep (0.1)
        sys.stdout.write ('.')
        sys.stdout.flush ()
    # Blocking call that processes network traffic, dispatches callbacks and
    # handles reconnecting.
    client.loop_forever ()


if __name__ == "__main__":
    main ()
