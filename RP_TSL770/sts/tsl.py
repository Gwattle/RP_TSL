import pyvisa 
import logging
from dataclasses import dataclass
import os

from ..error_handling.error_handling import exception_handler, formatter

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

### Resource manager ###
rm = pyvisa.ResourceManager() 
listing = rm.list_resources() # List of detected connections
tools = [i for i in listing if 'GPIB' in i]

tsl_version = 770

@dataclass
class sweep_parameters_class:
    """## Sweep Parameters Data Class

    Contains the members start_wavelength, stop_wavelength, speed, and power.
    """
    speed: int | str | float
    power: int | str | float
    start_wavelength: int | str | float = 1500
    stop_wavelength: int | str | float = 1600


class TSL:
    """## TSL Laser Class

    This is the class that contains all the functions relevant to the laser.
    """
    def __init__(self, laser, read_terminator: str, write_terminator: str):
        """Sets initial values for the TSL

        ### Parameters
            laser : int
                This is the index in "tools" (+1) for the laser resource.
            read_terminator : str
                This is the read terminator.
            write_terminator : str
                This is the write terminator.
        """
        self.buf = rm.open_resource(
            tools[int(laser) - 1], 
            read_termination = read_terminator, 
            write_termination = write_terminator
        )     

        self.GPIB = int(self.buf.query(":SYST:COMM:GPIB:ADDR?"))        # The GPIB address for the TSL
        self.set_wavelength_unit("nm")
        self.set_power_unit("mW")

    @exception_handler(logger)
    def set_wavelength_unit(self, unit: str):
        """Sets the wavelength units for the TSL
        
        ### Parameters
            unit : str
                This is the unit to be used (nm or THz)
        """
        try:
            match unit.lower():
                case "thz":
                    self.buf.write(":WAV:UNIT 1")       # Sets the units to THz
                    return
                case "nm":
                    self.buf.write(":WAV:UNIT 0")       # Sets the units to nm
                    return
                case _:
                    raise ValueError("Invalid unit")
        except ValueError as e:
            e.add_note("Only THz and nm are supported")
            raise

    def get_wavelength(self):
        """Returns the current wavelength of the TSL
        
        ### Returns
            wavelength : str
                This is the current wavelength of the TSL (in the chosen units, m by default).
        """
        wavelength = self.buf.query(":WAV?")
        return wavelength
    
    @exception_handler(logger)
    def set_wavelength(self, wavelength: int | str | float):
        """Sets the wavelength of the TSL
        
        ### Parameters
            wavelength : int | str | float
                This is the wavelength that the TSL will be set to (in nm)
        """
        try:
            if (1480 <= wavelength <= 1640) and (tsl_version == 770):
                self.buf.write(":WAV " + str(wavelength) + "nm")
            elif (1480 <= wavelength <= 1640) and (tsl_version == 550):
                self.buf.write(":WAV " + str(wavelength))
            else:
                raise ValueError("Invalid wavelength")
        except ValueError as e:
            e.add_note("The wavelength must be in the range 1480-1640 nm")
            raise
        return

    @exception_handler(logger)
    def set_diode_state(self, state: str | int):
        """Sets the state of the laser diode
        
        ### Parameters
            state : str | int
                The diode state (0 for off, 1 for on)
        """
        try: 
            if (state == 0 or state == 1):
                self.buf.write(":POW:STAT " + str(state))
            else:
                raise ValueError("Invalid state")
        except ValueError as e:
            e.add_note("The state must be 0 (off) or 1 (on)")
            raise
        return

    @exception_handler(logger)
    def set_power_unit(self, unit: str):
        """Sets the power units for the TSL
        
        ### Parameters
            unit : str
                The chosen units ("dBm" or "mW")
        """
        try:
            match unit.lower():
                case "dbm":
                    unit = "0"
                case "mw":
                    unit = "1"
                case _:
                    raise ValueError("Invalid unit")
            self.buf.write(":POW:UNIT " + unit)
        except ValueError as e:
            e.add_note("Only dBm and mW are supported")
            raise
        return
    
    @exception_handler(logger)
    def set_power(self, power: str | float | int):
        """Sets the power of the TSL
        
        ### Parameters
            power : str | float | int
                The chosen power (in mW)
        """
        try: 
            if (power <= 13) and (tsl_version == 770):
                self.buf.write(":POW " + str(power) + "mW")
            elif (power <= 13) and (tsl_version == 550):
                self.buf.write(":POW " + str(power))
            else:
                raise ValueError("Invalid power")
        except ValueError as e:
            e.add_note("Power must be below 13 mW")
            raise
        return


