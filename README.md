# Commercial Fleet Operations & Turnaround Optimization Model

[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![SQLite 3](https://img.shields.io/badge/sqlite-3-003B57.svg)](https://www.sqlite.org/)
[![Scikit-Learn](https://img.shields.io/badge/scikit--learn-1.0+-F7931E.svg)](https://scikit-learn.org/)
[![FAA Benchmark](https://img.shields.io/badge/FAA%20Cost%20Standard-$75%2Fmin-red.svg)](https://www.faa.gov/)
[![Potential Cost Savings](https://img.shields.io/badge/Annual%20Savings-$10.24M-success.svg)](#financial-translation--roi-dashboard)

An enterprise machine learning and analytical SQL engine designed for airline **Operations Control Centers (OCC)** to detect, predict, and mitigate turnaround buffer breaches and cascading schedule delays across commercial aircraft rotations.

---

## System Architecture & Workflow

```mermaid
flowchart TD
    subgraph S1["Stage 1: Raw Ingestion & Telemetry Normalization"]
        A[("Raw DOT BTS Carrier Data<br/>441,348 Flight Records")] --> B["src/db_setup.py<br/>Time-Series Parser"]
        B --> C{"Filter Status & Normalize<br/>Cancelled / Diverted / Rollovers"}
        C --> D[("SQLite: operations.db<br/>B-Tree Indexed on Tail & Time")]
    end

    subgraph S2["Stage 2: Analytical SQL Engine (Aircraft Sequencing)"]
        D --> E["sql/turnaround_analytics.sql<br/>Window Functions & CTEs"]
        E --> F["LAG() by Tail_Number<br/>Prior Flight Arrival State"]
        F --> G["Turnaround & Buffer Delta<br/>Prior_Dest == Current_Origin"]
        G --> H["Network Choke Point Discovery<br/>DTW 27.1% | ORD 22.0% | ATL 22.7%"]
    end

    subgraph S3["Stage 3: Predictive ML Engine (Feature Architecture)"]
        D & G --> I["Feature Engineering Pipeline<br/>Inbound Delay (42.2%) | Congestion (15.8%)"]
        I --> J["Random Forest Classifier<br/>Balanced Class Weights (60/40 Split)"]
        J --> K["Stratified Evaluation (88,270 Test Flights)<br/>PR-AUC: 81.9% | Precision: 78.4% | F1: 71.7%"]
    end

    subgraph S4["Stage 4: Operations Dispatch & Financial ROI"]
        K --> L["Dispatch Alert Gateway<br/>Turn Breach Probability &gt; 60%"]
        L --> M{"Tactical Ground Interventions<br/>Crew Surges | Gate Swaps | Fast Boarding"}
        M --> N["FAA Delay Cost Benchmark<br/>$75/min * 682,723 True Positive Minutes"]
        N --> O(("Quantified Annual Cost Mitigation<br/>$10,240,845 ($10.2M ROI)"))
    end

    %% Visual Styling
    classDef stageIng fill:#e0f2fe,stroke:#0284c7,stroke-width:2px,color:#0369a1;
    classDef stageSql fill:#f3e8ff,stroke:#9333ea,stroke-width:2px,color:#6b21a8;
    classDef stageMl fill:#fef3c7,stroke:#d97706,stroke-width:2px,color:#92400e;
    classDef stageRoi fill:#dcfce7,stroke:#16a34a,stroke-width:2px,color:#15803d;
    classDef finalRoi fill:#fef08a,stroke:#ca8a04,stroke-width:3px,color:#854d0e;

    class A,B,C,D stageIng;
    class E,F,G,H stageSql;
    class I,J,K stageMl;
    class L,M,N stageRoi;
    class O finalRoi;
```

---

## Executive Summary & Problem Landscape

### The Domino Effect: How Ground Turns Propagate Network Delays
Commercial airlines operate with hyper-compressed aircraft utilization schedules. A single aircraft rotation typically executes between **4 to 7 flights per day**.
- **The Turnaround Buffer**: The scheduled ground window (typically 45–60 minutes) allocated for deplaning, baggage offloading, aircraft cleaning, refueling, catering, baggage loading, and passenger boarding.
- **Buffer Exhaustion**: When an aircraft arrives late or ground operations suffer friction, the scheduled turn buffer collapses.
- **The Cascading Delay**: If an aircraft arrives 25 minutes late and ground turnaround requires 50 minutes against a scheduled 45-minute window, the outbound flight incurs a 30-minute departure delay. This deficit compounds across downstream rotations, triggering missed passenger connections, crew duty-hour timeouts, and severe operational penalties.
- **Industry Cost Standard**: According to the **Federal Aviation Administration (FAA)** and **Airlines for America (A4A)**, the direct operational cost of aircraft delay averages **$75.00 per minute** (fuel burn, crew overtime wages, gate hold fees, and passenger re-accommodation).

---

## Technical Methodology & Engineering Pipeline

### Stage 1: Data Ingestion & Time-Series Normalization (`src/db_setup.py`)
- Ingests raw Bureau of Transportation Statistics (BTS) on-time performance records (**441,348 flight events**).
- **Edge-Case Resolution**:
  - Converts integer/float time expressions (`1530.0` $\rightarrow$ `15:30:00`).
  - Resolves midnight 24-hour rollover anomalies (`2400` $\rightarrow$ `00:00:00`).
  - Corrects cross-midnight overnight arrivals (`CRSDepTime > CRSArrTime`).
- Normalizes records into an optimized SQLite database (`operations.db`) with `WAL` journal mode and compound B-Tree indexes on `(Tail_Number, Scheduled_Departure)` for sub-second window queries.

### Stage 2: Analytical SQL Sequencing Engine (`sql/turnaround_analytics.sql`)
Instead of slow row-by-row iteration in Python, flight rotations are reconstructed directly within SQLite using Common Table Expressions (CTEs) and C-optimized window functions:
```sql
LAG(Actual_Arrival) OVER (
    PARTITION BY Tail_Number 
    ORDER BY Scheduled_Departure
) AS Prior_Actual_Arrival
```
- **Physical Aircraft Continuity**: Enforces `Prior_Dest = Current_Origin` and constrains valid ground turns to operational windows ($30 \le \Delta t \le 720$ minutes).
- **Mathematical Buffer Delta**:
  $$\text{Ground Buffer Delta} = \text{Scheduled Turnaround (min)} - \text{Actual Turnaround (min)}$$
- **Cascading Delay Isolation**: Flags events where inbound delay $> 15$ minutes directly forces departure delay $> 15$ minutes.

#### Major Hub Choke Points Identified:
| Airport Hub | Carrier Code | Total Turns | Avg Scheduled Turn | Avg Actual Turn | Cascading Delay % |
| :--- | :--- | :---: | :---: | :---: | :---: |
| **DTW** (Detroit) | OO | 1,902 | 48.5 min | 61.2 min | **27.08%** |
| **PBI** (Palm Beach) | B6 | 731 | 54.1 min | 68.4 min | **26.13%** |
| **DCA** (Reagan National) | B6 | 501 | 49.3 min | 62.0 min | **24.95%** |
| **ASE** (Aspen) | OO | 713 | 46.2 min | 58.7 min | **24.40%** |
| **ATL** (Atlanta) | F9 | 1,267 | 52.4 min | 65.1 min | **22.65%** |
| **ORD** (Chicago O'Hare) | OO | 4,001 | 50.8 min | 63.4 min | **21.97%** |
| **MIA** (Miami) | DL | 965 | 55.3 min | 67.8 min | **20.31%** |
| **EWR** (Newark) | NK | 649 | 51.0 min | 64.2 min | **19.88%** |

---

### Stage 3: Predictive Machine Learning Engine (`src/train_model.py`)
Predicts whether an incoming aircraft will breach its turnaround buffer and generate downstream delays before touchdown, giving station control centers a **60–90 minute intervention lead time**.

#### Feature Importance Contributions:
| Feature Signal | Relative Importance | Operational Description |
| :--- | :---: | :--- |
| `Inbound_Delay_Mins` | **42.16%** | Primary shock to ground buffer capacity upon touchdown. |
| `Route_Congestion` | **15.76%** | Expanding historical average delay at Origin airport hub. |
| `Tail_Delay_Freq` | **13.37%** | Specific aircraft historical mechanical/turnaround latency. |
| `Turn_Buffer` | **8.99%** | Scheduled turn slack relative to minimum turn time (45 mins). |
| `Scheduled_Turnaround_Mins` | **8.46%** | Scheduled timetable ground allocation. |
| `Departure_Hour` | **7.61%** | Airport bank congestion profile (morning vs afternoon rush). |
| `Day_of_Week` | **3.66%** | Weekly business travel volume cyclicality. |

#### Model Validation Scorecard (88,270 Out-of-Sample Holdout Flights):
| Metric | Score | Operational Significance |
| :--- | :---: | :--- |
| **ROC-AUC** | **0.8678** | Area Under the Receiver Operating Characteristic. |
| **PR-AUC** | **0.8192** | Robust performance under real-world class distribution. |
| **Precision** | **78.44%** | Minimizes false alarms; 8 out of 10 alerts represent real breaches. |
| **Recall** | **65.94%** | Captures two-thirds of all buffer breaches across the network. |
| **F1-Score** | **0.7165** | Balanced harmonic accuracy. |

#### Confusion Matrix:
$$\begin{pmatrix} \text{True Negatives (On-Time)}: 47,425 & \text{False Positives (False Alarm)}: 6,268 \\ \text{False Negatives (Missed Breach)}: 11,778 & \text{True Positives (Delay Intercepted)}: 22,799 \end{pmatrix}$$

#### Operational Decision Threshold Sweep:
| Threshold | Precision | Recall | F1-Score | Optimal Operational Use Case |
| :---: | :---: | :---: | :---: | :--- |
| **0.30** | 63.8% | 84.1% | 72.5% | Severe weather days (maximize delay capture). |
| **0.40** | 71.5% | 75.3% | 73.3% | Balanced station readiness. |
| **0.50** | **78.4%** | **65.9%** | **71.7%** | **Default OCC operational threshold (high precision).** |
| **0.60** | 84.9% | 55.4% | 67.1% | Resource-constrained ramp stations (zero false alarms). |
| **0.70** | 90.7% | 42.8% | 58.1% | High-cost ground crew surge triggers. |

---

## Financial Translation & ROI Dashboard

Using the FAA delay standard of **$75.00 / minute**:

$$\text{Gross Exposure} = \sum (\text{True Positive Delay Minutes}) \times \$75.00$$

- **True Positives Intercepted**: **22,799 flights**
- **Captured Delay Minutes**: **682,723 minutes**
- **Gross Delay Cost Exposure**: **$51,204,225.00 ($51.2M)**
- **Tactical Mitigation (20% Recovery)**: **$10,240,845.00 ($10.2M Net Annual Savings)**

### Tactical Station Intervention Playbook:
1. **Dynamic Ground Crew Surges**: When breach probability exceeds $65\%$, station managers auto-dispatch dedicated secondary baggage ramp crews and pre-position fueling trucks at the gate before block-in.
2. **Proactive Gate Reassignments**: Reroute late-arriving aircraft to gates with shorter taxi-in distances and dual jet bridges.
3. **Priority Boarding Sequencing**: Pre-tag and gate-check carry-on bags 20 minutes prior to cabin door opening, shaving 8–12 minutes off passenger boarding duration.

---

## Quickstart & Reproducibility Guide

### 1. Prerequisites & Environment Setup
Clone the repository and install dependencies:
```bash
git clone https://github.com/shreshth-nanda83/Turnaround-Optimization-Model.git
cd Turnaround-Optimization-Model
pip install -r requirements.txt
```

### 2. Ingest Data & Initialize SQLite
Parses the flight dataset, cleans timestamps, resolves overnight rollovers, and initializes `operations.db`:
```bash
python src/db_setup.py
```

### 3. Run Analytical SQL Engine
Execute the LAG windowing CTE pipeline to inspect hub choke points:
```bash
sqlite3 operations.db < sql/turnaround_analytics.sql
```

### 4. Train Model & Generate Financial Impact Report
Trains the Random Forest model, runs the threshold sweep, saves the trained model artifact to `src/turnaround_rf_model.joblib`, and outputs the financial ROI analysis:
```bash
python src/train_model.py
```

---

## Project Structure

```text
Turnaround_Optimization_Model/
├── sql/
│   └── turnaround_analytics.sql    # Analytical CTE & LAG() windowing engine
├── src/
│   ├── db_setup.py                 # Telemetry ingestion & SQLite WAL builder
│   └── train_model.py              # ML classifier, threshold sweep & ROI calculator
├── Workflow_Presentation.pptx      # 8-slide executive presentation deck
├── requirements.txt                # Production environment dependencies
├── .gitignore                      # Git exclusion rules
└── README.md                       # Architecture, metrics & execution guide
```

---

## Executive Presentation Deck
A PowerPoint presentation (`Workflow_Presentation.pptx`) is included in the root directory. It features an 8-slide executive dashboard covering:
- **Slide 1**: Executive Overview & KPI Badges ($10.2M Savings, 441K Turns, 81.9% PR-AUC).
- **Slide 2**: The Domino Effect & Buffer Exhaustion Breakdown.
- **Slide 3**: Four-Stage Decoupled Engineering Architecture.
- **Slide 4**: Aircraft Tail Sequencing & Hub Choke Points (`DTW`, `ORD`, `ATL`, `MIA`).
- **Slide 5**: Random Forest Feature Importance Drivers & Class Balancing.
- **Slide 6**: Out-of-Sample Holdout Scorecard & Confusion Matrix Heatmap.
- **Slide 7**: Executive Financial Exposure Waterfall & ROI Quantification.
- **Slide 8**: Station Control Center Dispatch Playbooks & Future Streaming Roadmap.
