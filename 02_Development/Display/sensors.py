import os
import random
from abc import ABC, abstractmethod
import time

from spl06_007 import PressureSensor
from sfm3300d import FlowSensor
from tca9548a import I2CMux
from process_sample_data import ProcessSampleData
from rpi_check import is_on_raspberry_pi
import constants


class SensorsABC(ABC):
    """A class to collect data from the sensing suit for the Tetra
    Ventillator Splitter.  If this class is not used on a Raspberry Pi,
    Then it will return data recorded from the sensors.
    """

    @abstractmethod
    def __init__(self):
        """Initializes self."""
        super().__init__()

    @abstractmethod
    def close(self):
        """Closes ever sensor in the system."""
        pass

    @abstractmethod
    def connected_sensors(self):
        """Returns a tuple of all the sensors connected to the system.

        Returns
        -------
        sensors : tuple
            A tuple of tuples of strings, where a string can be
            "SPL06-007" (representing the pressure sensor), "SFM3300-D"
            (representing the Sensirion sensor), or "Mass Air Flow"
            (representing the automotive sensor).  sensors[i] gives
            a tuple of all the sensors connected to port i of the 
            splitter.  sensors[constants.NUMBER_OF_PATIENTS + 1] will
            give the sensors connected for calibration of the whole
            system.  The output will look something like this:
                (("SPLO6-007", "SFM3300-D"), ("SPL06-007", "SFM3300-D"),
                 ("SPLO6-007", "SFM3300-D"), ("SPLO6-007", "SFM3300-D"),
                 ("SPLO6-007"))
        """
        pass

    @abstractmethod
    def tubes_with_enough_sensors(self):
        """Returns a list of the ports with both a pressure sensor and
        a flow sensor.

        Returns
        -------
        port_list : list
            A list of ints in range(constants.NUMBER_OF_PATIENTS)
            representing ports that have enough sensors.
        """
        pass

    @abstractmethod
    def calibration_pressure_sensor_connected(self):
        """Returns whether a fifth pressure sensor is connected for 
        calibration.

        Returns
        -------
        is_connected : bool
            True if a pressure sensor is connected on I2C port
            constants.CALIBRATION_PRESSURE_SENSOR_INDEX, else False.
        """
        pass

    @abstractmethod
    def poll(self):
        """Returns a tuple of tuples of sensor data.  The data is
        returned in the same shape and order as self.connected_sensors().

        Returns
        -------
        sensor_data : tuple
            A tuple of tuples of floats.  The value in self.poll()[i][j]
            corresponds to data from the sensor
            self.connected_sensors()[i][j].
        """
        pass


if is_on_raspberry_pi():

    
    class Sensors(SensorsABC):

        def __init__(self):
            self._pressure_mux = I2CMux(constants.PRESSURE_SENSOR_MUX_ADDRESS)
            self._pressure_sensors = []
            for i in range(constants.NUMBER_OF_PRESSURE_SENSORS):
                self._pressure_mux.select_channel(i)
                self._pressure_sensors.append(PressureSensor())
                self._pressure_sensors[i].set_sampling(
                    pressure_oversample=constants.PRESSURE_OVERSAMPLING,
                    pressure_sampling_rate=constants.PRESSURE_RATE,
                    temperature_oversample=constants.TEMPERATURE_OVERSAMPLING,
                    temperature_sampling_rate=constants.TEMPERATURE_RATE
                )
                self._pressure_sensors[i].set_op_mode(
                    PressureSensor.OpMode.background)

            self._flow_mux = I2CMux(constants.FLOW_SENSOR_MUX_ADDRESS)
            self._flow_sensors = []
            for i in range(constants.NUMBER_OF_SENSIRION_SENSORS):
                self._flow_mux.select_channel(i)
                print(f"i{i} {self._flow_mux.scan()}")
                self._flow_sensors.append(FlowSensor())

            self._mass_airflow_sensors = []
            for i in range(constants.NUMBER_OF_MASS_AIRFLOW_SENSORS):
                pass

        def close(self):
            
            for i in range(constants.NUMBER_OF_PRESSURE_SENSORS):
                self._pressure_mux.select_channel(i)
                self._pressure_sensors[i].close()
            for i in range(constants.NUMBER_OF_SENSIRION_SENSORS):
                self._flow_mux.select_channel(i)
                self._flow_sensors[i].close()
            for mass_airflow_sensor in self._mass_airflow_sensors:
                pass
            self._pressure_mux.close()
            self._flow_mux.close()

        def connected_sensors(self):
            def sensors_available_on_port(i):
                port_i = []
                self._pressure_mux.select_channel(i)
                if self._pressure_sensors[i].is_present():
                    port_i.append(constants.PRESSURE_SENSOR)
                if i < constants.NUMBER_OF_SENSIRION_SENSORS:
                    self._flow_mux.select_channel(i)
                    if self._flow_sensors[i].is_present():
                        print(f"{i} {self._flow_mux.scan()}")
                        print(f"{i} {self._flow_mux.scan()}")
                        port_i.append(constants.SENSIRION_SENSOR)
                # if mass airflow sensor is present, add that
                return tuple(port_i)
            
            return tuple(sensors_available_on_port(i)
                         for i in range(constants.MAX_SENSOR_COUNT))

        def tubes_with_enough_sensors(self):
            tubes = []
            sensors = self.connected_sensors()
            for i in range(len(sensors)):
                if (constants.PRESSURE_SENSOR in sensors[i]
                    and (constants.SENSIRION_SENSOR in sensors[i]
                         or constants.MASS_AIRFLOW_SENSOR in sensors[i])):
                    tubes.append(i)

            return tubes

        def calibration_pressure_sensor_connected(self):
            if (constants.PRESSURE_SENSOR in
                self.connected_sensors()[
                    constants.CALIBRATION_PRESSURE_SENSOR_INDEX]):
                return True
            else:
                return False

        def poll(self):
            sensors = self.connected_sensors()
            def sensor_data_on_port(i):
                data = []
                if constants.PRESSURE_SENSOR in sensors[i]:
                    data.append(self._pressure_sensors[i].pressure())
                if constants.SENSIRION_SENSOR in sensors[i]:
                    data.append(self._flow_sensors[i].flow())
                if constants.MASS_AIRFLOW_SENSOR in sensors[i]:
                    pass
                return data

            return tuple(sensor_data_on_port(i)
                         for i in range(constants.MAX_SENSOR_COUNT))