class TRIGGER:
    """## TSL Trigger Class

    This is a class that contains all the functions relevant to the input/ouput 
    triggers of the TSL.
    """
    def __init__(self, laser):
        """Initialises the Trigger class.
        
        ### Parameters
            laser : str | int
                The index (+1) for the chosen TSL
        """
        self.TSL = laser.buf
        self.set_external_trigger(1)
        self.set_trigger_edge(0)
        self.set_trigger_output("Stop")

    @exception_handler(logger)
    def set_external_trigger(self, mode: str | int):
        """Sets the trigger to internal or external.
        
        ### Parameters
            mode : str | int
                The trigger mode. 0 for internal (front panel) and 1 for external (rear BNC)
        """
        try:
            if (mode == 0 or mode == 1):
                self.TSL.write(":TRIG:INP:EXT " + str(mode))
            else:
                raise ValueError("Invalid mode")
        except ValueError as e:
            e.add_note("The supported modes are 0 (internal) and 1 (external)")
            raise
        return
    
    def get_external_trigger(self):
        """Gets the trigger mode (internal or external)
        
        ### Returns
            mode : str
                The trigger mode. 0 for internal (front panel) and 1 for external (rear BNC)
        """
        mode = self.TSL.write(":TRIG:INP:EXT?")
        return mode

    @exception_handler(logger)
    def set_trigger_edge(self, edge: str | int):
        """Sets the trigger input edge.
        
        ### Parameters
            edge : str | int
                The trigger edge. 0 for rising and 1 for falling
        """
        try:
            if (edge == 0 or edge == 1):
                self.TSL.write(":TRIG:INP:ACT " + str(edge))
            else:
                raise ValueError("Invalid mode")
        except ValueError as e:
            e.add_note("The supported modes are 0 (rising edge) and 1 (falling edge)")
            raise
        return

    def send_software_trigger(self):
        """Sends a software trigger to the TSL 
        (this is used to remotely trigger the TSL when in external mode).
        """
        self.TSL.write(":TRIG:INP:SOFT")
        return
        
    @exception_handler(logger)
    def set_trigger_standby(self, mode: str | int):
        """Sets the TSL's standby mode.
        
        ### Parameters
            mode : str | int
                The trigger standby mode. 
                0 to disable standby mode and 1 to enable standby mode.
        """
        try:
            if (mode == 0 or mode == 1):
                self.TSL.write(":TRIG:INP:STAN " + str(mode))
            else:
                raise ValueError("Invalid mode")
        except ValueError as e:
            e.add_note("The supported modes are 0 (disabled) and 1 (enabled)")
            raise
        return
    
    def get_trigger_standby(self):
        """Gets the standby status.
        
        ### Returns
            mode : str
                Returns the current trigger mode. 
                Returns 'ERROR!: Invalid Error' if the mode is not recognised.
        """
        mode = self.TSL.write("TRIG:INP:STAN?")
        match mode:
            case "0":
                return "Normal operation mode"
            case "1":
                return "Trigger standby mode"
            case _:
                return "ERROR!: Invalid Mode"

    @exception_handler(logger)
    def set_trigger_output(self, when: str):
        """Sets where in the sweep the ouput trigger is sent.
        
        ### Parameters
            when : str
                When the trigger is sent.
                        - 'None' for no trigger
                        - 'Stop' for a trigger at the end of the sweep
                        - 'Start' for a trigger at the start of the sweep
                        - 'Step' for a trigger at each wavelength step
        """
        try:
            match when.lower():
                case "none":
                    when = "0"
                case "stop":
                    when = "1"
                case "start":
                    when = "2"
                case "step":
                    when = "3"
                case _:
                    raise ValueError("Invalid value")
            self.TSL.write(":TRIG:OUTP " + when)
        except ValueError as e:
            e.add_note("The valid values are None (no trigger), \
                       Stop (trigger at the end of the sweep), \
                       Start (trigger at the start of the sweep), \
                       Step (trigger at each wavelength step)")
            raise


    def get_trigger_output(self):
        """Gets where the output trigger is sent.
        
        ### Returns
            mode : str
                    - 'None' for no trigger
                    - 'Stop' for a trigger at the end of the sweep
                    - 'Start' for a trigger at the start of the sweep
                    - 'Step' for a trigger at each trigger step
        """
        mode = self.TSL.write("TRIG:OUTP?")
        match mode:
            case "0":
                return "None"
            case "1":
                return "Stop"
            case "2":
                return "Start"
            case "3":
                return "Step"


