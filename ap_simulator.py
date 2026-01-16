# filename: ap_simulator.py (Ruckus R650 Realistic Simulator)

import random
import time
import os
from dotenv import load_dotenv

from influxdb_client import InfluxDBClient, Point
from influxdb_client.client.write_api import SYNCHRONOUS

# Load env vars
load_dotenv()

def get_env(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise RuntimeError(f"Missing required env variable: {name}")
    return value

# ---- InfluxDB Config (FROM ENV) ----
INFLUX_URL = get_env("INFLUX_URL")
INFLUX_TOKEN = get_env("INFLUX_TOKEN")
INFLUX_ORG = get_env("INFLUX_ORG")
INFLUX_BUCKET = get_env("INFLUX_BUCKET")

# ---- Simulator Config ----
TOTAL_APS = int(os.getenv("TOTAL_APS", 10))
INTERVAL = int(os.getenv("INTERVAL", 30))
SLOW_AP_THRESHOLD_UTILIZATION = int(os.getenv("SLOW_AP_THRESHOLD_UTILIZATION", 75))

AP_LOCATIONS = [
    "Lobby", "Cafeteria", "Conf-Room-A", "Conf-Room-B",
    "Warehouse", "Office-Wing-1", "Office-Wing-2",
    "Hallway", "Executive-Suite", "Break-Room"
]

HIGH_DENSITY_AREAS = ["Lobby", "Cafeteria", "Conf-Room-A"]

# ---- InfluxDB Client ----
client = InfluxDBClient(
    url=INFLUX_URL,
    token=INFLUX_TOKEN,
    org=INFLUX_ORG
)
write_api = client.write_api(write_options=SYNCHRONOUS)

print("--- Starting Ruckus R650 AP Simulator ---")

while True:
    all_points = []
    down_ap_count = 0
    slow_ap_count = 0

    print(f"\n[{time.ctime()}] Generating status for {TOTAL_APS} APs")

    for i in range(1, TOTAL_APS + 1):
        location = random.choice(AP_LOCATIONS)
        ap_name = f"{location}-AP-{i:02d}"

        ap_status = random.choices([1, 0], weights=[95, 5], k=1)[0]

        client_count = 0
        utilization_5ghz = 0.0
        throughput_mbps = 0.0

        if ap_status == 1:
            client_count = (
                random.randint(15, 40)
                if location in HIGH_DENSITY_AREAS
                else random.randint(1, 15)
            )

            utilization_5ghz = round(
                random.uniform(50, 95) if location in HIGH_DENSITY_AREAS else random.uniform(5, 50),
                2
            )

            throughput_mbps = round(
                (client_count * random.uniform(2, 10)) * (1 - utilization_5ghz / 120),
                2
            )
            throughput_mbps = max(throughput_mbps, 0)

            if utilization_5ghz > SLOW_AP_THRESHOLD_UTILIZATION and client_count > 5:
                slow_ap_count += 1
        else:
            down_ap_count += 1

        point = (
            Point("ruckus_ap_metrics")
            .tag("ap_name", ap_name)
            .tag("location", location)
            .field("status", ap_status)
            .field("client_count", client_count)
            .field("channel_utilization_5ghz", utilization_5ghz)
            .field("throughput_mbps", throughput_mbps)
        )

        all_points.append(point)

    write_api.write(bucket=INFLUX_BUCKET, record=all_points)

    print(f"Written points: {len(all_points)}")
    print(f"APs Offline: {down_ap_count}")
    print(f"APs Slow: {slow_ap_count}")
    print(f"Sleeping {INTERVAL}s...\n")

    time.sleep(INTERVAL)
