import time
import sys
from pymodbus.client import ModbusTcpClient
from influxdb_client import InfluxDBClient, Point, WriteOptions
from influxdb_client.client.write_api import SYNCHRONOUS

# --- SENSOR CONFIGURATION ---
SENSOR_IP = "192.168.0.160"
SENSOR_PORT = 502

# --- INFLUXDB CONFIGURATION ---
INFLUX_URL = "http://localhost:8086"
# --- IMPORTANT: PASTE YOUR TOKEN FROM STEP 1 HERE ---
INFLUX_TOKEN = "2jawDJw6S4yVkuyaKRL4b5nrkz4m1CSji94K6wbpPpANNpWMcEV_wVkyIeBDvHd1t3kNKjoKJYY-xwyHXtioQw==" 
INFLUX_ORG = "my-org"
INFLUX_BUCKET = "my-bucket"

def main():
    print("--- Starting Sensor to InfluxDB Service ---")

    # --- Initialize InfluxDB Client ---
    try:
        influx_client = InfluxDBClient(url=INFLUX_URL, token=INFLUX_TOKEN, org=INFLUX_ORG)
        write_api = influx_client.write_api(write_options=SYNCHRONOUS)
        print("Successfully connected to InfluxDB.")
    except Exception as e:
        print(f"!!! CRITICAL: Could not connect to InfluxDB: {e}", file=sys.stderr)
        exit(1)

    # --- Initialize Modbus Client ---
    modbus_client = ModbusTcpClient(SENSOR_IP, port=SENSOR_PORT)
    if not modbus_client.connect():
        print(f"!!! CRITICAL: Unable to connect to Modbus device at {SENSOR_IP}. Exiting.", file=sys.stderr)
        exit(1)
    print(f"Successfully connected to sensor at {SENSOR_IP}.")

    # --- MAIN LOOP ---
    while True:
        try:
            result = modbus_client.read_holding_registers(0, count=2)
            if result.isError():
                print("Error reading registers from sensor.", file=sys.stderr)
            else:
                # Get and scale the data
                temperature = result.registers[0] / 10.0
                humidity = result.registers[1] / 10.0
                
                # Create a "Point" of data for InfluxDB
                point = Point("environment") \
                    .tag("location", "server_room") \
                    .field("temperature", temperature) \
                    .field("humidity", humidity)

                # Write the point to the database
                write_api.write(bucket=INFLUX_BUCKET, org=INFLUX_ORG, record=point)
                
                print(f"Data written to InfluxDB: Temp={temperature}°C, Humidity={humidity}%")

        except Exception as e:
            print(f"An error occurred in the main loop: {e}", file=sys.stderr)

        # Wait for 30 seconds before the next reading
        time.sleep(0.5)

if __name__ == '__main__':
    main()