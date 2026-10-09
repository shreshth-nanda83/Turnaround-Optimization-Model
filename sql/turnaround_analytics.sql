-- ==============================================================================
-- ANALYTICAL SQL PIPELINE: COMMERCIAL FLEET TURNAROUND OPTIMIZATION
-- ==============================================================================
-- Business Objective:
--   1. Sequence physical aircraft rotations across the entire route network.
--   2. Calculate exact ground turn durations, scheduled buffer slacks, and inbound latency.
--   3. Detect and isolate cascading delay propagation choke points by airport and carrier.
-- ==============================================================================

-- 1. Create a Common Table Expression (CTE) to sequence flights by aircraft
WITH FlightSequence AS (
    SELECT 
        Carrier,
        Tail_Number,
        Flight_Number,
        Origin,
        Dest,
        Scheduled_Departure,
        Actual_Departure,
        Departure_Delay,
        Scheduled_Arrival,
        Actual_Arrival,
        Arrival_Delay,
        -- Use LAG() window function partitioned by physical aircraft tail number
        -- and ordered by scheduled departure to calculate prior arrival metrics.
        LAG(Actual_Arrival) OVER (
            PARTITION BY Tail_Number 
            ORDER BY Scheduled_Departure
        ) AS Prior_Actual_Arrival,
        LAG(Scheduled_Arrival) OVER (
            PARTITION BY Tail_Number 
            ORDER BY Scheduled_Departure
        ) AS Prior_Scheduled_Arrival,
        LAG(Dest) OVER (
            PARTITION BY Tail_Number 
            ORDER BY Scheduled_Departure
        ) AS Prior_Dest
    FROM flight_operations
),

-- 2. Calculate Ground Turnaround Times and Inbound Delays
TurnaroundMetrics AS (
    SELECT 
        *,
        -- Actual Ground Turnaround Time (in minutes)
        (julianday(Actual_Departure) - julianday(Prior_Actual_Arrival)) * 1440.0 AS Actual_Turnaround_Mins,
        -- Scheduled Turnaround Time allocated in airline timetable
        (julianday(Scheduled_Departure) - julianday(Prior_Scheduled_Arrival)) * 1440.0 AS Scheduled_Turnaround_Mins,
        -- Inbound Delay of the incoming flight
        (julianday(Prior_Actual_Arrival) - julianday(Prior_Scheduled_Arrival)) * 1440.0 AS Inbound_Delay_Mins
    FROM FlightSequence
    -- Enforce physical aircraft rotation continuity: prior arrival airport must match current departure
    WHERE Prior_Dest = Origin 
      AND Prior_Actual_Arrival IS NOT NULL
      -- Filter out overnight hangaring and multi-day maintenance blocks (30 mins <= turn <= 12 hours)
      AND (julianday(Scheduled_Departure) - julianday(Prior_Scheduled_Arrival)) * 1440.0 BETWEEN 30 AND 720
),

-- 3. Determine Ground Buffer Delta and Cascading Delay Flags
CascadingDelays AS (
    SELECT
        *,
        -- Buffer Delta: Positive = scheduled buffer surplus; Negative = buffer deficit
        Scheduled_Turnaround_Mins - Actual_Turnaround_Mins AS Ground_Buffer_Delta,
        -- Cascading Delay Indicator:
        -- Inbound delay > 15 mins directly triggers Departure delay > 15 mins
        CASE 
            WHEN Inbound_Delay_Mins > 15 AND Departure_Delay > 15 THEN 1 
            ELSE 0 
        END AS Is_Cascading_Delay
    FROM TurnaroundMetrics
)

-- 4. Aggregate Network Choke Points by Origin Airport and Carrier
SELECT 
    Origin AS Airport_Code,
    Carrier AS Airline_Code,
    COUNT(*) AS Total_Turnarounds,
    ROUND(AVG(Scheduled_Turnaround_Mins), 1) AS Avg_Scheduled_Turn_Mins,
    ROUND(AVG(Actual_Turnaround_Mins), 1) AS Avg_Actual_Turn_Mins,
    ROUND(AVG(Inbound_Delay_Mins), 1) AS Avg_Inbound_Delay_Mins,
    SUM(Is_Cascading_Delay) AS Total_Cascading_Delays,
    ROUND(CAST(SUM(Is_Cascading_Delay) AS FLOAT) / COUNT(*) * 100.0, 2) AS Pct_Cascading_Delay
FROM CascadingDelays
GROUP BY Origin, Carrier
HAVING Total_Turnarounds > 50
ORDER BY Pct_Cascading_Delay DESC;
