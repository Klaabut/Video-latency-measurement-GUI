from guizero import App, Text, Picture, Box, PushButton
import matplotlib.pyplot as plt
import io
import random
import datetime
import time
import threading
import statistics
from luma.core.interface.serial import i2c
from luma.core.render import canvas
from luma.oled.device import ssd1306
from PIL import Image, ImageDraw, ImageFont
import numpy as np
from multiprocessing import Process
from multiprocessing import Value
import subprocess
from gpiozero import LED
import RPi.GPIO as GPIO
# LED stuff
ledPin = 22


#LCD stuff
# Define the I2C bus
#i2c = busio.I2C(board.SCL, board.SDA)
# Define the I2C bus and display
serial = i2c(port=1, address=0x3C)
device = ssd1306(serial)

font = ImageFont.truetype("Minecraftia.ttf", 8)

# Sample data for plotting
timeArr = []
delay = []
measurementSize = 30  # The number of delays in one file. Default is 30(one session = 1min)
graph_picture = None  # Declare graph_picture as a global variable
hist_picture = None  # Declare hist_picture as a global variable
sensor_thread_instance = None  # Declare sensor_thread_instance as a global variable
led_thread_instance = None
stop_led_blink = threading.Event()  # Event to signal stopping LED blinking



def led_state():
    global goodToGraph, goodToBlink, led_thread_instance
	if not sync_process.is_alive():
		sync_process.start()    
	
	device.clear()
	hide_sensor_var()
	goodToGraph = False #Allows graph generation
	goodToBlink = True #Allows LED to blink
	
	if delay:
		save_to_file()    
		delete_graph()
		timeArr.clear()
		delay.clear()        
	currentState.value = "Current state: BLINKING"

    # LED BLINK CODE HERE
	if sensor_thread_instance and sensor_thread_instance.is_alive():
		sensor_thread_instance.join()
	if not led_thread_instance or not led_thread_instance.is_alive():
		led_thread_instance = threading.Thread(target=blink_led)
		led_thread_instance.daemon = True  # Set daemon to True
		led_thread_instance.start()
    
	
def blink_led():
    global goodToBlink
    #GPIO.setmode(GPIO.BCM)
    #GPIO.setup(ledPin, GPIO.OUT)
    led = LED(ledPin)
    try:
        while goodToBlink:
            # Blink the LED every even second
            if datetime.datetime.now().second % 2 == 0:
                led.on()
            else:
                led.off()

            time.sleep(0.5)  # Blinking interval
            display_on_lcd([
                f"{syncroStatus.value}",
                f"{currentState.value}"])
                      
        led.off()
        led.close()
        print("LED free")  
    except (KeyboardInterrupt, EOFError):
        # Cleanup GPIO on keyboard interrupt
        led.off()
        led.close()
        print("LED free")



def delete_graph():
    # Remove the graph_picture from the GUI
    global graph_picture, hist_picture
    if graph_picture:
        graph_picture.destroy()
        graph_picture = None  # Reset graph_picture to None
    if hist_picture:
        hist_picture.destroy()
        hist_picture = None  # Reset graph_picture to None
