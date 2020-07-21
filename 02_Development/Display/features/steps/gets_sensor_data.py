import os
from behave import given, when, then

import server
from sensors import Sensors, NotEnoughSensors
import constants


@given("there is an object that represent the total sensing package")
def step_impl(context):
    os.environ[constants.SENSOR_QUANTITY] = constants.ENOUGH_SENSORS
    context.sensors = server.Sensors()


@when("these sensors are initialized")
def step_impl(context):
    pass


@then("the software will calibrate the sensors")
def step_impl(context):
    # context.sensors.calibrate()
    pass


@then("the software will determine which tubes have both pressure and "
      "airflow sensing")
def step_impl(context):
    number_of_good_tubes = len(context.sensors.tubes_with_enough_sensors())
    assert (number_of_good_tubes == constants.NUMBER_OF_PATIENTS), \
           ("Incorrect number of tubes.  "
            f"{constants.NUMBER_OF_PATIENTS} expected, "
            f"{number_of_good_tubes} received")


@then("the software will return the state of the sensor to the user.")
def step_impl(context):
    datum = context.sensors.poll()
    assert len(datum) == constants.NUMBER_OF_PATIENTS, \
        ("Not the correct number of data.  "
         f"{constants.NUMBER_OF_PATIENTS} expected, "
         f"{len(datum)} received.")


@given("any tube doesn't have a complete set of working sensors")
def step_impl(context):
    os.environ[constants.SENSOR_QUANTITY] = constants.NOT_ENOUGH_SENSORS


@when("the software diagnostic is run")
def step_impl(context):
    try:
        context.sensors.tubes_with_enough_sensors()
    except Exception as exception:
        context.exception = exception


@then("an exception {exception} will be raised")
def step_impl(context, exception):
    assert isinstance(context.exception, eval(exception)), \
        ("Invalid exception\n"
            f"{context.exception} received and {exception} expected")


@given("{sensor} sensor on a tube")
def step_impl(context, sensor):
    pass


@when("data is read")
def step_impl(context):
    pass


@then("the data from {sensor} will be used")
def step_impl(context, sensor):
    pass
