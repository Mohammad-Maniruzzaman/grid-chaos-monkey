# 🚨 Incident Report: GRID-2025-001

| Field                     | Details                                 |
| ------------------------- | --------------------------------------- |
| **Incident Date**         | Dec 11, 2025                            |
| **Severity**              | SEV-1 (Critical Availability Failure)   |
| **Status**                | RESOLVED                                |
| **Component**             | GridChaos Orchestrator (US-East Region) |
| **TTD (Time to Detect)**  | < 3 seconds                             |
| **TTR (Time to Resolve)** | 4 minutes                               |

---

## 1. Executive Summary

At **14:00 UTC**, the GridChaos platform experienced a **catastrophic voltage collapse (Blackout)** across the IEEE 14-Bus System. The failure resulted in a complete loss of power flow convergence.

Telemetry indicates the root cause was a **Cascading Failure scenario**: A cyber-induced load spike (1.8x) saturated the reactive power reserves, followed immediately by a physical severance of Transmission Line #1 (Bus 1 -> Bus 2).

## 2. Timeline

- **T-00:00** - Baseline Grid Operation (Voltage: 1.01 p.u., Status: HEALTHY).
- **T+00:30** - **INJECTION:** "Botnet" Load Spike initiated via Control Plane (1.8x multiplier).
- **T+00:35** - **ALERT:** Grafana Dashboard triggered "Low Voltage" alert (0.94 p.u.).
- **T+01:00** - **INJECTION:** Physical sabotage of Line #1 triggered via Chaos Monkey.
- **T+01:05** - **OUTAGE:** Physics Engine returned `None` (Divergence). API logged `status="BLACKOUT"`.
- **T+04:00** - Operator initiated "System Reset". Grid restored to nominal state.

## 3. Root Cause Analysis (5 Whys)

1.  **Why did the grid crash?**
    - Demand exceeded the system's ability to transmit power (Voltage Collapse).
2.  **Why did it exceed capacity?**
    - A massive load spike (1.8x) occurred simultaneously with a transmission line loss.
3.  **Why did the transmission line fail?**
    - Intentional Fault Injection test (Chaos Engineering).
4.  **Why was the impact so severe?**
    - Line #1 carries the bulk of power from the Slack Generator. Losing it while under load removed the primary power corridor.

## 4. Evidence

_See attached screenshot: `evidence_graph.png`_

- **Graph A:** Shows voltage plummeting from 1.01 to 0.0.
- **Graph B:** Shows Load vs Generation delta widening before collapse.

## 5. Corrective Actions

- **[Immediate]** System Reset performed.
- **[Feature Request]** Implement automated "Load Shedding" (Circuit Breakers) in `simulation.py` to prevent blackout when Voltage < 0.85.
- **[Process]** Update Runbook to require N-1 contingency checks before injecting load spikes > 1.5x.

---

_Report generated via GridChaos Resilience Platform_
