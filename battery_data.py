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

# VIN decoder
def vin(can_message): 
    raw_vin = can_response(can_message)
    vin_str = ""
    for v in range(16, 33):
        vin_str = vin_str + chr(bytes_to_int(raw_vin[v:v+1]))
    return vin_str


# Publish all messages to MQTT
def publish_data_mqtt(msgs):
    try:
        logger.info("Publish messages to MQTT")
        for msg in msgs:
            logger.info("{}".format(msg))

        publish.multiple(msgs,
                    hostname=broker_address,
                    port=port,
                    client_id="battery-data-script",
                    keepalive=60,
                    will=None,
                    auth={'username':user, 'password':password},
                    tls={'tls_version':ssl.PROTOCOL_TLS},
                    protocol=mqtt.MQTTv311,
                    transport="tcp")
        logger.info("{} message(s) published to MQTT".format(len(msgs)))
    except Exception as err:
        logger.error("Error publishing to MQTT: {}".format(err), exc_info=False)

# main script
if __name__ == '__main__':
    logger = logging.getLogger('battery')
    
    console_handler = logging.StreamHandler() # sends output to stderr
    console_handler.setFormatter(logging.Formatter("%(asctime)s %(name)-10s %(levelname)-8s %(message)s"))
    console_handler.setLevel(logging.DEBUG)
    logger.addHandler(console_handler)
    
    file_handler = logging.handlers.TimedRotatingFileHandler(os.path.dirname(os.path.realpath(__file__)) + '/battery_data.log',
                                                    when='midnight',
                                                    backupCount=15) # sends output to battery_data.log file rotating it at midnight and storing latest 15 days
    file_handler.setFormatter(logging.Formatter("%(asctime)s %(name)-10s %(levelname)-8s %(message)s"))
    file_handler.setLevel(logging.INFO)
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
        logger.info("=== Script start ===")
        
        # Add state data to messages array
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
        cmd_can_receive_address_7ec = OBDCommand("ATCRA7EC",
                                            "Set the CAN receive address to 7EC",
                                            b"ATCRA7EC",
                                            0,
                                            raw_string,
                                            ECU.ALL,
                                            False)

        cmd_can_receive_address_7ea = OBDCommand("ATCRA7EA",
                                            "Set the CAN receive address to 7EA",
                                            b"ATCRA7EA",
                                            0,
                                            raw_string,
                                            ECU.ALL,
                                            False)

        cmd_can_filter_7ce = OBDCommand("ATCF7CE",
                                    "Set the CAN filter to 7CE",
                                    b"ATCF7CE",
                                    0,
                                    raw_string,
                                    ECU.ALL,
                                    False)
        
        cmd_can_mask_7ff = OBDCommand("ATCM7FF",
                                "Set the CAN mask to 7FF",
                                b"ATCM7FF",
                                0,
                                raw_string,
                                ECU.ALL,
                                False)
        
        cmd_2101 = OBDCommand("2101",
                            "2101 - Extended command - Battery information",
                            b"2101",
                            0,
                            can_response,
                            ECU.ALL,
                            False)

        cmd_2102 = OBDCommand("2102",
                            "2102 - Extended command - Battery information",
                            b"2102",
                            0,
                            can_response,
                            ECU.ALL,
                            False)

        cmd_2103 = OBDCommand("2103",
                            "2103 - Extended command - Battery information",
                            b"2103",
                            0,
                            can_response,
                            ECU.ALL,
                            False)

        cmd_2104 = OBDCommand("2104",
                            "2104 - Extended command - Battery information",
                            b"2104",
                            0,
                            can_response,
                            ECU.ALL,
                            False)

        cmd_2105 = OBDCommand("2105",
                            "2105 - Extended command - Battery information",
                            b"2105",
                            0,
                            can_response,
                            ECU.ALL,
                            False)
        
        cmd_odometer = OBDCommand("ODOMETER",
                            "22b002 - Extended command - Odometer information",
                            b"22b002",
                            0,
                            odometer,
                            ECU.ALL,
                            False,
                            "7C6")

        cmd_vin = OBDCommand("VIN",
                            "1A80 - Extended command - Vehicle Identification Number",
                            b"1A80",
                            0,
                            vin,
                            ECU.ALL,
                            False,
                            "7E2")

        # Add defined commands to supported commands
        connection.supported_commands.add(cmd_can_receive_address_7ec)
        connection.supported_commands.add(cmd_can_receive_address_7ea)
        connection.supported_commands.add(cmd_can_filter_7ce)
        connection.supported_commands.add(cmd_can_mask_7ff)
        connection.supported_commands.add(cmd_2101)
        connection.supported_commands.add(cmd_2102)
        connection.supported_commands.add(cmd_2103)
        connection.supported_commands.add(cmd_2104)
        connection.supported_commands.add(cmd_2105)
        connection.supported_commands.add(cmd_odometer)
        connection.supported_commands.add(cmd_vin)
    
        # Print supported commands
        # DTC = Diagnostic Trouble Codes
        # MIL = Malfunction Indicator Lamp
        logger.debug(connection.print_commands())
        
        logger.info("Querying for battery information")
        
        # Set the CAN receive address to 7EC
        connection.query(cmd_can_receive_address_7ec)
        
        # 2101 - 2105 codes to get battery status information
        raw_2101 = connection.query(cmd_2101)
        raw_2102 = connection.query(cmd_2102)
        raw_2103 = connection.query(cmd_2103)
        raw_2104 = connection.query(cmd_2104)
        raw_2105 = connection.query(cmd_2105)

        soh = bytes_to_int(raw_2105.value[27:29]) / 10.0

        # Only create battery status data if got a consistent Status Of Health (sometimes it's not consistent)
        if (soh <= 100):
            data_battery = {}
            chargingBits = raw_2101.value[11]
            dcBatteryCurrent = bytes_to_int(raw_2101.value[12:14]) / 10.0
            dcBatteryVoltage = bytes_to_int(raw_2101.value[14:16]) / 10.0
            
            cellTemps = [
                bytes_to_int(raw_2101.value[18:19]), #  0
                bytes_to_int(raw_2101.value[19:20]), #  1
                bytes_to_int(raw_2101.value[20:21]), #  2
                bytes_to_int(raw_2101.value[21:22]), #  3
                bytes_to_int(raw_2101.value[22:23]), #  4
                bytes_to_int(raw_2105.value[11:12]), #  5
                bytes_to_int(raw_2105.value[12:13]), #  6
                bytes_to_int(raw_2105.value[13:14]), #  7
                bytes_to_int(raw_2105.value[14:15]), #  8
                bytes_to_int(raw_2105.value[15:16]), #  9
                bytes_to_int(raw_2105.value[16:17]), # 10
                bytes_to_int(raw_2105.value[17:18])] # 11

            cellVoltages = []
            for cmd in [raw_2102, raw_2103, raw_2104]:
                for byte in range(6,38):
                    cellVoltages.append(cmd.value[byte] / 50.0)

             
            data_battery.update({
                'timestamp':                int(round(time.time())),
        
                'socBms':                  raw_2101.value[6] / 2.0,
                'socDisplay':              int(raw_2105.value[33] / 2.0),
                'soh':                      soh,

                'auxBatteryVoltage':        raw_2101.value[31] / 10.0,

                'charging':                 1 if chargingBits & 0x80 else 0,
                'normalChargePort':         1 if chargingBits & 0x20 else 0,
                'rapidChargePort':          1 if chargingBits & 0x40 else 0,

                'fanStatus':                raw_2101.value[29],
                'fanFeedback':              raw_2101.value[30],

                'cumulativeEnergyCharged':  bytes_to_int(raw_2101.value[40:44]) / 10.0,
                'cumulativeEnergyDischarged': bytes_to_int(raw_2101.value[44:48]) / 10.0,

                'cumulativeChargeCurrent':  bytes_to_int(raw_2101.value[32:36]) / 10.0,
                'cumulativeDischargeCurrent': bytes_to_int(raw_2101.value[36:40]) / 10.0,

                'availableChargePower':     bytes_to_int(raw_2101.value[7:9]) / 100.0,
                'availableDischargePower':  bytes_to_int(raw_2101.value[9:11]) / 100.0,

                'dcBatteryInletTemperature':  bytes_to_int(raw_2101.value[22:23]),
                'dcBatteryMaxTemperature':    bytes_to_int(raw_2101.value[16:17]),
                'dcBatteryMinTemperature':    bytes_to_int(raw_2101.value[17:18]),
                'dcBatteryCurrent':         dcBatteryCurrent,
                'dcBatteryPower':           dcBatteryCurrent * dcBatteryVoltage / 1000.0,
                'dcBatteryVoltage':         dcBatteryVoltage,
                'dcBatteryAvgTemperature':    sum(cellTemps) / len(cellTemps),

                'driveMotorSpeed':          bytes_to_int(raw_2101.value[55:57]) # In mph so convert to Km/h -> TODO check if its correct
                })
        
            for i,temp in enumerate(cellTemps):
                key = "dcBatteryModuleTemp{:02d}".format(i+1)
                data_battery[key] = float(temp)
    
            for i,cvolt in enumerate(cellVoltages):
                key = "dcBatteryCellVoltage{:02d}".format(i+1)
                data_battery[key] = float(cvolt)

            logger.info("Got battery information")

            try:
                logger.info("Querying for Vehicle Identification Number")
                # Set the CAN receive address to 7EA
                connection.query(cmd_can_receive_address_7ea)
                # Query VIN
                vin_value = connection.query(cmd_vin)
                logger.info("Got Vehicle Identification Number")
                if 'vin_value' in locals() and vin_value is not None and vin_value.value is not None:
                    data_battery['vin'] = vin_value.value
                else:
                    logger.warning("Vehicle Identification Number doesn't exist or is None")
            except (ValueError, CanError) as err:
                logger.warning("Error getting Vehicle Identification Number: {}".format(err), exc_info=False)


            # Add battery data messages array
            mqtt_msgs.extend([{'topic':topic_prefix + "battery", 'payload':json.dumps(data_battery), 'qos':0, 'retain':True}])
        else:
            logger.error("Got inconsistent data for battery Status Of Health: {}%".format(soh))

        try:
            logger.info("Querying for odometer")
            # Set the CAN receive address to 7EC
            connection.query(cmd_can_receive_address_7ec)
            # Sets the ID filter to 7EC
            connection.query(cmd_can_filter_7ce)
            # Sets the ID mask to 7FF
            connection.query(cmd_can_mask_7ff)
            # Query odometer
            odometer_value = connection.query(cmd_odometer)
        except (ValueError, CanError) as err:
            logger.warning("Error getting odometer value: {}".format(err), exc_info=False) # Not available when car engine is off

        # Only set odometer data if present
        if 'odometer_value' in locals() and odometer_value is not None and odometer_value.value is not None:
            logger.info("Got odometer value")
            # Add odometer data to messages array
            mqtt_msgs.extend([{'topic':topic_prefix + "odometer", 'payload':odometer_value.value, 'qos':0, 'retain':True}])
        else:
            logger.warning("Odometer value doesn't exist or is None")
    except ConnectionError as err:
        logger.error("OBDII connection error: {0}".format(err), exc_info=False)
    except ValueError as err:
        logger.error("Error found: {0}".format(err), exc_info=False)
    except CanError as err:
        logger.error("Error found reading CAN response: {0}".format(err), exc_info=False)
    except Exception as ex:
        logger.error("Unexpected error: {}".format(ex), exc_info=False)
    finally:
        publish_data_mqtt(mqtt_msgs)
        connection.close()
        logger.info("===  Script end  ===")
