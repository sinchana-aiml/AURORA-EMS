# 🌌 AURORA-EMS

## AI-Driven Energy Management System for Polar Research Stations

> **Smart India Hackathon 2026 — Problem Statement 26061**  
> **Theme:** Clean & Green Technology  
> **Category:** Software

AURORA-EMS is an AI-assisted Energy Management System designed for polar
research stations. It combines weather intelligence, a physics-informed
Digital Twin, renewable-energy forecasting, battery and generator modelling,
energy dispatch optimization, resilience mechanisms, and an interactive
3D operator dashboard.

The system is designed around one core objective:

> **Use available renewable energy intelligently, minimize diesel dependency,
> protect critical station loads, and continue safe operation during
> communication or component failures.**

---

## 🚀 Live Demo

### 🌐 Public Dashboard

**https://aurora-ems.vercel.app**

The public dashboard provides an interactive view of the AURORA-EMS prototype,
including:

- 🌍 Antarctic-focused 3D Digital Twin visualization
- ⚡ Station energy telemetry
- ☀️ Solar and 🌬️ wind contribution
- 🔋 Battery state of charge
- ⛽ Generator and fuel information
- 🤖 AI forecasting
- 🧠 Energy dispatch decisions
- 🛰️ Station connectivity and resilience status
- 📊 Energy and operational insights

### 🐙 Source Code

**https://github.com/sinchana-aiml/AURORA-EMS**

---

# 🎯 Problem

Polar research stations operate in harsh and isolated environments where:

- Renewable generation is highly dependent on weather.
- Diesel generators are often required for reliable power.
- Battery capacity and fuel availability are limited resources.
- Communication with external infrastructure may become unavailable.
- Critical scientific and life-support loads cannot simply be switched off.
- Operators need reliable forecasts and explainable energy decisions.

AURORA-EMS addresses these challenges through an integrated,
resilience-first energy-management architecture.

---

# 💡 Proposed Solution

AURORA-EMS combines multiple intelligent layers into a single energy
management workflow:

```text
Polar Weather Data
        ↓
Weather Validation
        ↓
Digital Twin
        ↓
Load / Solar / Wind / Battery / Generator Models
        ↓
AI Energy Forecasting
        ↓
24-Hour Energy Dispatch Optimization
        ↓
Resilience & Offline Safety Layer
        ↓
Operator Dashboard
```

The system continuously considers:

- Station demand
- Solar generation
- Wind generation
- Battery state of charge
- Generator availability
- Fuel availability
- Weather conditions
- Forecast uncertainty
- Critical and flexible loads
- Communication availability

---

# 🧠 Core Capabilities

## 🌍 Physics-Informed Digital Twin

The Digital Twin models the station's energy ecosystem, including:

- Station load
- Solar generation
- Wind generation
- Battery state
- Generator operation
- Fuel consumption
- Unmet load
- Critical-load protection

It provides a simulated representation of station energy behavior that can
be used for forecasting, optimization, and scenario testing.

---

## 🤖 AI Energy Forecasting

The forecasting layer estimates future:

- ⚡ Load demand
- ☀️ Solar generation
- 🌬️ Wind generation
- 🌡️ Weather conditions

Forecasts include uncertainty information and can operate using available
historical/weather information.

The system is also designed to support offline/fallback operation when
normal forecasting inputs become unavailable.

---

## ⚡ Energy Dispatch Optimization

The dispatch layer determines how the station should use:

1. Renewable generation
2. Battery storage
3. Generator 1
4. Generator 2
5. Flexible-load shedding when required

The optimization considers a 24-hour look-ahead horizon and attempts to
reduce diesel consumption while maintaining station reliability and
protecting critical loads.

The objective is not fuel minimization alone: critical-load protection and station reliability remain hard priorities when determining the dispatch strategy.

### Tested simulation example

For one validated 24-hour simulation dataset:

| Metric | Result |
|---|---:|
| Baseline diesel consumption | 158.19 L |
| Optimized diesel consumption | 81.50 L |
| Simulated reduction | 76.69 L |
| Simulated reduction percentage | 48.48% |
| Unmet load | 0 |
| Critical-load failures | 0 |

> **Important:** These values are results from a project simulation dataset.
> They are not guaranteed real-world savings or measurements from a polar
> research station.

A baseline-versus-optimized comparison is used to quantify the effect of the dispatch strategy on fuel consumption while monitoring unmet and critical load.

---

# 📴 Resilience & Offline-First Operation

Polar stations cannot depend completely on continuous external connectivity.

AURORA-EMS therefore includes a resilience layer capable of:

- Detecting connectivity status
- Using cached weather/station information
- Continuing local decision-making during communication loss
- Falling back to safe dispatch behavior
- Protecting critical loads
- Handling generator failures
- Handling low-fuel scenarios
- Handling storm scenarios
- Supporting recovery after reconnection

The system is designed so that loss of communication does not automatically
mean loss of local energy-management capability.

---

# 🖥️ Interactive Operator Dashboard

The AURORA-EMS dashboard is built as a polar research command center.

