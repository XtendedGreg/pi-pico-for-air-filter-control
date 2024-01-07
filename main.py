import machine
import network
import socket
import ure
import time
import ujson
import os

# Define pin numbers
PWM_PIN = machine.Pin(17, machine.Pin.OUT)
POTENTIOMETER_PIN = machine.ADC(machine.Pin(26))

# Load WiFi credentials from secrets.py
try:
    import secrets
    SSID = secrets.WIFI_SSID
    PASSWORD = secrets.WIFI_PASSWORD
except ImportError:
    print("secrets.py not found. Please create secrets.py with WiFi credentials.")
    raise SystemExit

# Configure PWM for motor control
pwm_motor = machine.PWM(PWM_PIN)
pwm_motor.freq(1000)  # Set PWM frequency to 1 kHz

# Initialize WiFi
sta_if = network.WLAN(network.STA_IF)
sta_if.active(True)
sta_if.connect(SSID, PASSWORD)

# Wait for WiFi connection
while not sta_if.isconnected():
    pass

print("Connected to WiFi")
print("IP Address:", sta_if.ifconfig()[0])  # Print the IP address

# Create a simple web server
addr = socket.getaddrinfo('0.0.0.0', 80)[0][-1]

s = socket.socket()
s.bind(addr)
s.listen(1)

print("Web server is listening on port 80")

# Initialize values
override_value = 100
mode = "Manual"
current_percent = 0

# Function to read potentiometer value as a percentage
def read_potentiometer_percent():
    pot_value = POTENTIOMETER_PIN.read_u16()
    return int((pot_value / 65535) * 100)

def interruption_handler(timer):
    global mode, current_percent
    if mode == "Manual":
        manual_percent = read_potentiometer_percent()
        pwm_motor.duty_u16(int(manual_percent * 65535 / 100))
        print("Manual Mode: "+str(manual_percent)+"%")
        current_percent = manual_percent
        
soft_timer = machine.Timer(mode=machine.Timer.PERIODIC, period=1000, callback=interruption_handler)

def html_return(current_percent, mode):
    # Web page HTML
    if mode == "Override":
        button = """<button id="override_off">Manual</button>
<script>
    var override_off_button = document.getElementById("override_off");
    override_off_button.onclick = function() {
      var xhr = new XMLHttpRequest();
      xhr.open("GET", "/manual", true);
      xhr.send();
      xhr.onload = function() {
        location.reload()
      };
    };
</script>
<button id="power_off">Power Off</button>
<script>
    var power_off_button = document.getElementById("power_off");
    power_off_button.onclick = function() {
      var xhr = new XMLHttpRequest();
      xhr.open("GET", "/off", true);
      xhr.send();
      xhr.onload = function() {
        location.reload()
      };
    };
</script>
"""
    elif mode == "Manual":
        button = """<button id="override_on">Override</button>
<script>
    var override_on_button = document.getElementById("override_on");
    override_on_button.onclick = function() {
      var xhr = new XMLHttpRequest();
      xhr.open("GET", "/override", true);
      xhr.send();
      xhr.onload = function() {
        location.reload()
      };
    };
</script>
<button id="power_off">Power Off</button>
<script>
    var power_off_button = document.getElementById("power_off");
    power_off_button.onclick = function() {
      var xhr = new XMLHttpRequest();
      xhr.open("GET", "/off", true);
      xhr.send();
      xhr.onload = function() {
        location.reload()
      };
    };
</script>
"""
    elif mode == "Off":
        button = """<button id="override_off">Manual</button>
<script>
    var override_off_button = document.getElementById("override_off");
    override_off_button.onclick = function() {
      var xhr = new XMLHttpRequest();
      xhr.open("GET", "/manual", true);
      xhr.send();
      xhr.onload = function() {
        location.reload()
      };
    };
</script>
<button id="override_on">Override</button>
<script>
    var override_on_button = document.getElementById("override_on");
    override_on_button.onclick = function() {
      var xhr = new XMLHttpRequest();
      xhr.open("GET", "/override", true);
      xhr.send();
      xhr.onload = function() {
        location.reload()
      };
    };
</script>
"""
    else:
        button = ""
        
    html = """
    <!DOCTYPE html>
    <html>
    <head><title>Motor Control</title></head>
    <body>
    <h1>Motor Control</h1>
    <p>Current Fan Power: <span id="current_setting">%s%%</span></p>
    <p>Current Mode Setting: <span id="current_mode">%s</span></p>
    %s
    </body>
    </html>
    """ % (current_percent, mode, button)
    return html

# Main loop
while True:
    try:
        client_sock, client_addr = s.accept()

        # Receive and parse HTTP request
        request = client_sock.recv(4096)
        request_str = request.decode('utf-8')

        if "GET /override" in request_str:
            try:
                mode = "Override"
                pwm_motor.duty_u16(int(override_value * 65535 / 100))  # PWM duty cycle is in range [0, 65535]
                print("Override Mode: "+str(override_value)+"%")
                current_percent = override_value
            except Exception as e:
                print("Failed to set override value:", e)
        elif "GET /manual" in request_str:
            try:
                mode = "Manual"
                manual_percent = read_potentiometer_percent()
                pwm_motor.duty_u16(int(manual_percent * 65535 / 100))
                print("Manual Mode: "+str(manual_percent)+"%")
                current_percent = manual_percent
            except Exception as e:
                print("Failed to set manual value:", e)
        elif "GET /off" in request_str:
            try:
                mode = "Off"
                pwm_motor.duty_u16(0)
                print("Power Off Mode: 0%")
                current_percent = 0
            except Exception as e:
                print("Failed to set off value:", e)
        # Send the HTML page
        client_sock.send(html_return(current_percent, mode))
        client_sock.close()
    except Exception as e:
        print("Error:", e)
        time.sleep(1)
        machine.reset()  # Restart on any exception for resilience
