from obd import OBDCommand
from obd.protocols import ECU
from obd.decoders import raw_string
from decoders import bms_2101, cell_voltages, bms_2105, odometer, vin
from decoders import vmcu, tpms, external_temperature

# flake8: noqa

ext_commands = {
#                                          name                       description                                            cmd        bytes decoder               ECU         fast
    'CAN_HEADER_7E4':          OBDCommand("CAN_HEADER_7E4",          "Set CAN module ID to 7E4 - BMS battery information"  , b"ATSH7E4" ,  0, raw_string          , ECU.UNKNOWN, False),
    'CAN_HEADER_7C6':          OBDCommand("CAN_HEADER_7C6",          "Set CAN module ID to 7C6 - Odometer information"     , b"ATSH7C6" ,  0, raw_string          , ECU.UNKNOWN, False),
    'CAN_HEADER_7E2':          OBDCommand("CAN_HEADER_7E2",          "Set CAN module ID to 7E2 - VMCU information"         , b"ATSH7E2" ,  0, raw_string          , ECU.UNKNOWN, False),
    'CAN_HEADER_7A0':          OBDCommand("CAN_HEADER_7A0",          "Set CAN module ID to 7A0 - TPMS information"         , b"ATSH7A0" ,  0, raw_string          , ECU.UNKNOWN, False),
    'CAN_HEADER_7E6':          OBDCommand("CAN_HEADER_7E6",          "Set CAN module ID to 7E6 - External temp information", b"ATSH7E6" ,  0, raw_string          , ECU.UNKNOWN, False),

    'CAN_RECEIVE_ADDRESS_7EC': OBDCommand("CAN_RECEIVE_ADDRESS_7EC", "Set the CAN receive address to 7EC"                  , b"ATCRA7EC",  0, raw_string          , ECU.UNKNOWN, False),
    'CAN_RECEIVE_ADDRESS_7EA': OBDCommand("CAN_RECEIVE_ADDRESS_7EA", "Set the CAN receive address to 7EA"                  , b"ATCRA7EA",  0, raw_string          , ECU.UNKNOWN, False),
    'CAN_RECEIVE_ADDRESS_7A8': OBDCommand("CAN_RECEIVE_ADDRESS_7A8", "Set the CAN receive address to 7A8"                  , b"ATCRA7A8",  0, raw_string          , ECU.UNKNOWN, False),
    'CAN_RECEIVE_ADDRESS_7EE': OBDCommand("CAN_RECEIVE_ADDRESS_7EE", "Set the CAN receive address to 7EE"                  , b"ATCRA7EE",  0, raw_string          , ECU.UNKNOWN, False),

    'CAN_FILTER_7CE':          OBDCommand("CAN_FILTER_7CE",          "Set the CAN filter to 7CE"                           , b"ATCF7CE" ,  0, raw_string          , ECU.UNKNOWN, False),

    'BMS_2101':                OBDCommand("BMS_2101",                "Extended command - BMS Battery information"          , b"2101"    , 61, bms_2101            , ECU.ALL    , False),
    'BMS_2102':                OBDCommand("BMS_2102",                "Extended command - BMS Battery information"          , b"2102"    , 38, cell_voltages       , ECU.ALL    , False),
    'BMS_2103':                OBDCommand("BMS_2103",                "Extended command - BMS Battery information"          , b"2103"    , 38, cell_voltages       , ECU.ALL    , False),
    'BMS_2104':                OBDCommand("BMS_2104",                "Extended command - BMS Battery information"          , b"2104"    , 38, cell_voltages       , ECU.ALL    , False),
    'BMS_2105':                OBDCommand("BMS_2105",                "Extended command - BMS Battery information"          , b"2105"    , 45, bms_2105            , ECU.ALL    , False),

    'ODOMETER_22B002':         OBDCommand("ODOMETER_22B002",         "Extended command - Odometer information"             , b"22b002"  , 15, odometer            , ECU.ALL    , False),
    'VIN_1A80':                OBDCommand("VIN_1A80",                "Extended command - Vehicle Identification Number"    , b"1A80"    , 99, vin                 , ECU.ALL    , False),
    'VMCU_2101':               OBDCommand("VMCU_2101",               "Extended command - VMCU information"                 , b"2101"    , 22, vmcu                , ECU.ALL    , False),
    'TPMS_22C00B':             OBDCommand("TPMS_22C00B",             "Extended command - TPMS information"                 , b"22C00B"  , 23, tpms                , ECU.ALL    , False),
    'EXT_TEMP_2180':           OBDCommand("EXT_TEMP_2180",           "Extended command - External temperature"             , b"2180"    , 25, external_temperature, ECU.ALL    , False)
}
