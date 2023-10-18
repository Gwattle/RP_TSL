import time
import sys
import logging
import os

from ..error_handling.error_handling import exception_handler, formatter
from ..redpitaya import redpitaya_scpi as scpi
from ..redpitaya import redpitaya as rp
from . import tsl
from ..get_address import get_address_IL

filename = os.path.basename(__file__)
filename = os.path.splitext(filename)[0]
if not os.path.exists("./logs"):
    os.mkdir("./logs")

logger = logging.getLogger(filename)
handler = logging.FileHandler(f"./logs/{filename}.log")

handler.setLevel(logging.DEBUG)
logger.setLevel(logging.DEBUG)

handler.setFormatter(formatter)
logger.addHandler(handler)

__author__ = "Andrew Kruger"

BUFFER_SIZE = 16384       # Red Pitaya buffer size

rp_s = scpi.scpi(sys.argv[1])
_RP = rp.ACQ(rp_s)

_TSL = tsl.TSL(get_address_IL(), "\r\n", "\r\n")
_STS = tsl.STS(_TSL)
_TRIG = tsl.TRIGGER(_TSL)

def set_wavelength(wavelength: str | int | float):
    """Sets the current wavlength of the TSL.
    
    ### Parameters
        wavelength : str | int | float
            The wavelength to set the TSL to.
    """
    _TSL.set_wavelength(wavelength)
    return


def get_data(previous_pointer: int):
    """Get all data from previous_pointer in the buffer to the current write pointer position.
    
    ### Parameters
        previous_pointer : int
            The previous recorded write pointer position.

    ### Returns
        buffer_string[1:] : str
            A string containing the data (excluding a comma added at the start).
        
        current_pointer : str
            The current write pointer.
    """
    buffer_string = ""
    current_pointer = _RP.get_write_pointer()

    if current_pointer < previous_pointer:
        buffer_string = buffer_string + "," + _RP.get_data_N("SOUR1", previous_pointer, BUFFER_SIZE - previous_pointer) + "," + _RP.get_data_N("SOUR1", 1, current_pointer - 1)
    else:
        buffer_string = buffer_string + "," + _RP.get_data_N("SOUR1", previous_pointer, current_pointer - previous_pointer)

    return buffer_string[1:], current_pointer


def set_sweep_parameters(parameters : tsl.sweep_parameters_class):
    """Sets the sweep parameters.
    
    ### Parameters
        parameters : class TSL770.sweep_parameters_class
            A class containing the sweep parameters. These parameters are 
            the members start_wavelength, stop_wavelength, speed, and power.
    """
    _STS.set_start_wavelength(parameters.start_wavelength)
    _STS.set_stop_wavelength(parameters.stop_wavelength)
    _STS.set_sweep_speed(parameters.speed)
    _TSL.set_power(parameters.power)
    return


def sweep_STS() -> tuple[list[float], float]:
    """Runs the sweep.
    
    ### Returns
        data : list[float]
            Collected data in volts.
        
        acquisition_time : float
            Red Pitaya data acquisition time.
    """
    dec = 2048
    buffer_string = ""
    previous_pointer = 1

    _TRIG.set_external_trigger(0)
    _TRIG.set_trigger_output("Stop")
    _TRIG.set_trigger_standby(1)

    _RP.stop_logging()
    #_RP.rpReset()
    _RP.set_averaging("OFF")
    _RP.set_decimation(dec)
    _RP.set_data_units("Volts")
    _RP.set_trigger_level(1)

    _STS.start_sweep()
    time.sleep(3)
    
    _RP.start_logging()
    time.sleep(131.072e-6 * dec)            # Gives the StemLab time to fill the buffer once

    acquisition_start = time.time()
    previous_pointer = _RP.get_write_pointer()

    _RP.set_trigger_state("CH2_NE")

    _TRIG.send_software_trigger()             # Sends a software trigger to start the sweep

    acquisition_time = 0

    while 1:
        if _RP.get_trigger_state() == "TD":
            _RP.stop_logging()
            acquisition_end = time.time()
            break
            
        buffer_string_temp, previous_pointer = get_data(previous_pointer)
        buffer_string = buffer_string + "," + buffer_string_temp
        
    acquisition_time = acquisition_end - acquisition_start

    buffer_string_temp, previous_pointer = get_data(previous_pointer) 
    buffer_string = buffer_string + "," + buffer_string_temp

    buffer_string = buffer_string[1:]
    buffer_string = buffer_string.strip('{}\n\r').replace("  ", "").replace('{', "")
    buffer_string = buffer_string.replace('}', "").split(',')
    data = list(map(float, buffer_string[:-1]))    # Converts the data to a list of floats
    _STS.stop_sweep()

    return data, acquisition_time