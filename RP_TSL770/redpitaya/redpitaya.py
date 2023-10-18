import logging
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

class ACQ():
    """## Red Pitaya Data Acquisition Class
    This class contains all the functions relevant to the Red Pitaya's data logger.
    """
    def __init__(self, rp_s):
        """Initialise Data Acquisition Setup
        
        ### Parameters
            rp_s : scpi.scpi
                Red Pitaya scpi object.
        """
        self.rp_s = rp_s                    # Sets the Red Pitaya device to be that given by the user
        self.redpitaya_reset()                      # Resets the acquire settings
        self.set_averaging("OFF")
        self.set_decimation(2048)
        self.__set_trigger_delay(-8192)       # Places the trigger at the end of the data
        self.set_data_units("VOLTS")
        self.set_trigger_level(1)    

    def redpitaya_reset(self):
        """Resets the data acquisition settings of the Red Pitaya."""
        self.rp_s.tx_txt("ACQ:RST")
        return

    def start_logging(self):
        """Starts the data logging."""
        self.rp_s.tx_txt("ACQ:START")
        return
    
    def stop_logging(self):
        """Stops the data logging."""
        self.rp_s.tx_txt("ACQ:STOP")

    @exception_handler(logger)
    def set_decimation(self, dec: int):
        """Sets the decimation value.
        
        ### Parameters:
            dec : int
                The decimation number, must be a power of 2
        """

        is_power_of_two = (dec != 0) and ((dec & (dec - 1)) == 0)

        try:
            if is_power_of_two:
                self.rp_s.tx_txt("ACQ:DEC " + str(dec))
            else:
                raise ValueError("Invalid decimation number")
        except ValueError as e:
            e.add_note("The decimation value must be a power of 2")
            raise
        return

    @exception_handler(logger)
    def set_averaging(self, state: str):
        """Sets the averaging state.
        
        Parameters:
            state : str
                The averaging state ("ON" or "OFF")    
        """
        try:
            if (state.upper() == "ON" or state.upper() == "OFF"):
                self.rp_s.tx_txt("ACQ:AVG " + state.upper())
            else:
                raise ValueError("Invalid state")
        except ValueError as e:
            e.add_note("The possible states are \"ON\" or \"OFF\"")
        return

    def get_write_pointer(self) -> int:
        """Returns the position of the write pointer.
        
        Returns:
            pWpos : int
                The position of the write pointer in the buffer.
        """
        self.rp_s.tx_txt("ACQ:WPOS?")
        pWpos = int(self.rp_s.rx_txt())
        return pWpos
    
    def __set_trigger_delay(self, delay: int):
        """Sets the trigger delay to 'delay' in samples.
        
        Parameters:
            delay : int
                The trigger delay in samples. A delay of 0 sets the trigger 
                in the centre of the buffer (thus, the delay is actually 8192 samples).
        """
        self.rp_s.tx_txt("ACQ:TRIG:DLY " + str(delay))
        return
    
    def set_trigger_level(self, level: float):
        """Sets the trigger level
        
        Parameters:
            level : float
                The trigger level in volts.
        """
        self.rp_s.tx_txt("ACQ:TRIG:LEV " + str(level))
        return

    @exception_handler(logger)
    def set_data_units(self, unit: str):
        """Sets the units for the collected data.
        
        Parameters:
            units : str
                Data units ("RAW" or "VOLTS").
        """
        try:
            if (unit.upper() == "RAW" or unit.upper() == "VOLTS"):
                self.rp_s.tx_txt("ACQ:DATA:UNITS " + unit.upper())
            else:
                raise ValueError
        except ValueError as e:
            e.add_note("The supported data units are RAW data units or VOLTS")
            raise
        return

    def set_trigger_state(self, channel: str):
        """Sets the trigger state/channel (unlikely to be used).
        
        Parameters:
            channel : str
                The trigger state/channel.
        """
        self.rp_s.tx_txt("ACQ:TRIG " + channel)
        return
    
    def get_trigger_state(self) -> str:
        """Returns the current state of the trigger
        
        Returns:
            state : str
                The current trigger status.
        """
        self.rp_s.tx_txt("ACQ:TRIG:STAT?")
        state = self.rp_s.rx_txt()
        return state

    def get_data_N(self, source: str, start: int, N: int) -> str:
        """Returns N data values from the buffer.
        
        Parameters:
            source : str
                The input source that the data should be obtained from.
            start : int
                The buffer position to start taking data from (inclusively).
            N : int
                The number of buffer positions to read 
                (starting from start and going to start + N, exclusively).
        Returns:
            data : str
                The recorded data.
        """
        self.rp_s.tx_txt("ACQ:" 
                         + str(source) 
                         + ":DATA:STA:N? " 
                         + str(start) + "," + str(N))
        data = self.rp_s.rx_txt() 
        return data
    
    def get_data(self, source: str) -> str:
        """Gets all the data stored in the buffer.
        
        Parameters:
            source : str
                The input source that the data should be obtained from.
        
        Returns:
            data : str
                The recorded data.
        """
        self.rp_s.tx_txt("ACQ:" + str(source) + "DATA?")
        data = self.rp_s.rx_txt()
        return data