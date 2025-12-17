# ⚡ GridChaos: Distributed Resilience Orchestrator

> **A Microservices-based Chaos Engineering Platform for the US Power Grid.** > _Featuring Generative AI Root Cause Analysis & Historical Failure Simulation._

![GridChaos Demo](docs/demo.gif)

## 🚀 Mission

GridChaos is a **Digital Twin** of the NY Power Grid designed to simulate systemic risk. It orchestrates cascading failures—like **Hurricane Ida** or **Cyber-Physical Attacks**—to measure the "Blast Radius" of critical infrastructure collapse in real-time.

## 🏗️ Architecture (The Stack)

- **Orchestrator:** Docker Compose (Service Mesh)
- **Compute Engine:** Python 3.10 + Pandapower (Newton-Raphson Solver)
- **Control Plane:** FastAPI (REST Interface)
- **Telemetry Store:** InfluxDB (Time-Series Database)
- **Observability:** Grafana (Real-time Dashboards)
- **Mission Control:** Streamlit (Operator UI with Dark Mode)
- **AIOps:** Google Gemini Flash (Generative AI SRE Agent)

## ⚡ Core Capabilities

### 1. "War Room" Scenarios (Historical Re-enactment)

Simulates real-world Con Edison failure modes based on NYISO reports:

- **🌊 Hurricane Ida (2021):** Flash flooding trips critical transmission corridors (Lines 0 & 1).
- **🔥 Heatwave (2023):** External grid voltage sag + Reactive power exhaustion.
- **⚡ EV Fleet Spike (2024):** Synchronized 40MW load step-change on weak buses.
- **🌲 Northeast Blackout (2003):** Vegetation contact triggering cascading line trips.

### 2. The AI SRE Agent 🤖

Integrated **LLM-based Incident Response**.

- Ingests real-time voltage/frequency telemetry.
- Performs automated **Root Cause Analysis (RCA)**.
- Suggests remediation steps (e.g., "Load Shedding target: 15%").

### 3. Engineering Rigor

- **CI/CD:** GitHub Actions pipeline running `pytest` regression suites on the physics engine.
- **Hot Reload:** Optimized Docker volume mounting for <1s developer feedback loops.
- **Observability:** Sub-3-second latency from Fault Injection to Grafana Alert.

## 🛠️ Quick Start

### Prerequisites

- Docker Desktop
- Git
- (Optional) Google Gemini API Key

### Deployment

```bash
# 1. Clone the repo
git clone https://github.com/Mohammad-Maniruzzaman/grid-chaos-monkey.git

# 2. Launch the Fleet
docker compose up -d --build

# 3. Access the Interfaces
# UI: http://localhost:8501
# API: http://localhost:8000/docs
# Grafana: http://localhost:3000 (admin/password123)
```
