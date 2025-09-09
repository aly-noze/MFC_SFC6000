from sensirion_shdlc_driver.errors import ShdlcDeviceError
from sensirion_shdlc_driver import ShdlcSerialPort, ShdlcConnection
from sensirion_shdlc_sfc5xxx import Sfc5xxxShdlcDevice, Sfc5xxxScaling, \
    Sfc5xxxValveInputSource, Sfc5xxxUnitPrefix, Sfc5xxxUnit, \
    Sfc5xxxUnitTimeBase, Sfc5xxxMediumUnit
import logging
import atexit
from time import sleep

logging.basicConfig(level=logging.INFO)

class MFC:
    def __init__(self, port, analyte=None, retries=3):
        self.port = port
        self.analyte = analyte
        self.scaling = Sfc5xxxScaling.USER_DEFINED
        self.serial_port = None  # Ensure always initialized
        self.device = None
        self.unit = Sfc5xxxMediumUnit(
            Sfc5xxxUnitPrefix.MILLI,
            Sfc5xxxUnit.STANDARD_LITER,
            Sfc5xxxUnitTimeBase.MINUTE)
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

    def try_open_port(self, retries=3):
        for i in range(retries):
            try:
                self.serial_port = ShdlcSerialPort(port=self.port, baudrate=115200)
                connection = ShdlcConnection(self.serial_port)
                self.device = Sfc5xxxShdlcDevice(connection, slave_address=0)
                return True
            except Exception as e:
                logging.warning(f"Attempt {i+1} failed to open {self.port}: {e}")
                sleep(1)
        return False

    def get_serial_number(self):
        sn = self.device.get_serial_number()
        logging.debug(f'Device connected on port {self.port} has serial number: {sn}')
        return sn

    def get_current_flow_value(self):
        flow = self.device.read_measured_value(scaling=self.scaling)
        logging.debug(f'Current Flow value for MFC on port {self.port} is {flow}')
        return flow

    def set_flow_rate(self, value):
        self.current_setpoint = value
        logging.debug(f'Setting the flow value to {value} sccm')
        try:
            self.device.set_setpoint(self.current_setpoint, scaling=self.scaling)
        except Exception as e:
            logging.warning(f"MFC on port {self.port} with analyte {self.analyte} raised the following issue: {e}. Device status is {self.device.read_device_status()}")

    def ensure_flow_rate(self, value):
        logging.debug(f"Ensuring Flow rate for MFC on {self.port} is value: {value}")
        self.set_flow_rate(value=value)
        while abs(self.get_current_flow_value() - self.current_setpoint) > self.threshold:
            logging.warning(f'MFC on port {self.port} with analyte {self.analyte} flow rate is {self.get_current_flow_value()}. Set point is {self.current_setpoint}')
            sleep(0.1)

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

    def run_fixed_cycle(self, flow=100, duration=150):
        self.set_flow_rate(flow)
        sleep(duration)
        self.set_flow_rate(0)

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
        A = MFC("COM4", "Nitrogen")
        A.test_run()
    except KeyboardInterrupt:
        print("\nInterrupted by user.")
    except Exception as e:
        logging.error(f"Unexpected error: {e}")
    finally:
        if 'A' in locals():
            A.exit_procedure()