else:

    class Sensors(SensorsABC):

        def __init__(self):
            self._fake_data = (
                ProcessSampleData("TestData/20200609T2358Z_patrickData.txt"))
            self._data_index = 0

        def close(self):
            self._fake_data.close()

        def connected_sensors(self, not_enough_sensors=False):
            try:
                if (os.environ[constants.SENSOR_QUANTITY]
                        == constants.NOT_ENOUGH_SENSORS):
                    sensors = tuple([(constants.PRESSURE_SENSOR,)]
                                    + [(constants.PRESSURE_SENSOR,
                                        constants.SENSIRION_SENSOR)
                                       for _ in range(constants.
                                                      NUMBER_OF_PATIENTS-1)
                                       ])
                    raise NotEnoughSensors(
                        f"{len(self._tubes_with_enough_sensors(sensors))} "
                        "tube(s) do not have both a pressure sensor "
                        "and a flow sensor")

                elif (os.environ[constants.SENSOR_QUANTITY]
                      == constants.TOO_MANY_SENSORS):
                    return tuple([(constants.PRESSURE_SENSOR,
                                   constants.SENSIRION_SENSOR,
                                   constants.MASS_AIRFLOW_SENSOR)]
                                 + [(constants.PRESSURE_SENSOR,
                                     constants.SENSIRION_SENSOR)
                                    for _ in range(constants.
                                                   NUMBER_OF_PATIENTS-1)
                                    ])
            except KeyError:
                pass
            return tuple((constants.PRESSURE_SENSOR,
                          constants.SENSIRION_SENSOR)
                         for _ in range(constants.NUMBER_OF_PATIENTS))

        def tubes_with_enough_sensors(self):
            tubes = []
            sensors = self.connected_sensors()
            for i in range(len(sensors)):
                if (constants.PRESSURE_SENSOR in sensors[i]
                    and (constants.SENSIRION_SENSOR in sensors[i]
                         or constants.MASS_AIRFLOW_SENSOR in sensors[i])):
                    tubes.append(i)

            return tubes

        def calibration_pressure_sensor_connected(self, fail=False):
            if fail:
                return False
            else:
                return True

        def poll(self):
            """Pulls data from the pressure and flow sensors"""
<<<<<<< HEAD
            datum = tuple((self._fake_data.pressures[self._data_index],
                           self._fake_data.flow_rates[self._data_index])
                          for _ in range(constants.NUMBER_OF_PATIENTS))
            self._data_index += 1
            return datum
=======
            self._data_index += 1
            return tuple((self._fake_data.pressures[self._data_index-1],
                          self._fake_data.flow_rates[self._data_index-1])
                         for _ in range(constants.NUMBER_OF_PATIENTS))
>>>>>>> changed the sensors module so it will read data from a file when it's not run on a raspberry pi and added the start of a behave test to verify that the Docker image works.

        def _tubes_with_enough_sensors(self, tubes_sensors):
            tubes = []
            for tube in tubes_sensors:
                if (constants.PRESSURE_SENSOR in tube
                    and (constants.SENSIRION_SENSOR in tube
                         or constants.MASS_AIRFLOW_SENSOR in tube)):
                    tubes.append(tube)
            return tubes


class NotEnoughSensors(Exception):
    pass
