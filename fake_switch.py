import random
import time
from influxdb_client import InfluxDBClient, Point
from influxdb_client.client.write_api import SYNCHRONOUS

# ---- InfluxDB Config ----
INFLUX_URL = "http://172.17.0.1:8086"  # Use your InfluxDB IP if different
INFLUX_TOKEN = "2jawDJw6S4yVkuyaKRL4b5nrkz4m1CSji94K6wbpPpANNpWMcEV_wVkyIeBDvHd1t3kNKjoKJYY-xwyHXtioQw=="
INFLUX_ORG = "my-org"
INFLUX_BUCKET = "my-bucket"

# ---- Switch Simulation Config ----
SWITCH_MODELS = ["icx8100", "icx8200"]  # We will simulate both switches
PORTS = range(1, 25)
UPLINK_PORTS = [23, 24]  # These ports will have higher traffic
POE_PORTS = range(1, 13) # Assume ports 1-12 are PoE-enabled for APs
INTERVAL = 60  # seconds - reduced for faster data generation

# ---- InfluxDB Client Setup ----
client = InfluxDBClient(url=INFLUX_URL, token=INFLUX_TOKEN, org=INFLUX_ORG)
write_api = client.write_api(write_options=SYNCHRONOUS)

print("Starting comprehensive Ruckus switch simulator...")

# Initialize uptime counters for each switch
uptime_counters = {switch: 0 for switch in SWITCH_MODELS}

while True:
    all_points = [] # We will collect all points and write them in one batch

    for switch_name in SWITCH_MODELS:
        print(f"\n--- Generating data for switch: {switch_name} ---")

        # =============================================================
        # 1. SIMULATE CHASSIS-LEVEL METRICS (once per switch)
        # =============================================================
        uptime_counters[switch_name] += INTERVAL
        cpu = round(random.uniform(10.0, 25.0), 2)
        memory = round(random.uniform(30.0, 45.0), 2)
        temperature = round(random.uniform(40.0, 55.0), 2)
        
        # Simulate rare fan/psu failure (1 = OK, 0 = Failed)
        fan_status = random.choices([1, 0], weights=[0.999, 0.001], k=1)[0]
        psu_status = random.choices([1, 0], weights=[0.999, 0.001], k=1)[0]
        
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
        print(f"  CPU: {cpu}% | Memory: {memory}% | Temp: {temperature}C")

        # =============================================================
        # 2. SIMULATE PER-PORT METRICS (for each port)
        # =============================================================
        total_poe_power = 0.0
        for port in PORTS:
            # Simulate more realistic port status (most ports are up)
            status = random.choices([1, 0, 2], weights=[0.85, 0.10, 0.05], k=1)[0] # 85% up, 10% down, 5% empty

            traffic_in = 0.0
            traffic_out = 0.0
            errors = 0
            discards = 0
            poe_power = 0.0

            if status == 1: # Port is UP
                # Uplinks get high traffic
                if port in UPLINK_PORTS:
                    traffic_in = random.uniform(500_000_000, 950_000_000) # 500-950 Mbps
                    traffic_out = random.uniform(200_000_000, 700_000_000) # 200-700 Mbps
                # Regular ports get lower traffic
                else:
                    traffic_in = random.uniform(1_000_000, 75_000_000) # 1-75 Mbps
                    traffic_out = random.uniform(500_000, 20_000_000) # 0.5-20 Mbps

                # Simulate rare errors and discards
                errors = random.choices([0, random.randint(1, 5)], weights=[0.98, 0.02], k=1)[0]
                discards = random.choices([0, random.randint(1, 10)], weights=[0.97, 0.03], k=1)[0]

                # Simulate PoE power draw for connected devices
                if port in POE_PORTS:
                    poe_power = round(random.uniform(5.0, 12.0), 2) # Watts for an AP
                    total_poe_power += poe_power

            port_point = (
                Point("switch_port_metrics")
                .tag("switch", switch_name)
                .tag("port", f"port_{port}") # Using a clear name
                .field("status", status)
                .field("traffic_in_bps", float(traffic_in))
                .field("traffic_out_bps", float(traffic_out))
                .field("errors_in", errors)
                .field("discards_out", discards)
                .field("poe_power_watts", poe_power)
            )
            all_points.append(port_point)
        
        # Add a point for the total PoE power
        poe_total_point = Point("switch_chassis_metrics").tag("switch", switch_name).field("poe_total_power_watts", round(total_poe_power, 2))
        all_points.append(poe_total_point)
        print(f"  Total PoE Power: {round(total_poe_power, 2)}W")

    # Write all points for all switches in a single batch
    write_api.write(bucket=INFLUX_BUCKET, record=all_points)
    print(f"\nSuccessfully wrote {len(all_points)} data points to InfluxDB. Waiting {INTERVAL} seconds...")
    time.sleep(INTERVAL)