import random
import time
import os
from dotenv import load_dotenv

from influxdb_client import InfluxDBClient, Point
from influxdb_client.client.write_api import SYNCHRONOUS

# -------------------------------------------------
# Load environment variables
# -------------------------------------------------
load_dotenv()

def get_env(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise RuntimeError(f"Missing required env variable: {name}")
    return value

# -------------------------------------------------
# InfluxDB Config (FROM ENV)
# -------------------------------------------------
INFLUX_URL = get_env("INFLUX_URL")
INFLUX_TOKEN = get_env("INFLUX_TOKEN")
INFLUX_ORG = get_env("INFLUX_ORG")
INFLUX_BUCKET = get_env("INFLUX_BUCKET")

INTERVAL = int(os.getenv("INTERVAL", 60))

# -------------------------------------------------
# Switch Simulation Config
# -------------------------------------------------
SWITCH_MODELS = ["icx8100", "icx8200"]
PORTS = range(1, 25)
UPLINK_PORTS = [23, 24]
POE_PORTS = range(1, 13)

# -------------------------------------------------
# InfluxDB Client
# -------------------------------------------------
client = InfluxDBClient(
    url=INFLUX_URL,
    token=INFLUX_TOKEN,
    org=INFLUX_ORG
)
write_api = client.write_api(write_options=SYNCHRONOUS)

print("Starting Ruckus switch simulator (env-driven, safe)")

# Uptime counters
uptime_counters = {switch: 0 for switch in SWITCH_MODELS}

while True:
    all_points = []

    for switch_name in SWITCH_MODELS:
        uptime_counters[switch_name] += INTERVAL

        cpu = round(random.uniform(10.0, 25.0), 2)
        memory = round(random.uniform(30.0, 45.0), 2)
        temperature = round(random.uniform(40.0, 55.0), 2)

        fan_status = random.choices([1, 0], weights=[999, 1], k=1)[0]
        psu_status = random.choices([1, 0], weights=[999, 1], k=1)[0]

        chassis_point = (
            Point("switch_chassis_metrics")
            .tag("switch", switch_name)
            .field("cpu_utilization", cpu)
            .field("memory_utilization", memory)
            .field("temperature_celsius", temperature)
            .field("uptime_seconds", uptime_counters[switch_name])
            .field("fan_status", fan_status)
            .field("psu_status", psu_status)
        )
        all_points.append(chassis_point)

        total_poe_power = 0.0

        for port in PORTS:
            status = random.choices([1, 0, 2], weights=[85, 10, 5], k=1)[0]

            traffic_in = traffic_out = poe_power = 0.0
            errors = discards = 0

            if status == 1:
                if port in UPLINK_PORTS:
                    traffic_in = random.uniform(500e6, 950e6)
                    traffic_out = random.uniform(200e6, 700e6)
                else:
                    traffic_in = random.uniform(1e6, 75e6)
                    traffic_out = random.uniform(0.5e6, 20e6)

                errors = random.choices([0, random.randint(1, 5)], weights=[98, 2], k=1)[0]
                discards = random.choices([0, random.randint(1, 10)], weights=[97, 3], k=1)[0]

                if port in POE_PORTS:
                    poe_power = round(random.uniform(5.0, 12.0), 2)
                    total_poe_power += poe_power

            port_point = (
                Point("switch_port_metrics")
                .tag("switch", switch_name)
                .tag("port", f"port_{port}")
                .field("status", status)
                .field("traffic_in_bps", float(traffic_in))
                .field("traffic_out_bps", float(traffic_out))
                .field("errors_in", errors)
                .field("discards_out", discards)
                .field("poe_power_watts", poe_power)
            )
            all_points.append(port_point)

        poe_point = (
            Point("switch_chassis_metrics")
            .tag("switch", switch_name)
            .field("poe_total_power_watts", round(total_poe_power, 2))
        )
        all_points.append(poe_point)

    write_api.write(bucket=INFLUX_BUCKET, record=all_points)
    print(f"Wrote {len(all_points)} points. Sleeping {INTERVAL}s…")
    time.sleep(INTERVAL)
