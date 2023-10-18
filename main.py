import PySimpleGUI as sg
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import pandas as pd
import threading
import logging

from RP_TSL770.sts import sts
from RP_TSL770.error_handling.error_handling import exception_handler, formatter

if __name__ == "__main__":
    logger = logging.getLogger(__name__)
    logger.setLevel(logging.DEBUG)

    error_handler = logging.FileHandler(f"./logs/{__name__}_info.log")
    event_handler = logging.FileHandler(f"./logs/{__name__}_errors.log")

    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(formatter)
    logger.addHandler(error_handler)

    event_handler.setLevel(logging.INFO)
    event_handler.setFormatter(formatter)
    logger.addHandler(event_handler)


    inputs = ["st", "en", "sp", "pw"]
    wave = []
    data = []
    toggle = {True: "Looping On", False: "Looping Off"}
    loop_state = False
    sweep_state = False
    wavelength_spin_value = 1500

    def sweep_plot(window, values, figure_canvas_agg, fig):
        global sweep_state
        sweep_state = True

        window["sweepButton"].update("Sweeping...")

        params = sts.TSL770.sweep_parameters_class(
            values["stSlider"],
            values["enSlider"],
            values["spSlider"],
            values["pwSlider"]
        )

        sts.set_sweep_parameters(params)
        data, acquisition_time = sts.sweep_STS()

        window["sweepButton"].update("Begin Sweep")

        update_figure(figure_canvas_agg, data, acquisition_time, params, fig)

        sweep_state = False

    def sweep_loop(window, values, figure_canvas_agg, fig):
        global sweep_state

        while True:
            sweep_state = True
            sts.time.sleep(1)
            sweep_plot(window, values, figure_canvas_agg, fig)
            if not loop_state:
                break

    def plot_data(y_data, acquisition_time: float | int, params: list[float | int]):
        global wave
        global data
        print("Plot params:", params)
        """Plots the data.
        
        ### Parameters
            data : np.array(list[float])
                The ouput data in V.
            
            acquisition_time : float | int
                The total data acquisition time.

            params : list[float | int]
                A list containing the sweep parameters, 
                of the the form [minwave, maxwave, speed, power].
        """
        t = np.linspace(0, acquisition_time, len(y_data))
        print(t)
        print(acquisition_time)
        print(len(data))
        t = [val 
            for val in t 
            if val >= acquisition_time - (params[1] - params[0])/params[2]]
        wave = params[1] + params[2]*(t - t[-1])
        data = y_data[-len(wave):]
        plt.grid(True)
        plt.title("Wavelength Sweep")
        plt.xlabel("Wavelength (nm)")
        plt.ylabel("Voltage (V)")
        plt.plot(wave, data)
        return 

    def bind(win, element_type, bind_from, bind_to):
        """Binds element events.

        ### Parameters
            win : (class) Window
                PySimpleGUI Window.

            element_type : str
                Element type (eg. slider or button).

            bind_from : str
                Event to bind.

            bind_to : str
                What the event binds to.
        """
        inputs = ["st", "en", "sp", "pw", "wave"]
        for inp in inputs:
            win[inp + element_type].bind(bind_from, bind_to)

    def draw_figure(figure_canvas_agg):
        """ Draws the figure onto the canvas.
        
        ### Parameters
            figure_canvas_agg : (class) FigureCanvasTkAgg
                The canvas that the current matplotlib.pyplot figure is drawn on.
        """
        figure_canvas_agg.draw()
        figure_canvas_agg.get_tk_widget().pack(side='top', fill='both', expand=1)
        return figure_canvas_agg

    def delete_figure(figure_canvas_agg, fig):
        """ Clears the current canvas.
        
        ### Parameters
            figure_canvas_agg : (class) FigureCanvasTkAgg
                The canvas to be cleared.

            fig : (class) Figure
                The matplotlib.pyplot figure drawn on the canvas.
        """
        figure_canvas_agg.get_tk_widget().forget()
        fig.clf()

    def update_figure(figure_canvas_agg, data, acquisition_time, params, fig):
        """ Updates the figure on the canvas.

        ### Parameters
            figure_canvas_agg : (class) FigureCanvasTkAgg
                The canvas to be updated

            data : np.array(list[float])
                The data to be plotted.
            
            acquisition_time : float | int
                The total data acquisition time.

            params : list[float | int]
                A list containing the sweep parameters, 
                of the the form [minwave, maxwave, speed, power].

            fig : (class) Figure
                The matplotlib.pyplot Figure that the data is plotted on.
        """
        delete_figure(figure_canvas_agg, fig)
        plot_data(data, acquisition_time, params)
        draw_figure(figure_canvas_agg)


    sg.theme("DarkBlue14")
    """Layout of Inputs (left side of the window)"""
    inputs_column = [
        [sg.Text("Start Wavelength (nm)")], 
        [
            sg.Slider(orientation = "horizontal", 
                    key = "stSlider", 
                    range = (1500, 1600), 
                    enable_events = True, 
                    resolution = 0.01),
            sg.InputText("1500", key = "stInput", size = (7, 1))
        ], 
        [sg.Text("Stop Wavelength (nm)")],
        [
            sg.Slider(orientation = "horizontal", 
                    key = "enSlider", 
                    range = (1500, 1600), 
                    enable_events = True, 
                    resolution = 0.01), 
            sg.InputText("1500", key = "enInput", size = (7, 1))
        ],
        [sg.Text("Sweep Speed (nm/s)")],
        [
            sg.Slider(orientation = "horizontal", 
                    key = "spSlider", 
                    range = (1, 200), 
                    enable_events = True, 
                    resolution = 0.01), 
            sg.InputText("1", key = "spInput", size = (7, 1))
        ],
        [sg.Text("Power (mW)")],
        [
            sg.Slider(orientation = "horizontal", 
                    key = "pwSlider", 
                    range = (0, 3.0), 
                    enable_events = True, 
                    resolution = 0.01), 
            sg.InputText("0", key = "pwInput", size = (7, 1))
        ],
        [sg.Button(toggle[False], key = "loopButton")],
        [sg.Button("Begin Sweep", key = "sweepButton")],
        [sg.Text("Current Wavelength (nm)"), sg.Text("Wavelength Step (nm)")], 
        [
            sg.Spin([i for i in np.arange(1500, 1601, 0.01)], 
                    key = "waveSpin", 
                    size = (7, 1), 
                    enable_events = True), 
            sg.InputText("1", key = "waveInput", size = (7, 1))
        ],
        [sg.Button("Save Data", key = "saveButton")]
    ]
            
    """Layout of the Plot (right side of the window)"""
    canvas_column = [[sg.Canvas(key="figCanvas")]]

    layout = [
        [
            sg.Column(inputs_column, 
                    expand_x = True, 
                    expand_y = True, 
                    element_justification='c'), 
            sg.VSeparator(), 
            sg.Column(canvas_column, 
                    expand_x = True, 
                    expand_y = True, 
                    element_justification='c')
        ]
    ]

    window = sg.Window(
        "STSGui (Andrew Kruger, 2023)", 
        layout, 
        finalize=True, 
        resizable=True, 
        element_justification='c'
    )
    bind(window, "Input", "<Return>", "_Enter")

    fig = plt.figure()
    fig.clf()
    figure_canvas_agg = FigureCanvasTkAgg(fig, window['figCanvas'].TKCanvas)
    draw_figure(figure_canvas_agg)


    """Event Loop"""
    while True:
        window["waveSpin"].update(str(wavelength_spin_value))
        window.refresh()

        event, values = window.read()
        print(event)

        match event:
            case sg.WIN_CLOSED:
                break

            case "stInput_Enter":
                window["stSlider"].update(str(values["stInput"]))
                continue
            case "enInput_Enter":
                window["enSlider"].update(str(values["enInput"]))
                continue
            case "spInput_Enter":
                window["spSlider"].update(str(values["spInput"]))
                continue
            case "pwInput_Enter":
                window["pwSlider"].update(str(values["pwInput"]))
                continue
            case "stSlider":
                window["stInput"].update(str(values["stSlider"]))
                continue
            case "enSlider":
                window["enInput"].update(str(values["enSlider"]))
                continue
            case "pwSlider":
                window["pwInput"].update(str(values["pwSlider"]))
                continue
            case "spSlider":
                window["spInput"].update(str(values["spSlider"]))
                continue
            case "sweepButton":
                if not sweep_state:
                    sweep_thread = threading.Thread(
                        target = sweep_loop, 
                        args = (window, values, 
                            figure_canvas_agg, 
                            fig), 
                        daemon = True)
                    sweep_thread.start()
                continue
            
            case "loopButton":
                loop_state = not loop_state
                window["loopButton"].update(toggle[loop_state])
                continue

            case "waveSpin":
                wavelength_spin_value += float(values["waveInput"])
                wavelength_spin_value = round(wavelength_spin_value, 2)
                window["waveSpin"].update(str(wavelength_spin_value))

                sts.set_wavelength(wavelength_spin_value)
                continue

            case "saveButton":
                pd_data = pd.DataFrame(np.transpose(np.array([wave, data])))
                filename = sg.popup_get_text("Enter file name", title = "CSV File Name")
                print(filename[-4:])
                if filename[-4:] == ".csv":
                    pd_data.to_csv(filename, header = None, index = None)
                else:
                    pd_data.to_csv(filename + ".csv", header = None, index = None)
                continue
