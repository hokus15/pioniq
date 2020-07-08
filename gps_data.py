#! /usr/bin/python

# Based on script written by Dan Mandle http://dan.mandle.me September 2012
# http://www.danmandle.com/blog/getting-gpsd-to-work-with-python/
# License: GPL 2.0

import paho.mqtt.client as mqtt
import ssl
import json
import logging
import logging.handlers
import os

import gps
import threading
import time

gpsd = None # setting the global variable

#MQTT function for on_publish callback
def on_publish(client, userdata, mid):
    logger.debug("Publish message id: {}".format(mid))
    pass

def on_connect(client, userdata, flags, rc):
    if rc==0:
        client.connected_flag=True #set flag
        logger.info("Successfully connected to MQTT")
    else:
        logger.error("Not connected to MQTT. Bad connection Returned code=",rc)

class GpsPoller(threading.Thread):
    def __init__(self):
        threading.Thread.__init__(self)
        global gpsd # bring it in scope
        gpsd = gps.gps(mode=gps.WATCH_ENABLE) # starting the stream of info
        self.current_value = None
        self.running = True

    def run(self):
        global gpsd
        while gpsp.running:
            # this will continue to loop and grab EACH set of
            # gpsd info to clear the buffer
            next(gpsd)

if __name__ == '__main__':
    logger = logging.getLogger('gps')
    
    console_handler = logging.StreamHandler() # sends output to stderr
    console_handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s [%(name)s] %(message)s"))
    console_handler.setLevel(logging.DEBUG)
    logger.addHandler(console_handler)
    
    file_handler = logging.handlers.TimedRotatingFileHandler(os.path.dirname(os.path.realpath(__file__)) + '/gps_data.log',
                                                    when='midnight',
                                                    backupCount=15) # sends output to gps_data.log file rotating it at midnight and storing latest 15 days

    file_handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s [%(name)s] %(message)s"))
    file_handler.setLevel(logging.INFO)
    logger.addHandler(file_handler)

    logger.setLevel(logging.DEBUG)
    
    with open(os.path.dirname(os.path.realpath(__file__)) + '/gps_data.config.json') as config_file:
        config = json.loads(config_file.read())
    
    broker_address = config['mqtt']['broker']
    port = int(config['mqtt']['port'])
    user = config['mqtt']['user']
    password = config['mqtt']['password']
    topic_prefix = config['mqtt']['topic_prefix']

    gpsp = GpsPoller()   # create the GPS thread
    
    try:
        logger.info("=== Script start ===")
        
        # Start GPS Poller thread
        gpsp.start()
        
        mqtt.Client.connected_flag = False
        # Create MQTT client
        mqtt_client= mqtt.Client(client_id="gps-data-script", protocol=mqtt.MQTTv311, transport="tcp")
        # Assign callback functions
        mqtt_client.on_publish = on_publish 
        mqtt_client.on_connect = on_connect
        # Start loop to process callbacks
        mqtt_client.loop_start()
        # Set tls
        mqtt_client.tls_set()
        # Set user and password
        mqtt_client.username_pw_set(user,password)
        # Enable MQTT logger
        mqtt_client.enable_logger(logger)
        # Conect to MQTT server
        while not mqtt_client.connected_flag:
            try:
                mqtt_client.connect(broker_address,port)
            except Exception as err:
                logger.error("MQTT connection could not be established: {}, retrying... ".format(err), exc_info=False)
            time.sleep(1)

        previous_latitude = 0
        previous_logitude = 0
        max_accuracy = int(config['service']['min_accuracy'])

        sleep_time = int(config['service']['sleep'])
        
        published_messages = 0
        while True:
            try:
                # It may take some seconds to get good data
                logger.debug("Latitude error (EPY): +/- {} m".format(gpsd.fix.epy))
                logger.debug("Longitude error (EPX): +/- {} m".format(gpsd.fix.epx))
                fix_accuracy = max(gpsd.fix.epy, gpsd.fix.epx)
                logger.info("Location accuracy: +/- {} m".format(fix_accuracy))
                if fix_accuracy < max_accuracy:
                    logger.debug("GPS position fixed with +/- {} m".format(fix_accuracy))
                    location = {'latitude': gpsd.fix.latitude,
                                'longitude': gpsd.fix.longitude,
                                'gps_accuracy': fix_accuracy,
                                'eps': gpsd.fix.eps, # Estimated Speed error
                                'epx': gpsd.fix.epx, # Estimated longitude error
                                'epy': gpsd.fix.epy, # Estimated latitude error
                                'epv': gpsd.fix.epv, # Estimated altitude error
                                'ept': gpsd.fix.ept, # Estimated time error
                                'speed': gpsd.fix.speed, # m/s
                                'climb': gpsd.fix.climb, 
                                'track': gpsd.fix.track,
                                'mode': gpsd.fix.mode,
                                'last_update': int(round(time.time()))
                            }
                    if previous_latitude != 0 and previous_logitude != 0:
                        # Previous latitude and longitude data is useful to measure distance travelled between updates.
                        location.update({
                            'platitude': previous_latitude, # Latitude got from previous read
                            'plongitude': previous_logitude # Longitude got from previous read
                        })
                    previous_latitude = gpsd.fix.latitude
                    previous_logitude = gpsd.fix.longitude
    
                    # Publish to MQTT
                    logger.debug("Publishing positon to MQTT...")
                    logger.debug("{}".format(json.dumps(location)))
                    result = mqtt_client.publish(topic=topic_prefix + "location", payload=json.dumps(location), qos=0, retain=True)
                    result.wait_for_publish()                    
                    if (result.rc == 0): 
                        logger.info("Message successfully published: " + str(result))
                        published_messages += 1
                    else:
                        logger.error("Error publishing message: " + str(result))
    
    #                logger.debug("%s satellites in view" % len(gpsd.satellites))
    #                for sat in gpsd.satellites:
    #                    logger.debug("    %r" % sat)
                else:
                    logger.warning("Location not accurate enought: it's +/- {} m but +/- {} m required".format(fix_accuracy, max_accuracy))
                logger.debug("Waiting {} seconds...".format(sleep_time))
                time.sleep(sleep_time)
            except Exception as ex:
                logger.exception("Unexpected error: {}".format(ex))

    except (KeyboardInterrupt, SystemExit):
        # when you press ctrl+c
        pass
    except Exception as ex:
        logger.exception("Unexpected error: {}".format(ex))
    finally:
        logger.info("Killing threads...")
        gpsp.running = False
        gpsp.join()   # wait for the thread to finish what it's doing
        mqtt_client.loop_stop()
        mqtt_client.disconnect()
        logger.info("{} location points published".format(published_messages))
        logger.info("=== Script end ===")
