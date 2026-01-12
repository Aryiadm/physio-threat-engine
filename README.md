# SignalZero: Physio Threat Intelligence Engine

[Design Doc](https://docs.google.com/document/d/1AY0WEyM2We4BQ3Y9mxXZIPS_7u6C-_lcTHyvLGck0b0/edit?usp=sharing)


## Zero-Trust Health Data Pipeline • AI-Driven Signal Integrity & Anomaly Detection

SignalZero is an intelligent health & wellness aggregation platform that reframes personal health data as untrusted telemetry and applies security-grade, zero-trust ML techniques before generating insights.

Instead of assuming wearable and app data is clean, this system evaluates signal integrity, trustworthiness, and coherence across sources, mirroring how modern cybersecurity platforms reason about hostile or unreliable inputs.

Just as a firewall doesn't trust incoming packets, SignalZero doesn't trust incoming health data. Just as a SIEM correlates events across logs, we correlate signals across metrics. Just as IDS assigns threat scores, we assign trust scores. This isn't a health app that happens to be secure—it's a security platform applied to health data.


### Problem

Health-conscious individuals rely on data from many disconnected sources — wearables for sleep and activity, apps for nutrition, smart scales for weight, and sensors for heart metrics.

However, this data is:

- noisy and incomplete

- delayed or backfilled

- inconsistent across devices

- prone to drift and logging errors

As a result, traditional health dashboards often produce misleading correlations and false insights.

### Solution
_**🚀  Treat health data like untrusted network traffic 🚀**_

Physio Threat Intelligence applies a zero-trust ingestion model inspired by AI-driven cybersecurity systems:

- No signal is trusted by default

- Every metric receives a confidence score

- Anomalies are contextualized, not blindly flagged

The system degrades gracefully under corrupted or adversarial data
#### Key Features
**🚨 Signal Trust Scoring**

Each health metric (sleep, steps, calories, weight, etc.) is assigned a trust score based on:

- historical consistency

- missingness patterns

- distribution shifts

- cross-signal coherence

Low-trust signals are down-weighted instead of blindly used.

**🚨 Proactive Anomaly Detection**

Anomalies are detected relative to a user’s own historical baseline using robust statistics.
Each alert includes:

- anomaly severity

- contributing signals

- an explanatory narrative

This reduces false positives and improves interpretability.

**🚨  Cross-Signal Correlation Analysis**

The system analyzes relationships across metrics to:

- surface meaningful health interactions

- detect incoherent or suspect signals

- distinguish true health events from sensor failures

**🚨  Adversarial Simulation Mode**

The platform can intentionally inject:

- missing data (packet loss)

- delayed uploads (latency)

- spoofed values (data poisoning)

- random noise (sensor drift)

resilience under hostile conditions — a core security concept.

**🚨 Unified Observability Dashboard**

A security-style dashboard visualizes:

- health trends

- trust scores

- anomalies

- correlations

- simulation results

The UI is intentionally designed to resemble observability and threat-intelligence tooling, not a consumer fitness app.

## **Demo** 


https://github.com/user-attachments/assets/eaa4afe3-359d-4ea2-83df-360252dcd018



## Zero-Trust Security: 
Privacy-first design with differential privacy guarantees and encrypted transmission
<img width="1299" height="856" alt="Screenshot 2026-01-11 at 4 01 17 PM" src="https://github.com/user-attachments/assets/f06a339d-aaf1-42fd-b844-92ba0ebe70f4" />

## Health-board
Unified dashboard correlating long‑term trends (sleep vs. energy) with today’s health vector, demonstrating how the platform integrates disparate data streams into a single holistic view.
<img width="1609" height="726" alt="Screenshot 2026-01-11 at 4 06 00 PM" src="https://github.com/user-attachments/assets/7d14fb8a-7d37-4c8e-82eb-e0f5520b8f8d" />

## Signal Trust Scores
Confidence scoring of individual signals based on consistency, missingness and cross‑signal coherence. Low‑trust signals are down‑weighted, mirroring zero‑trust principles
<img width="1602" height="746" alt="Screenshot 2026-01-11 at 4 07 21 PM" src="https://github.com/user-attachments/assets/b37b6e92-fe86-48bf-9044-1e959a0d9c26" />

## Anomaly Detection
Proactive anomaly detection using robust baselines and explanatory narratives. Highlights how deviations are contextualized to reduce false positives
<img width="1578" height="773" alt="Screenshot 2026-01-11 at 4 08 23 PM" src="https://github.com/user-attachments/assets/052801ea-e038-4472-92e7-93657250c864" />

## Cross Signal Correlations
Cross‑signal analysis uncovering relationships between metrics and detecting incoherent or suspect signals, similar to how security platforms correlate multiple telemetry sources
<img width="1599" height="585" alt="Screenshot 2026-01-11 at 4 08 59 PM" src="https://github.com/user-attachments/assets/6fcf0e54-cb3e-4947-ae88-a2878fb1de7b" />

## Adversarial Simulation
Adversarial simulation mode that injects missing, delayed, spoofed or noisy data to test resilience
<img width="1579" height="689" alt="Screenshot 2026-01-11 at 4 10 02 PM" src="https://github.com/user-attachments/assets/9165a0a0-04f4-4aaf-8b65-2c2b52d65904" />




# 🚀 Local Installation & Running the App
This project follows a decoupled architecture: a PyTorch-based Inference Engine (Backend) and a Next.js Reactive Dashboard (Frontend).

📋 Prerequisites
- Python 3.10+ 
- Node.js v20.x
- NVM 

**1. Clone the Repository**

**2. Run Backend: Physio-Threat Intelligence Engine**
The backend serves the ML model predictions and handles adversarial signal simulations.

_Navigate to the backend_
cd backend

_Create and isolate the environment_
```python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
```

_Install dependencies (PyTorch, FastAPI, etc.)_
```pip install -r requirements.txt
```

_Start the Uvicorn server (Defaults to http://127.0.0.1:8000)_
```uvicorn app:app --reload```

**3.Run Frontend (health vector dashboard)**
The UI provides real-time visualization of health data and anomaly detection alerts.

_Open a new terminal and navigate to frontend_
cd frontend

_Ensure you are on the correct Node version_
nvm use 20 

_Install dependencies and start the dev server_
```cd frontend
npm install
npm run dev
```

**4. Running App**
Once both services are running, the application is accessible at:
👉 Dashboard: http://localhost:3000
👉 API Docs (Swagger): http://localhost:8000/docs