It provides:

- 🌌 Antarctic 3D globe
- 🌐 Digital Twin visualization
- ⚡ Live-style energy telemetry
- 🔋 Battery monitoring
- ⛽ Fuel monitoring
- ☀️ Renewable contribution
- 🤖 Forecast information
- 🧠 AI/optimization insights
- 🛰️ Resilience status
- 📊 Station-level operational information

The dashboard uses a dark polar-night visual design with aurora-inspired
visual elements and an Antarctic-focused 3D Earth.

---

# 🏗️ System Architecture

```text
                    ┌──────────────────────┐
                    │   Polar Weather Data │
                    │ NASA POWER / Future  │
                    │ Authorized Sources   │
                    └──────────┬───────────┘
                               ↓
                    ┌──────────────────────┐
                    │ Weather Validation   │
                    └──────────┬───────────┘
                               ↓
                    ┌──────────────────────┐
                    │    Digital Twin      │
                    │ Load / Solar / Wind  │
                    │ Battery / Generators │
                    └──────────┬───────────┘
                               ↓
              ┌────────────────┴────────────────┐
              ↓                                 ↓
     ┌──────────────────┐              ┌──────────────────┐
     │ AI Forecasting   │              │ Scenario Engine  │
     │ Load / Solar     │              │ Storm / Failure  │
     │ Wind / Weather   │              │ Low Fuel / etc.  │
     └────────┬─────────┘              └────────┬─────────┘
              └────────────────┬────────────────┘
                               ↓
                    ┌──────────────────────┐
                    │ Energy Optimization  │
                    │ 24h Dispatch         │
                    └──────────┬───────────┘
                               ↓
                    ┌──────────────────────┐
                    │ Resilience / Offline │
                    │ Safe Local Control   │
                    └──────────┬───────────┘
                               ↓
                    ┌──────────────────────┐
                    │ AURORA-EMS Dashboard │
                    │ React + Three.js     │
                    └──────────────────────┘
```

---

# 🛠️ Technology Stack

### Backend & AI

- Python
- Pandas
- NumPy
- Scikit-learn
- Joblib
- Flask
- OR-Tools
- Digital Twin simulation modules

### Frontend

- React
- TypeScript
- Vite
- Tailwind CSS
- Three.js
- React Three Fiber
- Plotly

### Data & Research

- NASA POWER weather data
- Polar weather validation pipeline
- Simulated station energy telemetry
- Future authorized station datasets

### Deployment

- **Frontend:** Vercel
- **Backend/API:** Render
- **Version Control:** Git + GitHub

---

# 🔐 Security & Privacy

Security and operational privacy are important considerations for a future
deployment in real polar research environments.

## Current Prototype

- The core prototype does not require personal user data.
- The public demonstration uses simulated station energy data.
- Weather inputs are sourced from available research/public data sources.
- Sensitive station infrastructure information is not required for the core
  demonstration.
- The architecture supports offline-first local operation.

## Planned Production Security

A production deployment is planned to include:

- 🔑 Secure authentication
- 👤 Role-Based Access Control (RBAC)
- 🛡️ API authentication and authorization
- 🔒 Encryption in transit and at rest
- 🗄️ Secure database access
- 🔐 Secure secret and API-key management
- 📋 Audit logs for important operational actions
- 🚨 Monitoring and security alerts
- 💾 Secure backup and recovery
- 📴 Local operation of critical functions during network outages

> The current public prototype should not be considered a production control
> system. Production deployment would require security review,
> authenticated infrastructure, appropriate authorization, encryption,
> operational validation, and station-specific safety requirements.

---

# 🤖 Planned RAG-Powered Research Assistant

A future version of AURORA-EMS will include a
**Retrieval-Augmented Generation (RAG)** layer.

The planned assistant will retrieve information from authorized knowledge
sources and provide grounded answers to operators and researchers.

Potential knowledge sources include:

- Station operating procedures
- Equipment manuals
- Maintenance documentation
- Energy-management documentation
- Safety procedures
- Approved research documents
- Historical operational reports

### Planned capabilities

- 📚 Document retrieval
- 🔎 Source-grounded answers
- 🧠 Explainable recommendations
- 📖 Equipment/procedure lookup
- ⚠️ Safety and operational guidance
- 🔗 References to retrieved sources
- 🔐 Access-controlled knowledge sources

> **RAG is a planned future capability and is not represented as a completed
> feature of the current public prototype.**

---

# 👤 Authentication & Database — Planned

The current public demonstration does not require user login.

A future production platform is planned to include:

- Secure user authentication
- Role-based access control
- Research-station user profiles
- Secure operational database
- Historical energy telemetry
- Forecast history
- Dispatch history
- Event and alert history
- Audit trails
- Configuration management
- Secure backup and recovery

The database will be designed so that access to sensitive station information
is controlled according to the user's authorization level.

---

# 🛰️ Real-World Data Integration

The current prototype uses simulated station energy data for development and
demonstration together with available polar weather inputs.

