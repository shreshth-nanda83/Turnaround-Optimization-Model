# Power BI Data Model Architecture & DAX Measures Dictionary
## Commercial Fleet Operations & Turnaround Optimization

This document outlines the enterprise **Star Schema Data Model** and **DAX Measures** designed for deploying the Turnaround Optimization Model into Microsoft Power BI Desktop or Microsoft Fabric.

---

## 1. Data Model Star Schema Architecture

```
                    +------------------------------------+
                    |       DimDate                      |
                    |------------------------------------|
                    | Flight_Date (PK)                   |
                    | Year, Quarter, Month, DayOfWeek    |
                    +-----------------+------------------+
                                      | 1
                                      |
                                      | *
+--------------------+        +-------+--------------------+        +--------------------+
| DimAirport         |        | FactTurnaround             |        | DimCarrier         |
|--------------------| 1    * |----------------------------| *    1 |--------------------|
| Airport_Code (PK)  +--------+ Origin (FK)                +--------+ Carrier_Code (PK)  |
| Airport_Name       |        | Tail_Number                |        | Airline_Name       |
| Hub_Category       |        | Scheduled_Turn_Mins        |        | Fleet_Type         |
+--------------------+        | Actual_Turn_Mins           |        +--------------------+
                              | Inbound_Delay_Mins         |
                              | Departure_Delay_Mins       |
                              | Remaining_Legs_Today       |
                              | Breach_Probability         |
                              | PII_Score                  |
                              +----------------------------+
```

### Table Specifications:
* **`FactTurnaround`**: Imported from [`dashboards/turnaround_bi_feed.csv`](turnaround_bi_feed.csv) (25,000+ representative operational turns with ML breach probabilities and downstream legs).
* **`DimDate`**: Auto-generated date hierarchy linked on `FactTurnaround[Flight_Date]`.
* **`DimAirport`**: Airport hub metadata linked on `FactTurnaround[Origin]`.

---

## 2. Enterprise DAX Measures

### A. Turnaround Operational Performance Measures

#### 1. Total Aircraft Turns
```dax
Total Turns = COUNTROWS('FactTurnaround')
```

#### 2. Average Scheduled Ground Turnaround Time (Minutes)
```dax
Avg Scheduled Turn (min) = AVERAGE('FactTurnaround'[Scheduled_Turn_Mins])
```

#### 3. Average Actual Ground Turnaround Time (Minutes)
```dax
Avg Actual Turn (min) = AVERAGE('FactTurnaround'[Actual_Turn_Mins])
```

#### 4. Ground Buffer Delta (Minutes)
```dax
Ground Buffer Delta (min) = 
[Avg Scheduled Turn (min)] - [Avg Actual Turn (min)]
```

#### 5. Buffer Breach Count & Breach Rate
```dax
Buffer Breach Count = 
CALCULATE(
    COUNTROWS('FactTurnaround'),
    'FactTurnaround'[Actual_Turn_Mins] > 'FactTurnaround'[Scheduled_Turn_Mins] + 15
)

Buffer Breach Rate % = 
DIVIDE([Buffer Breach Count], [Total Turns], 0)
```

#### 6. Cascading Delay Propagation Count & %
```dax
Cascading Delay Count = 
CALCULATE(
    COUNTROWS('FactTurnaround'),
    'FactTurnaround'[Inbound_Delay_Mins] > 15 && 'FactTurnaround'[Departure_Delay_Mins] > 15
)

Cascading Delay Rate % = 
DIVIDE([Cascading Delay Count], [Total Turns], 0)
```

---

### B. Machine Learning & Priority Intervention Index (PII) Measures

#### 7. Dynamic Decision Threshold Parameter (What-If Slider)
Create a What-If Parameter table `Threshold_Parameter` with values from $0.30$ to $0.80$ in steps of $0.05$ (default $0.50$).
```dax
Selected_Threshold = SELECTEDVALUE('Threshold_Parameter'[Threshold], 0.50)
```

#### 8. Predicted Breach Alert Trigger Count
```dax
Active Breach Alerts = 
CALCULATE(
    COUNTROWS('FactTurnaround'),
    'FactTurnaround'[Breach_Probability] >= [Selected_Threshold]
)
```

#### 9. Dynamic Priority Intervention Index (PII)
```dax
Dynamic PII = 
AVERAGEX(
    'FactTurnaround',
    'FactTurnaround'[Breach_Probability] * (1 + 0.50 * 'FactTurnaround'[Remaining_Legs_Today])
)
```

#### 10. Critical Rotations Flagged (High Downstream Centrality)
```dax
Critical Rotations Flagged = 
CALCULATE(
    COUNTROWS('FactTurnaround'),
    'FactTurnaround'[Breach_Probability] >= [Selected_Threshold] &&
    'FactTurnaround'[Remaining_Legs_Today] >= 3
)
```

---

### C. Financial Translation & Cost Avoidance Measures

#### 11. FAA Cost Benchmark Parameter (What-If Slider)
Create a What-If Parameter table `Cost_Benchmark_Parameter` with values from $\$50.00$ to $\$100.00$ (default $\$75.00$).
```dax
Selected_Cost_Per_Min = SELECTEDVALUE('Cost_Benchmark_Parameter'[Cost_Per_Min], 75.0)
```

#### 12. Tactical Mitigation Recovery % (What-If Slider)
Create a What-If Parameter table `Mitigation_Rate_Parameter` with values from $0.10$ to $0.35$ (default $0.20$).
```dax
Selected_Recovery_Rate = SELECTEDVALUE('Mitigation_Rate_Parameter'[Recovery_Rate], 0.20)
```

#### 13. Gross Delay Cost Exposure ($)
```dax
Gross Delay Cost Exposure = 
SUMX(
    FILTER('FactTurnaround', 'FactTurnaround'[Breach_Probability] >= [Selected_Threshold]),
    MAX('FactTurnaround'[Departure_Delay_Mins], 0) * [Selected_Cost_Per_Min]
)
```

#### 14. Net Annual Cost Mitigation ($ Savings)
```dax
Net Annual Delay Savings = 
[Gross Delay Cost Exposure] * [Selected_Recovery_Rate]
```

---

## 3. Step-by-Step Power BI Desktop Import Guide

1. Open **Power BI Desktop**.
2. Click **Get Data** $\rightarrow$ **Text/CSV** $\rightarrow$ Select `dashboards/turnaround_bi_feed.csv`.
3. In Power Query, verify:
   * `Flight_Date` is set to **Date**.
   * `Departure_Hour`, `Remaining_Legs_Today` are set to **Whole Number**.
   * `Breach_Probability`, `PII_Score` are set to **Decimal Number**.
4. Click **Close & Apply**.
5. Create a new measure group table (`_Measures`) and paste the DAX formulas above.
6. Assemble the 3 tabs:
   * **Tab 1: OCC Network Health & Hub Choke Points**
   * **Tab 2: Prescriptive Dispatch Board (PII Queue)**
   * **Tab 3: Financial ROI & What-If Simulator**
