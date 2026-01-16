import time
import sys
import os

from dotenv import load_dotenv
from pymodbus.client import ModbusTcpClient
from influxdb_client import InfluxDBClient, Point
from influxdb_client.client.write_api import SYNCHRONOUS

# Load environment variables
load_dotenv()

def get_env(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise RuntimeError(f"Missing required env variable: {name}")
    return value

# --- CONFIGURATION FROM ENV ---
DATABASE_URL = get_env("DATABASE_URL")

INFLUX_URL = get_env("INFLUX_URL")
INFLUX_TOKEN = get_env("INFLUX_TOKEN")
INFLUX_ORG = get_env("INFLUX_ORG")
INFLUX_BUCKET = get_env("INFLUX_BUCKET")

SENSOR_IP = get_env("SENSOR_IP")
SENSOR_PORT = int(get_env("SENSOR_PORT"))

POLL_INTERVAL = float(os.getenv("POLL_INTERVAL", 1))

def main():
    print("--- Starting Sensor to InfluxDB Service ---")
    print(f"Database URL: {DATABASE_URL}")

    # --- InfluxDB Client ---
    try:
        influx_client = InfluxDBClient(
            url=INFLUX_URL,
            token=INFLUX_TOKEN,
            org=INFLUX_ORG
        )
        write_api = influx_client.write_api(write_options=SYNCHRONOUS)
        print("Connected to InfluxDB")
    except Exception as e:
        print(f"CRITICAL: InfluxDB connection failed: {e}", file=sys.stderr)
        sys.exit(1)

    # --- Modbus Client ---
    modbus_client = ModbusTcpClient(SENSOR_IP, port=SENSOR_PORT)
    if not modbus_client.connect():
        print(f"CRITICAL: Cannot connect to sensor {SENSOR_IP}", file=sys.stderr)
        sys.exit(1)

    print(f"Connected to sensor at {SENSOR_IP}")

    # --- MAIN LOOP ---
    while True:
        try:
            result = modbus_client.read_holding_registers(0, count=2)

            if result.isError():
                print("Modbus read error", file=sys.stderr)
            else:
                temperature = result.registers[0] / 10.0
                humidity = result.registers[1] / 10.0

                point = (
                    Point("environment")
                    .tag("location", "server_room")
                    .field("temperature", temperature)
                    .field("humidity", humidity)
                )

                write_api.write(
                    bucket=INFLUX_BUCKET,
                    org=INFLUX_ORG,
                    record=point
                )

                print(f"Written → Temp={temperature}°C | Humidity={humidity}%")

        except Exception as e:
            print(f"Runtime error: {e}", file=sys.stderr)

        time.sleep(POLL_INTERVAL)

if __name__ == "__main__":
    main()
    