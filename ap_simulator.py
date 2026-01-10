# filename: ap_simulator.py (Ruckus R650 Realistic Simulator)

import random
import time
from influxdb_client import InfluxDBClient, Point
from influxdb_client.client.write_api import SYNCHRONOUS

# ---- InfluxDB Config ----
INFLUX_URL = "http://172.17.0.1:8086"
INFLUX_TOKEN = "2jawDJw6S4yVkuyaKRL4b5nrkz4m1CSji94K6wbpPpANNpWMcEV_wVkyIeBDvHd1t3kNKjoKJYY-xwyHXtioQw=="
INFLUX_ORG = "my-org"
INFLUX_BUCKET = "my-bucket"

# ---- R650 AP Simulation Config ----
TOTAL_APS = 10
AP_LOCATIONS = ["Lobby", "Cafeteria", "Conf-Room-A", "Conf-Room-B", "Warehouse", "Office-Wing-1", "Office-Wing-2", "Hallway", "Executive-Suite", "Break-Room"]
HIGH_DENSITY_AREAS = ["Lobby", "Cafeteria", "Conf-Room-A"] # These areas will have more clients
INTERVAL = 30  # seconds
SLOW_AP_THRESHOLD_UTILIZATION = 75 # We'll define a "slow" AP as one with >75% channel utilization

# ---- InfluxDB Client Setup ----
client = InfluxDBClient(url=INFLUX_URL, token=INFLUX_TOKEN, org=INFLUX_ORG)
write_api = client.write_api(write_options=SYNCHRONOUS)

print("--- Starting Ruckus R650 AP Simulator ---")

while True:
    all_points = []
    down_ap_count = 0
    slow_ap_count = 0

    print(f"\n[{time.ctime()}] Generating status for {TOTAL_APS} R650 APs...")

    for i in range(1, TOTAL_APS + 1):
        location = random.choice(AP_LOCATIONS)
        ap_name = f"{location}-AP-{i:02d}"

        ap_status = random.choices([1, 0], weights=[0.95, 0.05], k=1)[0] # 95% are online
        
        client_count = 0
        utilization_5ghz = 0.0
        throughput_mbps = 0.0
        
        if ap_status == 1: # Only online APs have performance metrics
            # Simulate more clients in high-density areas
            if location in HIGH_DENSITY_AREAS:
                client_count = random.randint(15, 40)
            else:
                client_count = random.randint(1, 15)

            # Simulate channel utilization - a key indicator of "slowness"
            # High-density areas are more likely to have high utilization
            if location in HIGH_DENSITY_AREAS and client_count > 20:
                 utilization_5ghz = round(random.uniform(50.0, 95.0), 2)
            else:
                 utilization_5ghz = round(random.uniform(5.0, 50.0), 2)
            
            # Simulate throughput based on clients and utilization
            throughput_mbps = round((client_count * random.uniform(2.0, 10.0)) * (1 - (utilization_5ghz / 120)), 2)
            if throughput_mbps < 0: throughput_mbps = 0

            # Define our condition for a "slow" AP
            if utilization_5ghz > SLOW_AP_THRESHOLD_UTILIZATION and client_count > 5:
                slow_ap_count += 1
                
        else: # AP is offline
            down_ap_count += 1
        
        # Create the data point with our new, realistic fields
        ap_point = (
            Point("ruckus_ap_metrics") # <-- NEW MEASUREMENT NAME
            .tag("ap_name", ap_name)
            .tag("location", location)
            .field("status", ap_status) # 1 for Online, 0 for Offline
            .field("client_count", client_count)
            .field("channel_utilization_5ghz", utilization_5ghz)
            .field("throughput_mbps", throughput_mbps)
        )
        all_points.append(ap_point)
    
    if all_points:
        write_api.write(bucket=INFLUX_BUCKET, record=all_points)
        print(f"  -> Wrote {len(all_points)} data points to InfluxDB.")
        print(f"  -> Total APs Offline: {down_ap_count}")
        print(f"  -> Total APs Slow (High Utilization): {slow_ap_count}")

    print(f"--- Waiting {INTERVAL} seconds... ---")
    time.sleep(INTERVAL)