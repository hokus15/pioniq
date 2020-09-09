from obd.utils import bytes_to_int
from utils import bytes_to_int_signed

def external_temperature(messages):
    """External temperature decoder."""
    d = messages[0].data
    return dict(external_temperature=(d[14] - 80) / 2.0)  # C


def vin(messages):
    """VIN decoder."""
    d = messages[0].data
    vin_str = ""
    for v in range(16, 33):
        vin_str = vin_str + chr(bytes_to_int(d[v:v + 1]))
    return dict(vin=vin_str)


def odometer(messages):
    """Odometer decoder."""
    d = messages[0].data
    if len(d) == 0:
        return None
    else:
        return dict(odometer=bytes_to_int(d[9:12]))  # Km


def tpms(messages):
    """TPMS decoder."""
    d = messages[0].data
    return dict(tire_fl_pressure=round((d[7] * 0.2) / 14.504, 1),  # bar - Front Left
                tire_fl_temperature=d[8] - 55,  # C   - Front Left

                tire_fr_pressure=round((d[11] * 0.2) / 14.504, 1),  # bar - Front Right
                tire_fr_temperature=d[12] - 55,  # C   - Front Right

                tire_bl_pressure=round((d[19] * 0.2) / 14.504, 1),  # bar - Back Left
                tire_bl_temperature=d[20] - 55,  # C   - Back Left

                tire_br_pressure=round((d[15] * 0.2) / 14.504, 1),  # bar - Back Right
                tire_br_temperature=d[16] - 55  # C   - Back Right
                )


def vmcu(messages):
    """VMCU decoder."""
    d = messages[0].data

    gear_str = ""
    gear_bits = d[7]
    if gear_bits & 0x1:  # 1st bit is 1
        gear_str = gear_str + "P"
    if gear_bits & 0x2:  # 2nd bit is 1
        gear_str = gear_str + "R"
    if gear_bits & 0x4:  # 3rd bit is 1
        gear_str = gear_str + "N"
    if gear_bits & 0x8:  # 4th bit is 1
        gear_str = gear_str + "D"

    brakes_bits = d[8]

    return dict(gear=gear_str,
                speed=(((d[16] * 256) + d[15]) / 100.0) * 1.60934,  # kmh. Multiplied by 1.60934 to convert mph to kmh
                accel_pedal_depth=d[16] / 2,  # %
                brake_lamp=1 if brakes_bits & 0x1 else 0,  # 1st bit is 1
                brakes_on=0 if brakes_bits & 0x2 else 1  # 2nd bit is 0
                )


def bms_2101(messages):
    """BMS 2101 decoder."""
    d = messages[0].data

    charging_bits = d[11]
    charging = 1 if charging_bits & 0x80 else 0  # 8th bit is 1

    battery_current = bytes_to_int_signed(d[12:14]) / 10.0
    battery_voltage = bytes_to_int(d[14:16]) / 10.0

    return dict(socBms=d[6] / 2.0,  # %
                bmsIgnition=1 if d[52] & 0x4 else 0,  # 3rd bit is 1
                bmsMainRelay=1 if charging_bits & 0x1 else 0,  # 1st bit is 1
                auxBatteryVoltage=d[31] / 10.0,  # V

                charging=charging,
                normalChargePort=1 if charging_bits & 0x20 else 0,  # 6th bit is 1
                rapidChargePort=1 if charging_bits & 0x40 else 0,  # 7th bit is 1
                fanStatus=d[29],  # Hz
                fanFeedback=d[30],
                cumulativeEnergyCharged=bytes_to_int(d[40:44]) / 10.0,  # kWh
                cumulativeEnergyDischarged=bytes_to_int(d[44:48]) / 10.0,  # kWh

                cumulativeChargeCurrent=bytes_to_int(d[32:36]) / 10.0,  # A
                cumulativeDischargeCurrent=bytes_to_int(d[36:40]) / 10.0,  # A

                cumulativeOperatingTime=bytes_to_int(d[48:52]),  # seconds

                availableChargePower=bytes_to_int(d[7:9]) / 100.0,  # kW
                availableDischargePower=bytes_to_int(d[9:11]) / 100.0,  # kW

                dcBatteryInletTemperature=bytes_to_int_signed(d[22:23]),  # C
                dcBatteryMaxTemperature=bytes_to_int_signed(d[16:17]),  # C
                dcBatteryMinTemperature=bytes_to_int_signed(d[17:18]),  # C
                dcBatteryCellMaxVoltage=d[25] / 50,  # V
                dcBatteryCellNoMaxVoltage=d[26],
                dcBatteryCellMinVoltage=d[27] / 50,  # V
                dcBatteryCellNoMinVoltage=d[28],
                dcBatteryCurrent=battery_current,  # A
                dcBatteryPower=round(battery_current * battery_voltage / 1000.0, 3),  # kW
                dcBatteryVoltage=battery_voltage,  # V

                driveMotorSpeed=bytes_to_int_signed(d[55:57]),  # RPM

                dcBatteryModuleTemp01=bytes_to_int_signed(d[18:19]),  # C
                dcBatteryModuleTemp02=bytes_to_int_signed(d[19:20]),  # C
                dcBatteryModuleTemp03=bytes_to_int_signed(d[20:21]),  # C
                dcBatteryModuleTemp04=bytes_to_int_signed(d[21:22]),  # C
                dcBatteryModuleTemp05=bytes_to_int_signed(d[22:23]),  # C
                )


def bms_2105(messages):
    """BMS 2105 decoder."""
    d = messages[0].data

    return dict(soh=bytes_to_int(d[27:29]) / 10.0,  # %
                dcBatteryCellMaxDeterioration=bytes_to_int(d[27:29]) / 10.0,  # %
                dcBatteryCellMinDeterioration=bytes_to_int(d[30:32]) / 10.0,  # %
                socDisplay=int(d[33] / 2.0),  # %
                dcBatteryModuleTemp06=bytes_to_int_signed(d[11:12]),  # C
                dcBatteryModuleTemp07=bytes_to_int_signed(d[12:13]),  # C
                dcBatteryModuleTemp08=bytes_to_int_signed(d[13:14]),  # C
                dcBatteryModuleTemp09=bytes_to_int_signed(d[14:15]),  # C
                dcBatteryModuleTemp10=bytes_to_int_signed(d[15:16]),  # C
                dcBatteryModuleTemp11=bytes_to_int_signed(d[16:17]),  # C
                dcBatteryModuleTemp12=bytes_to_int_signed(d[17:18]),  # C
                dcBatteryCellVoltageDeviation=d[22] / 50,  # V
                dcBatteryHeater1Temperature=float(d[25]),  # C
                dcBatteryHeater2Temperature=float(d[26]),  # C
                dcBatteryCellNoMaxDeterioration=int(d[29]),
                dcBatteryCellNoMinDeterioration=int(d[32]),
                )


def cell_voltages(messages):
    """Cell voltages decoder."""
    d = messages[0].data
    cell_voltages = []
    for byte in range(6, 38):
        cell_voltages.append(d[byte] / 50.0)
    return cell_voltages