To move toward real-world validation, the team has contacted the
**National Centre for Polar and Ocean Research (NCPOR)** to request access
to appropriate original or authorized polar-station datasets.

The requested data would help us:

- Validate energy-demand forecasting
- Improve renewable-generation modelling
- Compare simulated and real station conditions
- Validate energy-dispatch strategies
- Improve the Digital Twin
- Evaluate performance under realistic polar operating conditions

> Real station data will only be incorporated subject to authorization,
> availability, applicable data-sharing requirements, and security/privacy
> restrictions.

Bharati is designed for year-round scientific research and supports personnel, laboratories, regulated power, heating, water, and communications, making station-specific operational data valuable for future validation of the model.

---

# 🧪 Testing & Validation

The project includes automated validation for major system layers,
including:

- Digital Twin behavior
- Weather processing
- Forecasting
- Dispatch optimization
- Resilience scenarios
- Failure conditions
- Integration between forecasting and dispatch
- Dashboard API
- Frontend build validation

The project has also been tested across scenarios such as:

- Normal operation
- Storm conditions
- Generator failure
- Low fuel
- Communication loss
- Combined failure scenarios
- Recovery after reconnection

---

# 📁 Repository Structure

```text
AURORA-EMS/
├── config.py
├── data/
├── docs/
├── models/
├── scripts/
├── frontend/
│   ├── public/
│   └── src/
├── src/
│   ├── api/
│   ├── digital_twin/
│   ├── dispatch/
│   ├── forecasting/
│   └── resilience/
├── tests/
├── requirements.txt
├── requirements-dev.txt
└── README.md
```

---

# 🚀 Local Development

## Backend

Create and activate a virtual environment:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

Install dependencies:

```powershell
python -m pip install -r requirements.txt
```

Start the API:

```powershell
gunicorn src.api.app:app
```

For local development, the API is available on the configured local port.

## Frontend

Open another terminal:

```powershell
cd frontend
npm install
npm run dev
```

The frontend communicates with the backend through the configured API proxy.

---

# 🌐 Deployment Architecture

The public application uses a split deployment architecture:

```text
                 ┌─────────────────────┐
                 │      Vercel         │
                 │ React + Vite        │
                 │ AURORA-EMS UI       │
                 └──────────┬──────────┘
                            │
                       /api/*
                            ↓
                 ┌─────────────────────┐
                 │      Render         │
                 │ Flask + Gunicorn    │
                 │ AI / Digital Twin   │
                 │ Forecast / Dispatch │
                 └─────────────────────┘
```

This separation allows the frontend and Python energy-management backend to
be deployed independently while maintaining a unified public dashboard.

---

# 🗺️ Development Roadmap

## ✅ Implemented

- [x] Physics-informed Digital Twin
- [x] Polar weather data pipeline
- [x] Weather validation
- [x] Renewable-energy forecasting
- [x] Battery modelling
- [x] Generator modelling
- [x] 24-hour dispatch optimization
- [x] Critical-load protection
- [x] Offline-first resilience
- [x] Failure and storm scenarios
- [x] Interactive 3D polar dashboard
- [x] React + Three.js frontend
- [x] Flask backend API
- [x] Vercel + Render deployment
- [x] Public demonstration dashboard

## 🔄 Planned

- [ ] Secure authentication
- [ ] Role-Based Access Control
- [ ] Production database
- [ ] Historical telemetry storage
- [ ] RAG-powered research assistant
- [ ] Source-grounded operational knowledge retrieval
- [ ] Advanced audit logging
- [ ] Production-grade security controls
- [ ] Real authorized NCPOR/station data integration
- [ ] Validation using real operational datasets
- [ ] IoT/hardware sensor integration
- [ ] Advanced predictive maintenance
- [ ] Multi-station support
- [ ] Advanced monitoring and alerting

---

# 👥 Team

## NavYantra-AURORA

| Role | Name |
|---|---|
| Team Leader | **Sinchana S** |
| Team Member | Sheethal Kaveramma IR |
| Team Member | Deekshitha S |
| Team Member | Shravya Ganiga |
| Team Member | Yuktha K K |
| Team Member | Sheela GR |

**Team ID:** 141076  
**Institution:** Sapthagiri NPS University

---

# 📌 Prototype Disclaimer

AURORA-EMS is a research and demonstration prototype.

The energy values, optimization results, and simulated station behavior shown
in the public dashboard are intended for demonstration and evaluation.
They should not be interpreted as operational measurements from an actual
polar research station or as a replacement for certified station control
systems.

Deployment in a real research station would require:

- Authorized real-world data
- Hardware integration
- Safety validation
- Cybersecurity review
- Authentication and access control
- Operational testing
- Domain-expert validation
- Compliance with applicable station requirements

---

# 🌱 Vision

AURORA-EMS aims to demonstrate how AI, Digital Twins, renewable-energy
forecasting, optimization, and resilient local control can work together to
support more efficient and reliable energy management in remote research
environments.

> **Predict the energy. Optimize the resources. Protect the critical loads.
> Keep the station resilient.** 🌌⚡