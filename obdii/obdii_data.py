#!/usr/bin/env python3

import ssl
import time
import json
import os
import logging
import logging.handlers
import paho.mqtt.publish as publish
import paho.mqtt.client as mqtt
import obd
from obd import OBDCommand, OBDStatus
from obd.protocols import ECU
from obd.decoders import raw_string
from obd.utils import bytes_to_int
from decoders import *


class OBDIIConnectionError(Exception):
    pass


class CanError(Exception):
    pass


def obd_connect(portstr, baudrate, fast=False, timeout=30, max_attempts=3):
    connection_count = 0
    obd_connection = None
    while (obd_connection is None or obd_connection.status() != OBDStatus.CAR_CONNECTED) and connection_count < max_attempts:
        connection_count += 1
        # Establish connection with OBDII dongle
        obd_connection = obd.OBD(portstr=portstr,
                                 baudrate=baudrate,
                                 fast=fast,
                                 timeout=timeout)
        if (obd_connection is None or obd_connection.status() != OBDStatus.CAR_CONNECTED) and connection_count < max_attempts:
            logger.warning("{}. Retrying in {} second(s)...".format(obd_connection.status(), connection_count))
            time.sleep(connection_count)

    if obd_connection.status() != OBDStatus.CAR_CONNECTED:
        raise OBDIIConnectionError(obd_connection.status())
    else:
        return obd_connection


def query_command(command, max_attempts=3):
    command_count = 0
    cmd_response = None
    exception = False
    valid_response = False
    while not valid_response and command_count < max_attempts:
        command_count += 1
        try:
            cmd_response = connection.query(command, force=True)
        except Exception:
            exception = True
        valid_response = not(cmd_response is None or cmd_response.value == "?" or cmd_response.value == "NO DATA" or cmd_response.value == "" or cmd_response.value is None or exception)
        if not valid_response and command_count < max_attempts:
            logger.warning("No valid response for {}. Retrying in {} second(s)...".format(command, command_count))
            time.sleep(command_count)

    if not valid_response:
        raise ValueError("No valid response for {}. Max attempts ({}) exceeded."
                         .format(command, max_attempts))
    else:
        logger.info("Got response from command: {} ".format(command))
        return cmd_response


def query_battery_info():
    logger.info("**** Querying battery information ****")
    battery_info = {}
    # Set header to 7E4
    query_command(can_header_7e4)
    # Set the CAN receive address to 7EC
    query_command(can_receive_address_7ec)

    # 2101 - 2105 codes to get battery status information
    bms_2101_resp = query_command(bms_2101)
    bms_2102_resp = query_command(bms_2102)
    bms_2103_resp = query_command(bms_2103)
    bms_2104_resp = query_command(bms_2104)
    bms_2105_resp = query_command(bms_2105)

    # Extract status of health value from corresponding response
    soh = bms_2105_resp.value["soh"]

    # Only create battery status data if got a consistent
    # Status Of Health (sometimes it's not consistent)
    if soh <= 100:
        charging = bms_2101_resp.value["charging"]

        battery_current = bms_2101_resp.value["dcBatteryCurrent"]
        battery_voltage = bms_2101_resp.value["dcBatteryVoltage"]

        battery_cell_max_deterioration = bms_2105_resp.value["dcBatteryCellMaxDeterioration"]
        battery_cell_min_deterioration = bms_2105_resp.value["dcBatteryCellMinDeterioration"]
        soc_display = bms_2105_resp.value["socDisplay"]

        mins_to_complete = 0

        # Calculate time to fully charge (only when charging)
        if charging == 1:
            battery_capacity = config['vehicle']['battery_capacity']
            average_deterioration = (battery_cell_max_deterioration + battery_cell_min_deterioration) / 2.0
            lost_soh = 100 - average_deterioration
            lost_wh = ((battery_capacity * 1000) * lost_soh) / 100
            remaining_pct = 100 - soc_display
            remaining_wh = (((battery_capacity * 1000) - lost_wh) * remaining_pct) / 100
            charge_power = abs((battery_current * battery_voltage))
            mins_to_complete = int((remaining_wh / charge_power) * 60)

        battery_info.update({'timestamp': int(round(bms_2105_resp.time))})
        battery_info.update({'minsToCompleteCharge': mins_to_complete})
        battery_info.update(bms_2101_resp.value)
        battery_info.update(bms_2105_resp.value)

        # Battery average temperature
        module_temps = []
        for i in range(1, 12):
            module_temps.append(battery_info["dcBatteryModuleTemp{:02d}".format(i)])
        battery_info.update({'dcBatteryAvgTemperature': round(sum(module_temps) / len(module_temps), 1)})

        # Cell voltages
        cell_voltages = bms_2102_resp.value + bms_2103_resp.value + bms_2104_resp.value
        for i, cvolt in enumerate(cell_voltages):
            key = "dcBatteryCellVoltage{:02d}".format(i + 1)
            battery_info[key] = float(cvolt)

        logger.info("**** Got battery information ****")
    else:
        raise ValueError("Got inconsistent data for battery Status Of Health: {}%"
                         .format(soh))

    # Return exception when empty dict
    if not bool(battery_info):
        raise ValueError("Could not get battery information")
    else:
        return battery_info


