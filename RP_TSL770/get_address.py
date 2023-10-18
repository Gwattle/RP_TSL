import pyvisa
import nidaqmx

rm = pyvisa.ResourceManager() 
listing = rm.list_resources() # List of detected connections
system = nidaqmx.system.System.local()

def get_address_IL():
    """Returns the index of the selected instrument in the 'tools' list.
    
    ### Returns
        selection : str
            The index of the chosen instrument in the 'tools' list.
    """

    print("##############################################")
    print("Present GPIB instruments")

    tools=[i for i in listing if 'GPIB' in i] # Take only GPIB connections

    for i in range(len(tools)):
        buffer = rm.open_resource(tools[i], read_termination = '\r\n')      # Store GPIB intruments in a buffer
        print(i+1, ": ", buffer.query('*IDN?'))                             # Display GPIB instrument IDs

    print('')
    print("##############################################")
    print("")
    print("Select light source")
    selection = input()
    
    return selection