def generate_graph():
    global graph_picture, goodToGraph, hist_picture
    global timeArr, delay

    if goodToGraph:
        # --------------LINE GRAPH CREATION------------------------
        # Clear the current plot
        plt.clf()

        # Set the size of the plot
        plt.figure(figsize=(10, 6))  # Adjust the size as needed

        # Plot the data
        plt.plot(timeArr, delay)
        plt.xlabel('Timestamp')
        plt.ylabel('Delay (ns)')
        plt.title('Delay graph')
        plt.grid(True)

        # Calculate the number of ticks to display
        max_ticks = 10  # Adjust as needed
        num_timestamps = len(timeArr)
        tick_step = max(1, num_timestamps // max_ticks)

        # Set x-axis ticks and labels
        plt.xticks(range(0, num_timestamps, tick_step), timeArr[::tick_step], rotation=45)

        # Plot the mean line
        mean_value = calculate_mean(delay)
        meanValue.value = f"Mean: {mean_value:.2f} ms"
        plt.axhline(y=mean_value, color='r', linestyle='--', label=f'Mean: {mean_value:.2f} ms')

        # Plot the standard deviation line
        stddev_value = calculate_stddev(delay)
        stddev.value = f"Standard Deviation: {stddev_value:.2f} ms"
        plt.axhline(y=mean_value - stddev_value, color='g', linestyle='--',
                    label=f'Standard Deviation: {stddev_value:.2f} ms')
        plt.axhline(y=mean_value + stddev_value, color='g', linestyle='--')

        # Legend
        plt.legend(loc='best')

        # plt.tight_layout()  # Automatically adjust the size

        # Save the plot to an image file
        plt.savefig("graph.png", format='png')

        # matplotlib uses alot of memory so closing is needed
        plt.close()

        # Update the image source of graph_picture
        if graph_picture:
            graph_picture.value = "graph.png"
        else:
            graph_picture = Picture(graph_box, grid=[1, 0], align="top", image="graph.png")
            
        # ---------------------HISTOGRAM CREATION----------------------------
        if len(delay) == measurementSize:
            # Clear the current plot
            plt.clf()

            # Create subplots with only one plot for the histogram
            fig, ax2 = plt.subplots(1, 1, figsize=(10, 6))  # Adjust the size as needed
            # Apply filter to remove the anomalies
            filtered_delay = [delay for delay in delay if delay >= mean_value - 3 * stddev_value and delay <= mean_value + 3 * stddev_value]
            # Plot the histogram
            ax2.hist(delay, bins=10, alpha=0.7, color='blue', edgecolor='black')
            ax2.set_xlabel('Filtered delay (ms)')
            ax2.set_ylabel('Frequency')
            ax2.set_title(f"Filtered distribution of last {measurementSize} of delays (mean-3σ ; mean+3σ)")

            # Calculate mean and standard deviation for histogram
            mean_value_hist = calculate_mean(filtered_delay)
            stddev_value_hist = calculate_stddev(filtered_delay)
            ax2.axvline(x=mean_value_hist, color='r', linestyle='--', label=f'Filtered mean: {mean_value_hist:.2f} ms')
            ax2.axvline(x=mean_value_hist - stddev_value_hist, color='g', linestyle='--',
                        label=f'Filtered Standard Deviation: {stddev_value_hist:.2f} ms')
            ax2.axvline(x=mean_value_hist + stddev_value_hist, color='g', linestyle='--')

            # Legend for histogram
            ax2.legend(loc='best')

            # Save the plot to an image file
            plt.savefig("histogram.png", format='png')

            # Close the plot
            plt.close()

            # Update the image source of hist_picture
            if hist_picture:
                hist_picture.value = "histogram.png"
            else:
                hist_picture = Picture(graph_box, grid=[2, 0], align="top", image="histogram.png")
            # Adjust the width of the GUI window
            app.width = 1024 + 900  # Increase the width by 500 pixels to accommodate the histogram
    else:
        return
def sensor_thread():
    
    while True:
        if not goodToGraph:
            break
        else:
            current_time = datetime.datetime.now()
        	
            #Saving to file 
            if len(delay) == measurementSize:
                save_to_file()
                timeArr.clear()
                delay.clear()
            if current_time.second % 2 == 0: # Check if the second is even
            	# Append the current even second timestamp to the time array
                timeArr.append(current_time.strftime("%H:%M:%S"))
            
            	# Generate a random delay up to one second in milliseconds
                #random_delay = random.randint(0, 1000000000)#delay up to 1s in ns
                random_delay = random.randint(0, 2000000)
                random_delay = random_delay / 1000000  # converted from ns to ms
                # Append the random delay to the delay array
                delay.append(random_delay)
                
                #SENSOR CODE HERE, comment out the random generation!!!!!!
                
                #delay.append(sensor_input)
                #LCD print
                
                # Update the newestDelay text with the latest delay value
                newestDelay.value = f"Newest delay: {random_delay} ms"
                
                # Update the newestDelay text with the latest delay value
                newest_delay_text = f"Newest delay: {random_delay} ms"
                newestDelay.value = newest_delay_text
                mean_value = round(calculate_mean(delay), 2)
                stddev_value = round(calculate_stddev(delay), 2)
                #device.clear()
                
                display_on_lcd([
                    f"{syncroStatus.value}",
                    f"{currentState.value}",
                    f"{newest_delay_text}",
                    f"Mean: {mean_value} ms",
                    f"STD DEV: {stddev_value} ms"
])         
                
                app.after(0, generate_graph)
        time.sleep(1)
def display_on_lcd(lines):
    # Clear the display
    device.clear()
    # Display text on separate lines
    with canvas(device) as draw:
        y = 5
        for line in lines:
            draw.text((0, y), line, fill="white", font=font)
            y += 10  # Move to next line
def save_to_file():
    #device.clear()
     # Generate a timestamp for the filename
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    filename = f"Log_file_{timestamp}.txt"
    with open(filename, "w") as file:
            # Write the current timestamps and delays into file along with their mean and standard deviation
            mean = calculate_mean(delay)
            stddev = calculate_stddev(delay)
            print("writing")
            for timestamp, delay_value in zip(timeArr, delay):
                
                file.write(f"Timestamp: {timestamp}\nDelay: {delay_value} ms\n\n")
            file.write(f"Mean: {mean} ms\nStandard deviation: {stddev} ms\n\n")
    
def sensor_state():
    global sensor_thread_instance, goodToGraph, led_thread_instance, goodToBlink
    global graph_picture, timeArr, delay  # Declare global variables
    if not sync_process.is_alive():
        sync_process.start()    

    goodToGraph = True #Allows graph generation
    goodToBlink = False #Stops LED blink

    # Clear previous data
    if delay:
        save_to_file()
        timeArr.clear()
        delay.clear()
    # Show the disp and mean on the form
    show_sensor_var()
    # Generate the graph
    generate_graph()
    currentState.value = "Current state: SENSOR ACTIVE"
    with canvas(device) as draw:
        draw.text((0, 5), syncroStatus.value, fill="white", font=font)  
        draw.text((0, 15), currentState.value, fill="white", font=font)    
    # Wait for LED blinking thread to stop
    if led_thread_instance and led_thread_instance.is_alive():
        led_thread_instance.join()
        
    if not sensor_thread_instance or not sensor_thread_instance.is_alive():
        sensor_thread_instance = threading.Thread(target=sensor_thread)
        sensor_thread_instance.daemon = True
        sensor_thread_instance.start()


# Rest of your code...
def hide_sensor_var():
	#hide sensorstate variables
	meanValue.hide()
	newestDelay.hide()
	stddev.hide()
def show_sensor_var():
	#show sensorstate variables
	meanValue.show()
	newestDelay.show()
	stddev.show()	
    
def calculate_mean(data):
    if data:
        return statistics.mean(data)
    else:
        return 0

def calculate_stddev(data):
    if len(data) > 1:
        return statistics.pstdev(data)
    else:
        return 0
def sync_time_with_ntp_server():
    #EXAMPLE NTP SYNC CODE REWORK WHEN INTEGRATING INTO PROTOTYPE
    global syncSuccess
    command = "sudo ntpdate ntp.ttu.ee"
    while True:
        process = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        output, error = process.communicate()
            
        if process.returncode == 0:
            print("sync success")
            syncroStatus.value = "Sync status: SYNCED"
            #status_queue.put("Sync status: SYNCED")
            #with canvas(device) as draw:
            #    draw.text((0, 5), "Sync status: SYNCED", fill="white", font=font)
        else:
            print("SYNC ERROR:", error.decode())
            syncroStatus.value = "Sync status: FAILURE"
            #status_queue.put("Sync status: FAILURE")
            #with canvas(device) as draw:
            #    draw.text((0, 5), "Sync status: FAILURE", fill="white", font=font)
        time.sleep(5)  # Wait for 5 second before syncing again

    
if __name__ == "__main__":    
    app = App(title="Reval GUI", width=1024, height=800)
    # Set the app window position to the top left corner
    app.tk.attributes("-alpha", True)
    app.tk.geometry("+0+0")

    # Create a box to contain the buttons
    button_box = Box(app, layout="grid", width="fill", height="20", align="top")
    info_box = Box(app, layout="grid", width="fill", height="20", align="top")
    graph_box = Box(app, layout="grid", width="fill", height="fill", align="top")
    #info panel
    infoPanelTitle = Text(info_box, text="Info panel:", grid=[0, 0], align="left", size=20)
    syncroStatus = Text(info_box, text="Sync status: ", grid=[0, 1], align="left")
    currentState = Text(info_box, text="Current state:", grid=[0, 2], align="left")
    newestDelay = Text(info_box, text="Newest delay:", grid=[0, 3], align="left")
    meanValue = Text(info_box, text="Mean:", grid=[0, 4], align="left")
    stddev = Text(info_box, text="Standard deviation:", grid=[0, 5], align="left")
    sync_process = threading.Thread(target=sync_time_with_ntp_server)      
    
    
    ledButton = PushButton(button_box, command=led_state, text="BLINK", grid=[0, 0], align="left", width= 29)
    ledButton.text_size = 20
    sensorButton = PushButton(button_box, command=sensor_state, text="SENSE", grid=[1, 0], align="right", width= 28)
    sensorButton.text_size = 20
    
    app.display()
