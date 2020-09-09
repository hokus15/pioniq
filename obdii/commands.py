from obd import OBDCommand, OBDStatus
from obd.protocols import ECU
from obd.decoders import raw_string
from decoders import *

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