def query_odometer_info():
    logger.info("**** Querying odometer ****")
    odometer_info = {}
    # Set header to 7C6
    query_command(can_header_7c6)
    # Set the CAN receive address to 7EC
    query_command(can_receive_address_7ec)
    # Sets the ID filter to 7CE
    query_command(can_filter_7ce)
    # Query odometer
    odometer_resp = query_command(odometer_22b002)

    # Only set odometer data if present.
    # Not available when car engine is off
    if not odometer_resp.is_null():
        odometer_info.update({'timestamp': int(round(odometer_resp.time))})
        odometer_info.update(odometer_resp.value)
    else:
        logger.warning("Could not get odometer information")

    # Return exception when empty dict
    if not bool(odometer_info):
        raise ValueError("Could not get odometer information")
    else:
        return odometer_info


def query_vmcu_info():
    logger.info("**** Querying VMCU ****")
    vmcu_info = {}
    # Set header to 7E2
    query_command(can_header_7e2)
    # Set the CAN receive address to 7EA
    query_command(can_receive_address_7ea)

    # VIN
    vin_resp = query_command(vin_1a80)
    # Add vin to vmcu info
    if not vin_resp.is_null():
        vmcu_info.update(vin_resp.value)
    else:
        logger.warning("Could not get VIN")

    # VMCU
    vmcu_2101_resp = query_command(vmcu_2101)
    if not vmcu_2101_resp.is_null():
        vmcu_info.update({'timestamp': int(round(vmcu_2101_resp.time))})
        vmcu_info.update(vmcu_2101_resp.value)
    else:
        logger.warning("Could not get VMCU information")

    # Return exception when empty dict
    if not bool(vmcu_info):
        raise ValueError("Could not get VMCU information")
    else:
        return vmcu_info


def query_tpms_info():
    logger.info("**** Querying for TPMS information ****")
    tpms_info = {}
    # Set the CAN receive address to 7A8
    query_command(can_receive_address_7a8)
    # Set header to 7A0
    query_command(can_header_7a0)
    # Query TPMS
    tpms_22c00b_resp = query_command(tpms_22c00b)

    if not tpms_22c00b_resp.is_null():
        tpms_info.update({'timestamp': int(round(tpms_22c00b_resp.time))})
        tpms_info.update(tpms_22c00b_resp.value)
    else:
        logger.warning("Could not get TPMS information")

    # Return exception when empty dict
    if not bool(tpms_info):
        raise ValueError("Could not get TPMS information")
    else:
        return tpms_info


def query_external_temperature_info():
    logger.info("**** Querying for external temperature ****")
    external_temperature_info = {}
    # Set header to 7E6
    query_command(can_header_7e6)
    # Set the CAN receive address to 7EC
    query_command(can_receive_address_7ee)
    # Query external temeprature
    ext_temp_resp = query_command(ext_temp_2180)

    # Only set temperature data if present.
    if not ext_temp_resp.is_null():
        external_temperature_info.update({'timestamp': int(round(ext_temp_resp.time))})
        external_temperature_info.update(ext_temp_resp.value)  # C
    else:
        logger.warning("Could not get external temperature information")

    # Return exception when empty dict
    if not bool(external_temperature_info):
        raise ValueError("Could not get external temperature information")
    else:
        return external_temperature_info


def publish_data_mqtt(msgs):
    """Publish all messages to MQTT."""
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
                         auth={'username': user, 'password': password},
                         tls={'tls_version': ssl.PROTOCOL_TLS},
                         protocol=mqtt.MQTTv311,
                         transport="tcp"
                         )
        logger.info("{} message(s) published to MQTT".format(len(msgs)))
    except Exception as err:
        logger.error("Error publishing to MQTT: {}".format(err), exc_info=False)