class STS:
    """## TSL Swept Test System Class
    This is a class of all the functions necessary to run a wavelength sweep.
    """

    def __init__(self, laser: str | int):
        """Sets the initial parameters for the sweep.
        
        ### Parameters
            laser : str | int
                The index (+1) for the chosen TSL
        """
        self.TSL = laser.buf
        self.set_sweep_mode(1)
        self.set_start_wavelength(1500)
        self.set_stop_wavelength(1600)
        self.set_sweep_step(0.1)
        self.__set_sweep_cycles(0)

    def __set_sweep_cycles(self, cycles: str | int):
        """Sets the number of sweeps 
        (this function should not be used).
        
        ### Parameters
            cycles : str | int
                The number of sweeps to be run.
        """
        self.TSL.write(":WAV:SWE:CYCL " + str(cycles))
        return

    @exception_handler(logger)
    def set_sweep_step(self, step: str | int | float):
        """Sets the sweep step size.
        
        ### Parameters
            step : str | int | float
                The step size in pm.
        """
        try:
            if (0.1 <= step <= 160000) and (tsl_version == 770):
                self.TSL.write(":WAV:SWE:STEP " + str(step) + "pm")
            elif (0.1 <= step <= 160000) and (tsl_version == 550):
                self.TSL.write(":WAV:SWE:STEP " + str(step*1e-3))
            else:
                raise ValueError("Invalid step size")
        except ValueError as e:
            e.add_note("Only step sizes in the interval 0.1-160000 pm are supported")
            raise
        return

    @exception_handler(logger)
    def set_start_wavelength(self, wavelength: str | int | float):
        """Sets the initial wavelength of the sweep.
        
        ### Parameters
            wavelength : str | int | float
                The intial wavelength in nm
        """
        try:
            if (1480 <= wavelength <= 1640) and (tsl_version == 770):
                self.TSL.write(":WAV:SWE:STAR " + str(wavelength) + "nm")
            elif (1480 <= wavelength <= 1640) and (tsl_version == 550):
                self.TSL.write(":WAV:SWE:STAR " + str(wavelength))
            else:
                raise ValueError("Invalid wavelength")
        except ValueError as e:
            e.add_note("Only wavelengths in the interval 1480-1640 nm are supported")
            raise
        return

    def get_start_wavelength(self):
        """Gets the initial wavelength of the sweep.
        
        ### Returns
            wavelength : str
                The initial wavelength.
        """
        wavelength = self.TSL.query(":WAV:SWE:STAR?") + "m"
        return wavelength
    
    @exception_handler(logger)
    def set_stop_wavelength(self, wavelength):
        """Sets the final wavelength of the sweep.
        
        ### Parameters
            wavelength : str | int | float
                The final wavelength in nm
        """
        try:
            if (1480 <= wavelength <= 1640) and (tsl_version == 770):
                self.TSL.write(":WAV:SWE:STOP " + str(wavelength) + "nm")
            elif (1480 <= wavelength <= 1640) and (tsl_version == 550):
                self.TSL.write(":WAV:SWE:STOP " + str(wavelength))
            else:
                raise ValueError("Invalid wavelength")
        except ValueError as e:
            e.add_note("Only wavelengths in the interval 1480-1640 nm are supported")
            raise
        return
    
    def get_stop_wavelength(self):
        """Gets the final wavelength of the sweep.
    
        ### Returns
            wavelength : str
                The final wavelength.
        """
        wavelength = self.TSL.query(":WAV:SWE:STOP?") + "m"
        return wavelength

    @exception_handler(logger)
    def set_sweep_mode(self, mode: str | int):
        """Sets the sweep type.
        
        ### Parameters
            mode : str | int
                The sweep mode.

                        - For a one-way step sweep, mode = 0
                        - For a one-way continuous sweep, mode = 1
                        - For a two-way step sweep, mode = 2
                        - For a two-way continuous sweep, mode = 3
        """
        try:
            if (mode == 0 or mode == 1 or mode == 2 or mode == 3):
                self.TSL.write(":WAV:SWE:MOD " + str(mode))
            else:
                raise ValueError("Invalid mode")
        except ValueError as e:
            e.add_note("The supported modes are 0 (one-way step sweep), \
                       1 (one-way continuous sweep), \
                       2 (two-way step sweep), \
                       3 (two-way continuous sweep)")
            raise
        return
    
    def get_sweep_mode(self):
        """Gets the sweep type.
        
        ### Returns
            mode : str
                The sweep mode.
        """
        mode = self.TSL.query(":WAV:SWE:MOD?")
        match mode:
            case "0":
                return "One-way step mode"
            case "1":
                return "One-way continuous mode"
            case "2":
                return "Two-way step mode"
            case "3":
                return "Two-way continuous mode"
            case _:
                return "Error!: Invalid Mode"
    
    @exception_handler(logger)
    def set_sweep_speed(self, speed: str | int | float):
        """Sets the sweep speed.
        
        ### Parameters
            speed : str | int | float
                The sweep speed in nm/s.
        """
        try:
            if (0.5 <= speed <= 200) and (tsl_version == 770):
                self.TSL.write(":WAV:SWE:SPE " + str(speed) + "nm/s")
            elif (0.5 <= speed <= 200) and (tsl_version == 550):
                self.TSL.write(":WAVE:SWE:SPE " + str(speed))
            else:
                raise ValueError("Invalid sweep speed")
        except ValueError as e:
            e.add_note("Only sweep speeds in the interval 0.5-200 nm/s are supported")
            raise
        return
    
    def get_sweep_speed(self):
        """Gets the sweep speed.
        
        ### Returns
            speed : str
                The sweep speed.
        """
        speed = self.TSL.query(":WAV:SWE:SPE?") + "m/s"
        return speed
    
    def get_sweep_step(self):
        """Gets the step size of the sweep.
        
        ### Returns
            step : str
                The step size.
        """
        step = self.TSL.query(":WAV:SWE:STEP?") + "m"
        return step

    def start_sweep(self):
        """Starts the wavelength sweep."""
        self.TSL.write(":WAV:SWE 1")
        return

    def get_sweep_state(self):
        """Gets the sweep state.
        
        ### Returns
            state : str
                The current state of the sweep
        """
        state = self.TSL.write(":WAV:SWE?") 
        match state:
            case "0":
                return "Stopped"
            case "1":
                return "Running"
            case "2":
                return "Standing by trigger"
            case "3":
                return "Preparation for sweep start"
            case _:
                return "(" + str(state) + ") " + "ERROR!: Invalid State"

    def stop_sweep(self):
        """Stops the wavlength sweep."""
        self.TSL.write(":WAV:SWE 0")
        return