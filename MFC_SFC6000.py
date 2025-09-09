# import time
# import argparse
# from sensirion_shdlc_driver import ShdlcSerialPort
# from sensirion_shdlc_driver.errors import ShdlcDeviceError
# from sensirion_driver_adapters.shdlc_adapter.shdlc_channel import ShdlcChannel
# from sensirion_uart_sfx6xxx.device import Sfx6xxxDevice
# from sensirion_uart_sfx6xxx.commands import StatusCode

from sensirion_uart_sfx6xxx.device import Sfx6xxxDeviceBase

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
        self.port = port
        self.analyte = analyte
        self.scaling = 0x02
        self.serial_port = None  # Ensure always initialized
        self.device = None
        ### self.unit maps to get_calibration_gas_units(index)
        # https://sensirion.github.io/python-uart-sfx6xxx/_modules/sensirion_uart_sfx6xxx/device.html#Sfx6xxxDeviceBase.get_calibration_gas_unit
        # Note: I am unsure what is wanted as the index, I assume it is the calibration gas unit index - Anthony Ly
        self.unit = Sfx6xxxDeviceBase.get_calibration_gas_unit(index = analyte)
        """
        self.unit = Sfc5xxxMediumUnit(
            Sfc5xxxUnitPrefix.MILLI,
            Sfc5xxxUnit.STANDARD_LITER,
            Sfc5xxxUnitTimeBase.MINUTE)
        """
        self.threshold = 10  # in sccm
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

    # Funtion to Monitor 
    def ensure_flow_rate(self, value):
        logging.debug(f"Ensuring Flow rate for MFC on {self.port} is value: {value}")
        self.set_flow_rate(value=value)
        while abs(self.get_current_flow_value() - self.current_setpoint) > self.threshold:
            logging.warning(f'MFC on port {self.port} with analyte {self.analyte} flow rate is {self.get_current_flow_value()}. Set point is {self.current_setpoint}')
            time.sleep(0.1)

    # Test Run with Keyboard Controls (0 -> Off, 1 -> On, 999 -> Exit)
    def test_run(self):
        val = 0
        while val != 999:
            try:
                val = int(input('Type in 0 to turn off, 1 to turn on, 999 to exit the system: '))
                if val == 999:
                    break
                else:
                    self.ensure_flow_rate(val)
            except ValueError:
                print("Invalid input. Please enter a number.")
        self.exit_procedure()

    # Test Run with Flow = 100 and Duration = 150
    def run_fixed_cycle(self, flow=100, duration=150):
        self.set_flow_rate(flow)
        time.sleep(duration)
        self.set_flow_rate(0)

    # To Exit
    def exit_procedure(self):
        try:
            if self.device:
                print("bingo")
                self.set_flow_rate(0)
                print("boom")
                logging.info("Exiting the system")
        except Exception as e:
            logging.warning(f"Exception during exit: {e}")
        finally:
            if self.serial_port:
                try:
                    self.serial_port.close()
                    logging.info(f"Closed serial port {self.port}")
                except Exception as e:
                    logging.warning(f"Error closing port {self.port}: {e}")
                self.serial_port = None

if __name__ == "__main__":
    try:
        A = MFC_SFC6000("COM8", "Nitrogen")
        A.test_run()
    except KeyboardInterrupt:
        print("\nInterrupted by user.")
    except Exception as e:
        logging.error(f"Unexpected error: {e}")
    finally:
        if 'A' in locals():
            A.exit_procedure()