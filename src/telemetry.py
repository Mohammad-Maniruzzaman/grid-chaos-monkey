import os
import time
from influxdb_client import InfluxDBClient, Point
from influxdb_client.client.write_api import SYNCHRONOUS

URL = os.getenv("INFLUXDB_URL", "http://localhost:8086")
TOKEN = os.getenv("INFLUXDB_TOKEN", "")
ORG = os.getenv("INFLUXDB_ORG", "gridchaos_org")
BUCKET = os.getenv("INFLUXDB_BUCKET", "grid_telemetry")

V_UNSTABLE = float(os.getenv("V_UNSTABLE", "0.95"))
V_CRITICAL = float(os.getenv("V_CRITICAL", "0.90"))


class TelemetryClient:
    def __init__(self):
        try:
            self.client = InfluxDBClient(url=URL, token=TOKEN, org=ORG)
            self.write_api = self.client.write_api(write_options=SYNCHRONOUS)
            print(f"✅ Telemetry Connected to InfluxDB at {URL}")
        except Exception as e:
            print(f"❌ Telemetry Connection Failed: {e}")
            self.client = None

    def log_grid_state(self, ctx, voltage_pu, total_load, total_gen, status, converged, solve_time_ms):
        """
        Logs grid state with experiment correlation context.

        ctx keys:
          - experiment_id, scenario, phase, simulation_id, mutation_source
        """
        if not self.client:
            return

        point = (
            Point("grid_health")
            .tag("experiment_id", str(ctx.get("experiment_id", "none")))
            .tag("scenario", str(ctx.get("scenario", "none")))
            .tag("phase", str(ctx.get("phase", "baseline")))
            .tag("simulation_id", str(ctx.get("simulation_id", "none")))
            .tag("mutation_source", str(ctx.get("mutation_source", "unknown")))
            .tag("status", str(status))
            .field("min_voltage", float(voltage_pu))
            .field("total_load", float(total_load))
            .field("total_generation", float(total_gen))
            .field("converged", bool(converged))
            .field("solve_time_ms", float(solve_time_ms))
            .field("v_unstable", float(V_UNSTABLE))
            .field("v_critical", float(V_CRITICAL))
            .field("voltage_slo_violation", float(voltage_pu < V_UNSTABLE))
            .time(time.time_ns())
        )

        try:
            self.write_api.write(bucket=BUCKET, org=ORG, record=point)
        except Exception:
            pass


db = TelemetryClient()