if __name__ == '__main__':
    logger = logging.getLogger('obdii')

    console_handler = logging.StreamHandler()  # sends output to stderr
    console_handler.setFormatter(logging.Formatter("%(asctime)s %(name)-10s %(levelname)-8s %(message)s"))
    console_handler.setLevel(logging.DEBUG)
    logger.addHandler(console_handler)

    file_handler = logging.handlers.TimedRotatingFileHandler(os.path.dirname(os.path.realpath(__file__)) + '/../obdii_data.log',
                                                             when='midnight',
                                                             backupCount=15
                                                             )  # sends output to obdii_data.log file rotating it at midnight and storing latest 15 days
    file_handler.setFormatter(logging.Formatter("%(asctime)s %(name)-10s %(levelname)-8s %(message)s"))
    file_handler.setLevel(logging.INFO)
    logger.addHandler(file_handler)

    logger.setLevel(logging.DEBUG)

    with open(os.path.dirname(os.path.realpath(__file__)) + '/obdii_data.config.json') as config_file:
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
        state_info = {
            'timestamp': int(round(time.time())),
            'state': 'running'
        }
        mqtt_msgs.extend([{'topic': topic_prefix + "state",
                           'payload': json.dumps(state_info),
                           'qos': 0,
                           'retain': True}]
                         )

        obd.logger.setLevel(obd.logging.DEBUG)
        # Remove obd logger existing handlers
        for handler in obd.logger.handlers[:]:
            obd.logger.removeHandler(handler)
        # Add handlers to obd logger
        obd.logger.addHandler(console_handler)
        obd.logger.addHandler(file_handler)

        connection = obd_connect(portstr=config['serial']['port'],
                                 baudrate=int(config['serial']['baudrate']),
                                 fast=False,
                                 timeout=30)

        can_header_7e4 = OBDCommand("ATSH7E4",
                                    "Set CAN module ID to 7E4 - BMS battery information",
                                    b"ATSH7E4",
                                    0,
                                    raw_string,
                                    ECU.ALL,
                                    False)

        can_header_7c6 = OBDCommand("ATSH7C6",
                                    "Set CAN module ID to 7C6 - Odometer information",
                                    b"ATSH7C6",
                                    0,
                                    raw_string,
                                    ECU.ALL,
                                    False)

        can_header_7e2 = OBDCommand("ATSH7E2",
                                    "Set CAN module ID to 7E2 - VMCU information",
                                    b"ATSH7E2",
                                    0,
                                    raw_string,
                                    ECU.ALL,
                                    False)

        can_header_7a0 = OBDCommand("ATSH7A0",
                                    "Set CAN module ID to 7A0 - TPMS information",
                                    b"ATSH7A0",
                                    0,
                                    raw_string,
                                    ECU.ALL,
                                    False)

        can_header_7e6 = OBDCommand("ATSH7E6",
                                    "Set CAN module ID to 7E6 - External temp information",
                                    b"ATSH7E6",
                                    0,
                                    raw_string,
                                    ECU.ALL,
                                    False)

        can_receive_address_7ec = OBDCommand("ATCRA7EC",
                                             "Set the CAN receive address to 7EC",
                                             b"ATCRA7EC",
                                             0,
                                             raw_string,
                                             ECU.ALL,
                                             False)

        can_receive_address_7ea = OBDCommand("ATCRA7EA",
                                             "Set the CAN receive address to 7EA",
                                             b"ATCRA7EA",
                                             0,
                                             raw_string,
                                             ECU.ALL,
                                             False)

        can_receive_address_7a8 = OBDCommand("ATCRA7A8",
                                             "Set the CAN receive address to 7A8",
                                             b"ATCRA7A8",
                                             0,
                                             raw_string,
                                             ECU.ALL,
                                             False)

        can_receive_address_7ee = OBDCommand("ATCRA7EE",
                                             "Set the CAN receive address to 7EE",
                                             b"ATCRA7EE",
                                             0,
                                             raw_string,
                                             ECU.ALL,
                                             False)

        can_filter_7ce = OBDCommand("ATCF7CE",
                                    "Set the CAN filter to 7CE",
                                    b"ATCF7CE",
                                    0,
                                    raw_string,
                                    ECU.ALL,
                                    False)

        bms_2101 = OBDCommand("2101",
                              "Extended command - BMS Battery information",
                              b"2101",
                              0,  # 61
                              bms_2101,
                              ECU.ALL,
                              False)

        bms_2102 = OBDCommand("2102",
                              "Extended command - BMS Battery information",
                              b"2102",
                              0,  # 38
                              cell_voltages,
                              ECU.ALL,
                              False)

        bms_2103 = OBDCommand("2103",
                              "Extended command - BMS Battery information",
                              b"2103",
                              0,  # 38
                              cell_voltages,
                              ECU.ALL,
                              False)

        bms_2104 = OBDCommand("2104",
                              "Extended command - BMS Battery information",
                              b"2104",
                              0,  # 38
                              cell_voltages,
                              ECU.ALL,
                              False)

        bms_2105 = OBDCommand("2105",
                              "Extended command - BMS Battery information",
                              b"2105",
                              0,  # 45
                              bms_2105,
                              ECU.ALL,
                              False)

        odometer_22b002 = OBDCommand("22b002",
                                     "Extended command - Odometer information",
                                     b"22b002",
                                     0,  # 15
                                     odometer,
                                     ECU.ALL,
                                     False)

        vin_1a80 = OBDCommand("1A80",
                              "Extended command - Vehicle Identification Number",
                              b"1A80",
                              0,  # 99
                              vin,
                              ECU.ALL,
                              False)

        vmcu_2101 = OBDCommand("2101",
                               "Extended command - VMCU information",
                               b"2101",
                               0,  # 22
                               vmcu,
                               ECU.ALL,
                               False)

        tpms_22c00b = OBDCommand("22C00B",
                                 "Extended command - TPMS information",
                                 b"22C00B",
                                 0,  # 23
                                 tpms,
                                 ECU.ALL,
                                 False)

        ext_temp_2180 = OBDCommand("2180",
                                   "Extended command - External temperature",
                                   b"2180",
                                   0,  # 25
                                   external_temperature,
                                   ECU.ALL,
                                   False)

        # Print supported commands
        # DTC = Diagnostic Trouble Codes
        # MIL = Malfunction Indicator Lamp
        logger.debug(connection.print_commands())

        try:
            # Add battery information to MQTT messages array
            mqtt_msgs.extend([{'topic': topic_prefix + "battery",
                               'payload': json.dumps(query_battery_info()),
                               'qos': 0,
                               'retain': True}])
        except (ValueError, CanError) as err:
            logger.warning("**** Error querying battery information: {} ****"
                           .format(err), exc_info=False)

        try:
            # Add VMCU information to MQTT messages array
            mqtt_msgs.extend([{'topic': topic_prefix + "vmcu",
                               'payload': json.dumps(query_vmcu_info()),
                               'qos': 0,
                               'retain': True}])
        except (ValueError, CanError) as err:
            logger.warning("**** Error querying vmcu information: {} ****"
                           .format(err), exc_info=False)

        try:
            # Add Odometer to MQTT messages array
            mqtt_msgs.extend([{'topic': topic_prefix + "odometer",
                               'payload': json.dumps(query_odometer_info()),
                               'qos': 0,
                               'retain': True}])
        except (ValueError, CanError) as err:
            logger.warning("**** Error querying odometer: {} ****".format(err),
                           exc_info=False)

        try:
            # Add TPMS information to MQTT messages array
            mqtt_msgs.extend([{'topic': topic_prefix + "tpms",
                               'payload': json.dumps(query_tpms_info()),
                               'qos': 0,
                               'retain': True}])
        except (ValueError, CanError) as err:
            logger.warning("**** Error querying tpms information: {} ****"
                           .format(err),
                           exc_info=False)

        try:
            # Add external temperture information to MQTT messages array
            mqtt_msgs.extend([{'topic': topic_prefix + "ext_temp",
                               'payload': json.dumps(query_external_temperature_info()),
                               'qos': 0,
                               'retain': True}])
        except (ValueError, CanError) as err:
            logger.warning("**** Error querying external temperature information: {} ****"
                           .format(err),
                           exc_info=False)

    except OBDIIConnectionError as err:
        logger.error("OBDII connection error: {0}".format(err),
                     exc_info=False)
    except ValueError as err:
        logger.error("Error found: {0}".format(err),
                     exc_info=False)
    except CanError as err:
        logger.error("Error found reading CAN response: {0}".format(err),
                     exc_info=False)
    except Exception as ex:
        logger.error("Unexpected error: {}".format(ex),
                     exc_info=True)
    finally:
        publish_data_mqtt(mqtt_msgs)
        if 'connection' in locals() and connection is not None:
            connection.close()
        logger.info("===  Script end  ===")
