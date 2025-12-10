import os
import time
from influxdb_client import InfluxDBClient, Point
from influxdb_client.client.write_api import SYNCHRONOUS

# 1. Load Credentials from Docker Environment
# We defined these in docker-compose.yml
URL = os.getenv("INFLUXDB_URL", "http://localhost:8086")
TOKEN = os.getenv("INFLUXDB_TOKEN", "my-super-secret-token")
ORG = os.getenv("INFLUXDB_ORG", "gridchaos_org")
BUCKET = os.getenv("INFLUXDB_BUCKET", "grid_telemetry")

class TelemetryClient:
    def __init__(self):
        try:
            self.client = InfluxDBClient(url=URL, token=TOKEN, org=ORG)
            self.write_api = self.client.write_api(write_options=SYNCHRONOUS)
            print(f"✅ Telemetry Connected to InfluxDB at {URL}")
        except Exception as e:
            print(f"❌ Telemetry Connection Failed: {e}")
            self.client = None

    def log_grid_state(self, voltage_pu, total_load, total_gen, status):
        """
        Pushes a data point to the database.
        """
        if not self.client:
            print("⚠️ Database not connected. Skipping log.")
            return

        # Create a Data Point
        # Measurement: "grid_health" (Table name)
        # Tag: "status" (Indexed column for filtering)
        # Fields: The actual numbers
        point = Point("grid_health") \
            .tag("status", status) \
            .field("min_voltage", float(voltage_pu)) \
            .field("total_load", float(total_load)) \
            .field("total_generation", float(total_gen)) \
            .time(time.time_ns())

        try:
            self.write_api.write(bucket=BUCKET, org=ORG, record=point)
        except Exception as e:
            print(f"⚠️ Failed to write metric: {e}")

# Initialize the client immediately
db = TelemetryClient()