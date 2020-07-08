#!/usr/bin/python

import paho.mqtt.publish as publish
import paho.mqtt.client as mqtt
import ssl
import time
import json
import logging
import logging.handlers
import os

import obd
from obd import OBDCommand, OBDStatus
from obd.protocols import ECU
from obd.decoders import raw_string
from obd.utils import bytes_to_int

class ConnectionError(Exception): pass

class CanError(Exception): pass

class NoData(Exception): pass

# CAN response decoder
def can_response(can_message):
    data = None
    data_len = 0
    last_idx = 0

    raw = can_message[0].raw().split('\n')
    for line in raw:
        if (len(line) != 19):
            raise ValueError('Error parsing CAN response: {}. Invalid line length {}!=19. '.format(line,len(line)))
    
        offset = 3
        identifier = int(line[0:offset], 16)
    
        frame_type = int(line[offset:offset+1], 16)
    
        if frame_type == 0:     # Single frame
            data_len = int(line[offset+1:offset+2], 16)
            data = bytes.fromhex(line[offset+2:data_len*2+offset+2])
            break
    
        elif frame_type == 1:   # First frame
            data_len = int(line[offset+1:offset+4], 16)
            data = bytearray.fromhex(line[offset+4:])
            last_idx = 0
    
        elif frame_type == 2:   # Consecutive frame
            idx = int(line[offset+1:offset+2], 16)
            if (last_idx + 1) % 0x10 != idx:
                raise CanError("Bad frame order: last_idx({}) idx({})".format(last_idx,idx))
    
            frame_len = min(7, data_len - len(data))
            data.extend(bytearray.fromhex(line[offset+2:frame_len*2+offset+2]))
            last_idx = idx
    
            if data_len == len(data):
                break
    
        else:                   # Unexpected frame
            raise ValueError('Unexpected frame')
    return data

# Odometer decoder
def odometer(can_message): 
    raw_b22b002 = can_response(can_message)
    return bytes_to_int(raw_b22b002[9:12])

# Publish all messages to MQTT
def publish_data_mqtt(msgs):
    try:
        logger.debug("*** Publish to MQTT ***")
        logger.debug("{}".format(msgs))
        publish.multiple(msgs,
                    hostname=broker_address,
                    port=port,
                    client_id=None,
                    keepalive=60,
                    will=None,
                    auth={'username':user, 'password':password},
                    tls={'tls_version':ssl.PROTOCOL_TLS},
                    protocol=mqtt.MQTTv311,
                    transport="tcp")
        logger.warning("{} message(s) published to MQTT".format(len(msgs)))
    except Exception as err:
        logger.error("Error publishing to MQTT: {}".format(err), exc_info=False)

