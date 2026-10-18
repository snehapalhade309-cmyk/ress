# ResQAI — Emergency Management & Response System

**ResQAI** is a local-first, AI-powered emergency management and climate response decision-support system. It delivers real-time situational awareness, multi-factor risk assessment, intelligent fleet dispatch recommendations, and evacuation shelter routing without requiring external API keys.

---

## 🏛️ System Architecture

```text
┌────────────────────────────────────────────────────────────────────────┐
│                        RESQAI WEB DASHBOARD                            │
│  - Tactical Command Center KPI Overview                                │
│  - Interactive Leaflet Live Map (OpenStreetMap Tiles)                  │
│  - Real-Time Incident Reporting Form with Live Risk Gauge Meter        │
│  - Heuristic Risk Model Explorer & Simulation Sandbox                  │
│  - Smart Response Fleet Matrix & Collision-Free Dispatch Console       │
│  - Evacuation Shelters & Advisory Route Visualizer                     │
│  - Emergency Alert Center (Multilingual Templates: EN / HI / MR)      │
│  - Analytics & Operational Trends (Chart.js)                           │
│  - System Health & Integration Registry Dashboard                      │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │ HTTP / REST API
┌───────────────────────────────────▼────────────────────────────────────┐
│                       FLASK BACKEND REST ENGINE                        │
│  ├── /api/incidents           CRUD + Input Validation                  │
│  ├── /api/dispatch            Atomic Transaction Fleet Matching        │
│  ├── /api/shelters & routes   Evacuation Polyline Computation          │
│  ├── /api/weather             Open-Meteo Cache & Fallback Proxy        │
│  ├── /api/geocode             Nominatim Search & Anchor Resolver       │
│  ├── /api/health              Diagnostic Probe of System Components    │
│  └── /api/audit-logs          Immutable Activity & Audit Stream        │
└─────────┬───────────────────┬───────────────────┬──────────────────────┘
          │                   │                   │
┌─────────▼────────┐ ┌────────▼────────┐ ┌────────▼──────────────────────┐
│  AI RISK ENGINE  │ │ SMART DISPATCH  │ │  SQLITE PERSISTENCE LAYER     │
│  Deterministic   │ │ Capability Match│ │  - incidents (WAL Mode)       │
│  Heuristic Model │ │ Proximity/ETA   │ │  - resources (Fleet Units)    │
│  v2.1 Formula    │ │ Race-Cond. Lock │ │  - shelters & dispatches      │
└──────────────────┘ └─────────────────┘ └───────────────────────────────┘
```

---

## 🚀 Quickstart Guide for Windows PowerShell

Follow these step-by-step commands in **Windows PowerShell**:

### 1. Verify Python Installation
ResQAI requires Python 3.10 or higher.
```powershell
python --version
```

### 2. Set Up Virtual Environment
```powershell
# Create isolated environment
python -m venv venv

# Activate virtual environment
.\venv\Scripts\Activate.ps1
```
*(If PowerShell restricts script execution, run: `Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass`)*

### 3. Install Dependencies
```powershell
pip install -r requirements.txt
```

### 4. Run the Automated Test Suite
Verify all 13 unit tests and integration checks:
```powershell
python tests\run_all_tests.py
```

### 5. Launch the Application
```powershell
python run.py
```

### 6. Open the Command Center
Open your web browser and navigate to:
```
http://127.0.0.1:5000
```

---

## 🗺️ No-Mandatory-Key API Strategy

ResQAI runs reliably out-of-the-box in local and air-gapped environments. It queries free, documented, no-key public services with client caching and offline fallbacks:

| Service | Endpoint | Key Required? | Fallback Behavior |
| :--- | :--- | :--- | :--- |
| **OpenStreetMap Tiles** | `https://tile.openstreetmap.org/{z}/{x}/{y}.png` | **No** | Cached map tiles |
| **Open-Meteo Weather** | `https://api.open-meteo.com/v1/forecast` | **No** | In-memory 15m TTL cache; local meteorological baseline |
| **OSRM Driving Router** | `http://router.project-osrm.org/route/v1/driving` | **No** | Haversine direct geodesic waypoint interpolation |
| **Nominatim Geocoding** | `https://nominatim.openstreetmap.org/search` | **No** | Regional offline anchor coordinate dictionary |
| **Local AI (Ollama)** | `http://localhost:11434` | **No** | Deterministic rule-based tactical briefing synthesizer |

