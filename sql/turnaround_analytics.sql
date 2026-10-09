-- Analytical SQL Pipeline for Turnaround Optimization
-- This pipeline calculates turnaround metrics, identifies cascading delays,
-- and aggregates delay statistics to isolate network choke points.

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
        -- Use LAG() window function partitioned by aircraft tail number and ordered by scheduled departure 
        -- to calculate prior arrival time, prior scheduled arrival time, and prior destination.
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

-- 2. Calculate Ground Turnaround Times and Delays
TurnaroundMetrics AS (
    SELECT 
        *,
        -- Ground Turnaround Time: Actual time spent on ground (minutes)
        (julianday(Actual_Departure) - julianday(Prior_Actual_Arrival)) * 1440.0 AS Actual_Turnaround_Mins,
        -- Scheduled Turnaround Time
        (julianday(Scheduled_Departure) - julianday(Prior_Scheduled_Arrival)) * 1440.0 AS Scheduled_Turnaround_Mins,
        -- Inbound Delay (Delay of the aircraft arriving from the prior flight)
        (julianday(Prior_Actual_Arrival) - julianday(Prior_Scheduled_Arrival)) * 1440.0 AS Inbound_Delay_Mins
    FROM FlightSequence
    -- Ensure logical continuity: prior destination must be current origin
    WHERE Prior_Dest = Origin 
      AND Prior_Actual_Arrival IS NOT NULL
      -- Filter out overnight stays and long maintenance blocks (e.g. > 12 hours)
      AND (julianday(Scheduled_Departure) - julianday(Prior_Scheduled_Arrival)) * 1440.0 BETWEEN 30 AND 720
),

-- 3. Determine Ground Buffer Delta and Cascading Delays
CascadingDelays AS (
    SELECT
        *,
        -- Ground Buffer Delta = Scheduled Turnaround - Actual Turnaround
        Scheduled_Turnaround_Mins - Actual_Turnaround_Mins AS Ground_Buffer_Delta,
        -- Flag cascading delays: Inbound delay > 15 mins DIRECTLY propagates to a Departure delay > 15 mins
        CASE 
            WHEN Inbound_Delay_Mins > 15 AND Departure_Delay > 15 THEN 1 
            ELSE 0 
        END AS Is_Cascading_Delay
    FROM TurnaroundMetrics
)

-- 4. Aggregate delay metrics by Origin Airport and Carrier
-- Isolating network choke points
SELECT 
    Origin,
    Carrier,
    COUNT(*) AS Total_Turnarounds,
    ROUND(AVG(Scheduled_Turnaround_Mins), 2) AS Avg_Scheduled_Turnaround_Mins,
    ROUND(AVG(Actual_Turnaround_Mins), 2) AS Avg_Actual_Turnaround_Mins,
    ROUND(AVG(Inbound_Delay_Mins), 2) AS Avg_Inbound_Delay_Mins,
    SUM(Is_Cascading_Delay) AS Total_Cascading_Delays,
    ROUND(CAST(SUM(Is_Cascading_Delay) AS FLOAT) / COUNT(*) * 100.0, 2) AS Pct_Cascading_Delay
FROM CascadingDelays
GROUP BY Origin, Carrier
HAVING Total_Turnarounds > 50
ORDER BY Pct_Cascading_Delay DESC;
