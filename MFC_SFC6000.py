# import time
# import argparse
# from sensirion_shdlc_driver import ShdlcSerialPort
# from sensirion_shdlc_driver.errors import ShdlcDeviceError
# from sensirion_driver_adapters.shdlc_adapter.shdlc_channel import ShdlcChannel
# from sensirion_uart_sfx6xxx.device import Sfx6xxxDevice
# from sensirion_uart_sfx6xxx.commands import StatusCode

from sensirion_uart_sfx6xxx.device import Sfx6xxxDeviceBase
from sensirion_driver_adapters.shdlc_adapter.shdlc_channel import ShdlcChannel


import logging
import atexit
import time


"""
parser = argparse.ArgumentParser()
parser.add_argument('--serial-port', '-p', default='COM4')
args = parser.parse_args()

with ShdlcSerialPort(port=args.serial_port, baudrate=115200) as port:
    channel = ShdlcChannel(port)
    sensor = Sfx6xxxDevice(channel)
    sensor.device_reset()
    time.sleep(2.0)
    serial_number = sensor.get_serial_number()
    print(f"serial_number: {serial_number}; ")
    sensor.set_setpoint(2)
    for i in range(200):
        try:
            averaged_measured_value = sensor.read_averaged_measured_value(10)
            print(f"averaged_measured_value: {averaged_measured_value}; ")
        except ShdlcDeviceError as e:
            if e.error_code == StatusCode.SENSOR_MEASURE_LOOP_NOT_RUNNING_ERROR.value:
                print("Most likely the valve was closed due to overheating "
                      "protection.\nMake sure a flow is applied and start the "
                      "script again.")
                break
        except BaseException:
            continue
    sensor.close_valve()
"""

logging.basicConfig(level=logging.INFO)

class MFC_SFC6000:
    def __init__(self, port, analyte=None, retries=3):
        channel = ShdlcChannel(port)
        self._channel = channel
        self.analyte = analyte
        self.scaling = 0x02
        self.serial_port = None  # Ensure always initialized
        self.device = None
        ### self.unit maps to get_calibration_gas_units(index)
        # https://sensirion.github.io/python-uart-sfx6xxx/_modules/sensirion_uart_sfx6xxx/device.html#Sfx6xxxDeviceBase.get_calibration_gas_unit
        # Note: I am unsure what is wanted as the index, I assume it is the calibration gas unit index - Anthony Ly
        index = 0 # They said to look at the appendix but I don't see the appendix anywhere
        self.unit = Sfx6xxxDeviceBase.get_calibration_gas_unit(self, index)
        """
        self.unit = Sfc5xxxMediumUnit(
            Sfc5xxxUnitPrefix.MILLI,
            Sfc5xxxUnit.STANDARD_LITER,
            Sfc5xxxUnitTimeBase.MINUTE)
        """
        self.threshold = 5  # in sccm
        self.current_setpoint = 0

        success = self.try_open_port(retries)
        if not success:
            raise RuntimeError(f"Failed to open port {self.port} after {retries} attempts")

        self.sn = self.get_serial_number()
        self.device.set_user_defined_medium_unit(self.unit)

        if analyte:
            logging.info(f"MFC on port {self.port} with SN: {self.sn} is {analyte}")
        else:
            logging.info(f"MFC on port {self.port} has SN: {self.sn}")

        atexit.register(self.exit_procedure)
    
    # https://sensirion.github.io/python-uart-sfx6xxx/_modules/sensirion_uart_sfx6xxx/device.html#Sfx6xxxDeviceBase.get_serial_number
    def get_serial_number(self):
        serial_number = self.Sfx6xxxDeviceBase.get_serial_number()
        logging.debug(f'Device connected on port {self.port} has serial number: {serial_number}')
        return serial_number
    
    # https://sensirion.github.io/python-uart-sfx6xxx/_modules/sensirion_uart_sfx6xxx/device.html#Sfx6xxxDeviceBase.read_measured_value
    def get_current_flow_value(self):
        flow = self.Sfx6xxxDeviceBase.read_measured_value(scaling=self.scaling)
        logging.debug(f'Current Flow value for MFC on port {self.port} is {flow}')
        return flow
    
    # https://sensirion.github.io/python-uart-sfx6xxx/_modules/sensirion_uart_sfx6xxx/device.html#Sfx6xxxDeviceBase.set_setpoint
    def set_flow_rate(self, value):
        self.current_setpoint = value
        logging.debug(f'Setting the flow value to {value} sccm')
        try:
            self.Sfx6xxxDeviceBase.set_setpoint(self.current_setpoint, scaling=self.scaling)
        except Exception as e:
            logging.warning(f"MFC on port {self.port} with analyte {self.analyte} raised the following issue: {e}. Device status is {self.device.read_device_status()}")