---

## 🔬 AI Risk Intelligence Formula

ResQAI employs a transparent, deterministic heuristic model (`ResQAI Deterministic Heuristic Model v2.1`):

$$\text{Risk Score} = \min\Big(100.0, \max\big(5.0, \text{Base} + \text{Sev} + \text{Pop} + \text{Vuln} + \text{Weather}\big)\Big)$$

- **Baseline Hazard Weight:** Flood (35), Landslide (40), Fire (35), Earthquake (45), Severe Weather (25), Accident (25).
- **Reported Urgency:** Minor (+5), Moderate (+15), Severe (+28), Catastrophic (+40).
- **Population Impact:** 0 (+2), 1–5 (+8), 6–20 (+16), 21–50 (+24), >50 (+30).
- **Vulnerability Needs:** Trapped (+15), Medical Oxygen (+12), Mobility Impaired (+9), Elderly (+7), Children (+6). Capped at +25.
- **Environmental Amplification:** Heavy Rain $\ge 15\text{ mm/hr}$ (+10 to +15 for flood/landslide), Gale Winds $\ge 40\text{ km/h}$ (+14 for fire/storm).

### Tier Thresholds:
- **Low (5.0 – 29.9):** Minor disruption; advisory monitoring.
- **Medium (30.0 – 54.9):** Localized infrastructure damage; standard queue.
- **High (55.0 – 77.9):** Severe hazard envelope; priority response unit mobilized.
- **Critical (78.0 – 100.0):** Immediate threat to human life; automatic high-urgency alerts and instant tactical dispatch recommendation.

---

## ⏱️ 3-Minute Live Demonstration Script

1. **Overview & Baseline:**
   - Open `http://127.0.0.1:5000`.
   - Point out the active KPI cards, live weather widget, and priority queue table.
2. **Report New Flood Incident:**
   - Click **Report Emergency** on the top navigation bar.
   - Select Hazard Type: `Flood / Flash Inundation`.
   - Urgency: `Severe`.
   - Location: `Sangvi River Basin Lowlands`.
   - Coordinates: Click `Use My Browser GPS Coordinates` or enter `18.5700, 73.8100`.
   - Affected People: `35`.
   - Toggle Vulnerabilities: Select `Trapped / Waterbound` and `Elderly Citizens`.
   - Observe the **Live Risk Scoring Preview** dynamically adjust to **CRITICAL RISK (92.0)** with calculated factor points.
   - Click **Submit Incident to Command Net**.
3. **Inspect Situation & Dispatch Resource:**
   - The new incident immediately appears in the Command Center queue and on the **Live Map**.
   - Click **Inspect & Dispatch** on the incident row.
   - The modal reveals the AI Situation Brief and ranked recommendations.
   - Notice the top candidate: `Gemini Inflatable Flood Rescue Craft 201` (high suitability score for water rescue).
   - Click **Dispatch Unit**.
4. **Collision Prevention & In-App Alert:**
   - A success notification confirms unit deployment.
   - The in-app **Alert Center** generates a critical notification.
   - In the **Smart Dispatch** tab, the rescue craft status switches to `DISPATCHED`.
   - Any attempt to double-dispatch the unit to another incident is blocked by the atomic database lock.
5. **Evacuation Routing:**
   - Navigate to **Shelters & Routes**.
   - Select the flood incident and `Balewadi Sports Complex Evacuation Center`.
   - Click **Calculate Evacuation Route**. The system renders the advisory driving path on the Leaflet map with distance and estimated transit time.
6. **Data Persistence:**
   - Press `F5` to refresh the browser. All records, dispatches, alerts, and audit logs persist reliably in the SQLite database.

---

## 🛡️ Governance, Safety & Disclosures

- **Decision Support Only:** ResQAI provides advisory decision support. Operational directives must adhere to certified emergency response commanders.
- **Simulated Fleet Units:** Emergency vehicles and response teams are clearly labeled simulated assets for simulation, planning, and evaluation.
- **Evacuation Advisory:** Routing calculations do not guarantee physical road passability or safe water depths during severe floods. Field reconnaissance is required.