# main script
if __name__ == '__main__':
    logger = logging.getLogger('battery')
    
    console_handler = logging.StreamHandler() # sends output to stderr
    console_handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s [%(name)s] %(message)s"))
    console_handler.setLevel(logging.DEBUG)
    logger.addHandler(console_handler)
    
    file_handler = logging.handlers.TimedRotatingFileHandler(os.path.dirname(os.path.realpath(__file__)) + '/battery_data.log',
                                                    when='midnight',
                                                    backupCount=15) # sends output to battery_data.log file rotating it at midnight and storing latest 15 days
    file_handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s [%(name)s] %(message)s"))
    file_handler.setLevel(logging.WARNING)
    logger.addHandler(file_handler)

    logger.setLevel(logging.DEBUG)
    
    with open(os.path.dirname(os.path.realpath(__file__)) + '/battery_data.config.json') as config_file:
        config = json.loads(config_file.read())
    
    broker_address = config['mqtt']['broker']
    port = int(config['mqtt']['port'])
    user = config['mqtt']['user']
    password = config['mqtt']['password']
    topic_prefix = config['mqtt']['topic_prefix']
    
    mqtt_msgs = []
    
    try:
        logger.warning("=== Script start ===")
        
        mqtt_msgs.extend([{'topic':topic_prefix + "state", 'payload':"ON", 'qos':0, 'retain':True}])
        
        obd.logger.setLevel(obd.logging.DEBUG)
        # Remove obd logger existing handlers
        for handler in obd.logger.handlers[:]:
            obd.logger.removeHandler(handler)
         # Add handlers to obd logger
        obd.logger.addHandler(console_handler)
        obd.logger.addHandler(file_handler)
    
        # Establish connection with OBDII dongle
        connection = obd.OBD(portstr=config['serial']['port'], baudrate=int(config['serial']['baudrate']), fast=False, timeout=30)
        
        if connection.status() != OBDStatus.CAR_CONNECTED:
            raise ConnectionError(connection.status())
    
        # Define needed commands
        can_receive_address_7ec = OBDCommand("CAN Receive Address to 7EC",
                                            "Set the CAN receive address to 7EC",
                                            b"ATCRA7EC",
                                            0,
                                            raw_string,
                                            ECU.ALL,
                                            False)
        
        can_filter_7ce = OBDCommand("CAN filter to 7CE",
                                    "Set the CAN filter to 7CE",
                                    b"ATCF7CE",
                                    0,
                                    raw_string,
                                    ECU.ALL,
                                    False)
        
        can_mask_7ff = OBDCommand("CAN mask to 7FF",
                                "Set the CAN mask to 7FF",
                                b"ATCM7FF",
                                0,
                                raw_string,
                                ECU.ALL,
                                False)
        
        cmd_2101 = OBDCommand("2101",
                            "2101 command",
                            b"2101",
                            0,
                            can_response,
                            ECU.ALL,
                            False)
                            
        cmd_2105 = OBDCommand("2105",
                            "2105 command",
                            b"2105",
                            0,
                            can_response,
                            ECU.ALL,
                            False)
        
        odo = OBDCommand("Odometer",
                            "Get odometer data",
                            b"22b002",
                            0,
                            odometer,
                            ECU.ALL,
                            False,
                            "7C6")
    
        # Add defined commands to supported commands
        connection.supported_commands.add(can_receive_address_7ec)
        connection.supported_commands.add(can_filter_7ce)
        connection.supported_commands.add(can_mask_7ff)
        connection.supported_commands.add(cmd_2101)
        connection.supported_commands.add(cmd_2105)
        connection.supported_commands.add(odo)
    
        # Print supported commands
        # DTC = Diagnostic Trouble Codes
        # MIL = Malfunction Indicator Lamp
        #logger.debug(connection.print_commands())
        
        logger.debug("*** Get battery status information ***")
        
        # Set the CAN receive address to 7EC - Needed for next commands
        atcra7ec = connection.query(can_receive_address_7ec)
        
        # 2101,2105 codes to get battery status information
        raw_2101 = connection.query(cmd_2101)
        raw_2105 = connection.query(cmd_2105)
    
        soh = bytes_to_int(raw_2105.value[27:29]) / 10.0
        
        # Only create battery status data if got a consistent Status Of Health (sometimes it's not consistent)
        if (soh <= 100):
            data_battery = {}
            chargingBits = raw_2101.value[11]
        
            data_battery.update({
                'timestamp':                int(round(time.time())),
        
                'soc_bms':                  raw_2101.value[6] / 2.0,
                'soc_display':              int(raw_2105.value[33] / 2.0),
        
                'auxBatteryVoltage':        raw_2101.value[31] / 10.0,
        
                'charging':                 1 if chargingBits & 0x80 else 0,
                'normalChargePort':         1 if chargingBits & 0x20 else 0,
                'rapidChargePort':          1 if chargingBits & 0x40 else 0,
        
                'soh':                      soh,
        
                'fanStatus':                raw_2101.value[29],
                'fanFeedback':              raw_2101.value[30],
                
                'cumulativeEnergyCharged':  bytes_to_int(raw_2101.value[40:44]) / 10.0,
                'cumulativeEnergyDischarged': bytes_to_int(raw_2101.value[44:48]) / 10.0,
        
                'cumulativeChargeCurrent':  bytes_to_int(raw_2101.value[32:36]) / 10.0,
                'cumulativeDischargeCurrent': bytes_to_int(raw_2101.value[36:40]) / 10.0,
        
                'availableChargePower':     bytes_to_int(raw_2101.value[7:9]) / 100.0,
                'availableDischargePower':  bytes_to_int(raw_2101.value[9:11]) / 100.0,
                })
        
            logger.info("Got battery data: {}".format(json.dumps(data_battery)))
            
            # Publish battery data to MQTT
            mqtt_msgs.extend([{'topic':topic_prefix + "battery", 'payload':json.dumps(data_battery), 'qos':0, 'retain':True}])
        else:
            logger.error("Got inconsistent data for battery Status Of Health: {}%".format(soh))
    
        try:
            logger.debug("*** Get odometer information ***")
            # Sets the ID filter to 7EC
            atcf7ce = connection.query(can_filter_7ce)
            # Sets the ID mask to 7FF
            atcm7ff = connection.query(can_mask_7ff)
            # Query odometer
            odometer_value = connection.query(odo)
        except (ValueError, CanError, NoData) as err:
            logger.warning("Error getting odometer value: {}".format(err), exc_info=False) # Not available when car engine is off

        # Only set odometer data if present
        if 'odometer_value' in locals() and odometer_value is not None:
            logger.info("Got odometer value: {}".format(odometer_value.value))
            # Publish odometer data to MQTT
            mqtt_msgs.extend([{'topic':topic_prefix + "odometer", 'payload':odometer_value.value, 'qos':0, 'retain':True}])
    except ConnectionError as err:
        logger.error("OBDII connection error: {0}".format(err), exc_info=False)
    except ValueError as err:
        logger.error("Error found: {0}".format(err), exc_info=False)
    except CanError as err:
        logger.error("Error found reading CAN response: {0}".format(err), exc_info=False)
    except NoData as err:
        logger.error("No data returned by OBDII: {0}".format(err), exc_info=False)
    except Exception as ex:
        logger.error("Unexpected error: {}".format(ex), exc_info=False)
    finally:
        publish_data_mqtt(mqtt_msgs)
        connection.close()
        logger.warning("===  Script end  ===")