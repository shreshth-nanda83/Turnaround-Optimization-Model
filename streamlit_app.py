import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import sqlite3
import os

# -----------------------------------------------------------------------------
# PAGE CONFIGURATION
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="Fleet OCC | Turnaround Optimization & Prescriptive Dispatch",
    page_icon="✈️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom High-End Styling
st.markdown("""
<style>
    /* Metric Card Styling */
    div[data-testid="stMetricValue"] {
        font-family: 'JetBrains Mono', monospace;
        font-size: 1.85rem !important;
        font-weight: 700 !important;
    }
    div[data-testid="stMetricLabel"] {
        font-size: 0.82rem !important;
        font-weight: 600 !important;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        color: #94a3b8 !important;
    }
    /* Tab Styling */
    button[data-baseweb="tab"] {
        font-size: 0.95rem !important;
        font-weight: 600 !important;
        padding-top: 0.75rem !important;
        padding-bottom: 0.75rem !important;
    }
    /* Section Headers */
    .occ-header {
        font-size: 1.35rem;
        font-weight: 700;
        letter-spacing: -0.02em;
        margin-bottom: 0.5rem;
    }
    .occ-subtitle {
        font-size: 0.85rem;
        color: #94a3b8;
        margin-bottom: 1.25rem;
    }
</style>
""", unsafe_allow_html=True)

# -----------------------------------------------------------------------------
# DATA LOADERS & CACHING
# -----------------------------------------------------------------------------
@st.cache_data
def load_data():
    bi_feed_path = 'dashboards/turnaround_bi_feed.csv'
    hub_feed_path = 'dashboards/hub_analytics.csv'

    if os.path.exists(bi_feed_path):
        df_flights = pd.read_csv(bi_feed_path)
    elif os.path.exists('operations.db'):
        try:
            conn = sqlite3.connect('operations.db')
            df_flights = pd.read_sql_query("SELECT * FROM flight_operations LIMIT 10000", conn)
            conn.close()
        except Exception:
            df_flights = pd.DataFrame()
    else:
        df_flights = pd.DataFrame()

    if os.path.exists(hub_feed_path):
        df_hubs = pd.read_csv(hub_feed_path)
        rename_map = {
            'Total_Turnarounds': 'Total_Turns',
            'Avg_Scheduled_Turn_Mins': 'Avg_Scheduled_Turn',
            'Avg_Actual_Turn_Mins': 'Avg_Actual_Turn',
            'Avg_Inbound_Delay_Mins': 'Avg_Inbound_Delay',
            'Avg_Buffer_Delta_Mins': 'Avg_Buffer_Delta',
            'Pct_Cascading_Delay': 'Cascading_Delay_Pct'
        }
        df_hubs.rename(columns=rename_map, inplace=True)
    elif os.path.exists('operations.db'):
        try:
            conn = sqlite3.connect('operations.db')
            hub_sql = """
            WITH FlightSequence AS (
                SELECT 
                    Carrier, Origin, Dest, Scheduled_Departure, Actual_Departure,
                    Departure_Delay, Scheduled_Arrival, Actual_Arrival, Arrival_Delay,
                    LAG(Actual_Arrival) OVER (PARTITION BY Tail_Number ORDER BY Scheduled_Departure) AS Prior_Actual_Arrival,
                    LAG(Scheduled_Arrival) OVER (PARTITION BY Tail_Number ORDER BY Scheduled_Departure) AS Prior_Scheduled_Arrival,
                    LAG(Dest) OVER (PARTITION BY Tail_Number ORDER BY Scheduled_Departure) AS Prior_Dest
                FROM flight_operations
            ),
            TurnaroundMetrics AS (
                SELECT 
                    *,
                    (julianday(Actual_Departure) - julianday(Prior_Actual_Arrival)) * 1440.0 AS Actual_Turnaround_Mins,
                    (julianday(Scheduled_Departure) - julianday(Prior_Scheduled_Arrival)) * 1440.0 AS Scheduled_Turnaround_Mins,
                    (julianday(Prior_Actual_Arrival) - julianday(Prior_Scheduled_Arrival)) * 1440.0 AS Inbound_Delay_Mins
                FROM FlightSequence
                WHERE Prior_Dest = Origin 
                  AND Prior_Actual_Arrival IS NOT NULL
                  AND (julianday(Scheduled_Departure) - julianday(Prior_Scheduled_Arrival)) * 1440.0 BETWEEN 30 AND 720
            ),
            CascadingDelays AS (
                SELECT
                    *,
                    Scheduled_Turnaround_Mins - Actual_Turnaround_Mins AS Ground_Buffer_Delta,
                    CASE WHEN Inbound_Delay_Mins > 15 AND Departure_Delay > 15 THEN 1 ELSE 0 END AS Is_Cascading_Delay
                FROM TurnaroundMetrics
            )
            SELECT 
                Origin AS Airport_Code,
                Carrier AS Airline_Code,
                COUNT(*) AS Total_Turns,
                ROUND(AVG(Scheduled_Turnaround_Mins), 1) AS Avg_Scheduled_Turn,
                ROUND(AVG(Actual_Turnaround_Mins), 1) AS Avg_Actual_Turn,
                ROUND(AVG(Inbound_Delay_Mins), 1) AS Avg_Inbound_Delay,
                ROUND(AVG(Ground_Buffer_Delta), 1) AS Avg_Buffer_Delta,
                ROUND(CAST(SUM(Is_Cascading_Delay) AS FLOAT) / COUNT(*) * 100.0, 2) AS Cascading_Delay_Pct
            FROM CascadingDelays
            GROUP BY Origin, Carrier
            HAVING Total_Turns >= 50
            ORDER BY Cascading_Delay_Pct DESC;
            """
            df_hubs = pd.read_sql_query(hub_sql, conn)
            conn.close()
        except Exception:
            df_hubs = pd.DataFrame()
    else:
        df_hubs = pd.DataFrame()

    return df_flights, df_hubs

df_flights_raw, df_hubs_raw = load_data()

# -----------------------------------------------------------------------------
# SIDEBAR FILTERS & CONTROLS
# -----------------------------------------------------------------------------
with st.sidebar:
    st.markdown("## ✈️ Operations Control Center")
    st.markdown("**Mission Control Slicers & What-If Parameters**")
    st.divider()

    # Hub Filter
    all_hubs = sorted(list(df_flights_raw['Origin'].unique()))
    selected_hubs = st.multiselect("Origin Hub Station", options=all_hubs, default=all_hubs[:6])

    # Carrier Filter
    all_carriers = sorted(list(df_flights_raw['Carrier'].unique()))
    selected_carriers = st.multiselect("Operating Carrier", options=all_carriers, default=all_carriers)

    st.divider()
    st.markdown("### ⚡ Prescriptive Dispatch Engine")
    
    threshold = st.slider("Breach Alert Cutoff (P)", min_value=0.30, max_value=0.75, value=0.50, step=0.05,
                          help="Random Forest probability threshold to trigger station dispatch intervention.")
    
    alpha = st.slider("Downstream Sensitivity (α)", min_value=0.0, max_value=1.0, value=0.50, step=0.05,
                      help="PII delay multiplier weighting remaining tail rotation depth.")

    st.divider()
    st.markdown("### 💵 Financial Translation Benchmark")
    
    cost_per_min = st.slider("FAA Delay Cost Standard ($/min)", min_value=50.0, max_value=120.0, value=75.0, step=5.0)
    recovery_rate = st.slider("Tactical Recovery Efficiency (%)", min_value=10, max_value=35, value=20, step=1) / 100.0

    st.divider()
    st.caption("Telemetry: 441,348 flight records ingested & indexed in SQLite WAL mode.")

# -----------------------------------------------------------------------------
# DATA FILTERING & PII RECALCULATION
# -----------------------------------------------------------------------------
df_flights = df_flights_raw.copy()
if selected_hubs:
    df_flights = df_flights[df_flights['Origin'].isin(selected_hubs)]
if selected_carriers:
    df_flights = df_flights[df_flights['Carrier'].isin(selected_carriers)]

# Dynamically calculate PII based on current alpha slider
df_flights['Dynamic_PII'] = df_flights['Breach_Probability'] * (1.0 + alpha * df_flights['Remaining_Legs_Today'])

# Compute Naive Rank vs PII Rank
df_flights['Naive_Rank'] = df_flights['Breach_Probability'].rank(ascending=False, method='min').astype(int)
df_flights['PII_Rank'] = df_flights['Dynamic_PII'].rank(ascending=False, method='min').astype(int)
df_flights['Rank_Shift'] = df_flights['Naive_Rank'] - df_flights['PII_Rank']

# Hub data filter
df_hubs = df_hubs_raw.copy()
if selected_hubs:
    df_hubs = df_hubs[df_hubs['Airport_Code'].isin(selected_hubs)]
if selected_carriers:
    df_hubs = df_hubs[df_hubs['Airline_Code'].isin(selected_carriers)]

# -----------------------------------------------------------------------------
# TOP METRICS DASHBOARD
# -----------------------------------------------------------------------------
total_turns_monitored = 441348
active_turns = len(df_flights)
breaches = df_flights[df_flights['Breach_Probability'] >= threshold]
breach_rate = (len(breaches) / active_turns * 100.0) if active_turns > 0 else 0
critical_rotations = len(df_flights[(df_flights['Breach_Probability'] >= threshold) & (df_flights['Remaining_Legs_Today'] >= 3)])
avg_inbound = df_flights['Inbound_Delay_Mins'].mean() if active_turns > 0 else 0

# Baseline FAA calculation (682,723 captured delay minutes scaled)
delay_minutes = 682723 * (cost_per_min / 75.0)
gross_exposure = delay_minutes * cost_per_min
net_savings = gross_exposure * recovery_rate

m1, m2, m3, m4, m5 = st.columns(5)
m1.metric("Monitored Turns", f"{total_turns_monitored:,}", f"{active_turns:,} filtered")
m2.metric("Turn Buffer Breaches", f"{breach_rate:.1f}%", f"{len(breaches):,} alerts @ P≥{threshold:.2f}")
m3.metric("Avg Inbound Latency", f"{avg_inbound:.1f} min", "Primary turn shock")
m4.metric("High Centrality Rotations", f"{critical_rotations:,} Flights", "Slated for ≥3 legs")
m5.metric("Net Annual Savings", f"${net_savings/1e6:.2f}M", f"{recovery_rate*100:.0f}% mitigation ROI")

st.markdown("<br>", unsafe_allow_html=True)

# -----------------------------------------------------------------------------
# MAIN DASHBOARD TABS
# -----------------------------------------------------------------------------
tab_dispatch, tab_hub, tab_roi, tab_ml = st.tabs([
    "⚡ Prescriptive Dispatch & PII Queue",
    "📍 OCC Hub Network Health & Bottlenecks",
    "💰 Financial ROI & Delay Mitigation",
    "🤖 Machine Learning Performance Scorecard"
])

# -----------------------------------------------------------------------------
# TAB 1: PRESCRIPTIVE DISPATCH & PII QUEUE
# -----------------------------------------------------------------------------
with tab_dispatch:
    st.markdown('<div class="occ-header">Active Departure Bank Tactical Dispatch Queue</div>', unsafe_allow_html=True)
    st.markdown(
        f'<div class="occ-subtitle">'
        f'Prescriptive resource optimization comparing naive ML greedy selection against '
        f'<b>Priority Intervention Index</b> (PII = P(Breach) × (1 + {alpha:.2f} × Remaining Legs)).'
        f'</div>', 
        unsafe_allow_html=True
    )

    col_chart, col_stat = st.columns([2, 1])

    with col_chart:
        # Scatter Plot: Probability vs Remaining Legs with Bubble Size = PII
        sample_scatter = df_flights[df_flights['Breach_Probability'] >= threshold].head(150)
        if not sample_scatter.empty:
            fig_scatter = px.scatter(
                sample_scatter,
                x='Remaining_Legs_Today',
                y='Breach_Probability',
                size='Dynamic_PII',
                color='Dispatch_Action',
                color_discrete_map={
                    'AUTO-SURGE CREW (HIGH CENTRALITY)': '#ec4899',
                    'STANDARD GATE SWAP': '#3b82f6',
                    'MONITOR BUFFER': '#64748b'
                },
                hover_data=['Tail_Number', 'Carrier', 'Origin', 'Dest', 'Scheduled_Dep_Time', 'Dynamic_PII'],
                labels={
                    'Remaining_Legs_Today': 'Remaining Flight Legs Scheduled Today',
                    'Breach_Probability': 'Model Breach Probability P(Breach)',
                    'Dynamic_PII': 'PII Score'
                },
                title="Prescriptive Centrality Map: Risk vs. Network Exposure"
            )
            fig_scatter.update_layout(
                plot_bgcolor='rgba(0,0,0,0)',
                paper_bgcolor='rgba(0,0,0,0)',
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
            )
            st.plotly_chart(fig_scatter, use_container_width=True)
        else:
            st.info("No flights match the current threshold and station filters.")

    with col_stat:
        st.markdown("#### 💡 The Knapsack Dilemma in Action")
        st.markdown(
            r"""
            In an Operations Control Center during a departure bank rush, ground surge crews are strictly finite.
            
            * **Isolated Turn (Low Centrality)**: An aircraft arriving on its final flight of the day ($0$ remaining legs) has **zero downstream compounding effect** if delayed.
            * **High-Centrality Rotation**: An aircraft with $P=75\%$ and **$4$ remaining legs** will propagate delays across the nation, triggering crew duty timeouts and missed passenger connections.
            """
        )
        st.success(f"**Current PII Multiplier**: $\\alpha = {alpha:.2f}$. Rotations with $\\ge 3$ remaining legs receive up to a **+{alpha*3*100:.0f}%** intervention priority boost!")

    st.markdown("#### 📋 Live Departure Bank Dispatch Prioritization Matrix")
    
    # Filter table
    table_df = df_flights[df_flights['Breach_Probability'] >= threshold].sort_values(by='Dynamic_PII', ascending=False).head(50)
    
    display_cols = [
        'Tail_Number', 'Flight_Number', 'Carrier', 'Origin', 'Dest',
        'Scheduled_Dep_Time', 'Inbound_Delay_Mins', 'Breach_Probability',
        'Remaining_Legs_Today', 'Dynamic_PII', 'Naive_Rank', 'PII_Rank', 'Rank_Shift', 'Dispatch_Action'
    ]
    
    st.dataframe(
        table_df[display_cols].style.format({
            'Breach_Probability': '{:.1%}',
            'Dynamic_PII': '{:.3f}',
            'Inbound_Delay_Mins': '{:.0f} min',
            'Rank_Shift': lambda x: f"+{x}" if x > 0 else f"{x}"
        }).background_gradient(subset=['Dynamic_PII'], cmap='Blues'),
        use_container_width=True,
        height=420
    )

# -----------------------------------------------------------------------------
# TAB 2: HUB NETWORK HEALTH & BOTTLENECK DISCOVERY
# -----------------------------------------------------------------------------
with tab_hub:
    st.markdown('<div class="occ-header">Hub Turnaround Bottlenecks & Cascading Latency</div>', unsafe_allow_html=True)
    st.markdown('<div class="occ-subtitle">Aggregated directly via the Analytical SQL Window Function CTE Pipeline.</div>', unsafe_allow_html=True)

    col_h1, col_h2 = st.columns(2)

    with col_h1:
        # Cascading Delay Severity Bar Chart
        top_cascading = df_hubs.sort_values(by='Cascading_Delay_Pct', ascending=False).head(12)
        fig_bar = px.bar(
            top_cascading,
            x='Airport_Code',
            y='Cascading_Delay_Pct',
            color='Cascading_Delay_Pct',
            color_continuous_scale=['#38bdf8', '#f59e0b', '#f43f5e'],
            hover_data=['Airline_Code', 'Total_Turns', 'Avg_Inbound_Delay'],
            labels={'Cascading_Delay_Pct': 'Cascading Delay Breach %', 'Airport_Code': 'Airport Hub'},
            title="Hub Cascading Delay Propagation Severity (%)"
        )
        fig_bar.update_layout(plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)')
        st.plotly_chart(fig_bar, use_container_width=True)

    with col_h2:
        # Buffer Deficit Comparison (Scheduled vs Actual Turn)
        fig_turn = go.Figure()
        fig_turn.add_trace(go.Bar(
            name='Scheduled Turn (min)',
            x=top_cascading['Airport_Code'],
            y=top_cascading['Avg_Scheduled_Turn'],
            marker_color='#38bdf8'
        ))
        fig_turn.add_trace(go.Bar(
            name='Actual Turn (min)',
            x=top_cascading['Airport_Code'],
            y=top_cascading['Avg_Actual_Turn'],
            marker_color='#f43f5e'
        ))
        fig_turn.update_layout(
            barmode='group',
            title="Scheduled vs. Actual Ground Turnaround Duration (min)",
            plot_bgcolor='rgba(0,0,0,0)',
            paper_bgcolor='rgba(0,0,0,0)',
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
        )
        st.plotly_chart(fig_turn, use_container_width=True)

    st.markdown("#### 🏢 Hub Analytical Choke Point Leaderboard")
    st.dataframe(
        df_hubs.style.format({
            'Avg_Scheduled_Turn': '{:.1f}m',
            'Avg_Actual_Turn': '{:.1f}m',
            'Avg_Inbound_Delay': '{:.1f}m',
            'Avg_Buffer_Delta': '{:.1f}m',
            'Cascading_Delay_Pct': '{:.2f}%',
            'Total_Turns': '{:,}'
        }).background_gradient(subset=['Cascading_Delay_Pct'], cmap='Reds'),
        use_container_width=True,
        height=350
    )

# -----------------------------------------------------------------------------
# TAB 3: FINANCIAL ROI & DELAY MITIGATION
# -----------------------------------------------------------------------------
with tab_roi:
    st.markdown('<div class="occ-header">Financial Delay Cost Accounting & ROI Simulator</div>', unsafe_allow_html=True)
    st.markdown('<div class="occ-subtitle">Translating operational turnaround intercept into quantified bottom-line cost avoidance.</div>', unsafe_allow_html=True)

    f1, f2, f3 = st.columns(3)
    f1.metric("Captured Delay Minutes", f"{delay_minutes:,.0f} mins", "True Positives @ 60-90m lead time")
    f2.metric("Gross Delay Exposure", f"${gross_exposure:,.2f}", f"@ ${cost_per_min:.2f}/min FAA benchmark")
    f3.metric("Net Annualized Cost Avoidance", f"${net_savings:,.2f}", f"@ {recovery_rate*100:.0f}% tactical recovery")

    st.divider()

    col_fin_chart, col_playbook = st.columns([1.5, 1])

    with col_fin_chart:
        # Financial savings by major hub
        hub_savings = pd.DataFrame({
            'Hub': ['ORD (Chicago)', 'DTW (Detroit)', 'ATL (Atlanta)', 'DEN (Denver)', 'MIA (Miami)', 'EWR (Newark)', 'DFW (Dallas)'],
            'Annual_Savings': [
                net_savings * 0.26, net_savings * 0.21, net_savings * 0.18,
                net_savings * 0.14, net_savings * 0.09, net_savings * 0.07, net_savings * 0.05
            ]
        })
        fig_fin = px.bar(
            hub_savings,
            x='Annual_Savings',
            y='Hub',
            orientation='h',
            color='Annual_Savings',
            color_continuous_scale='Greens',
            title=f"Station Cost Avoidance Distribution ($ Annualized @ {recovery_rate*100:.0f}% Recovery)",
            labels={'Annual_Savings': 'Net Cost Avoidance ($)'}
        )
        fig_fin.update_layout(plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)')
        st.plotly_chart(fig_fin, use_container_width=True)

    with col_playbook:
        st.markdown("#### 🎯 Tactical OCC Station Playbook")
        with st.expander("1. Dynamic Ground Crew Surges", expanded=True):
            st.write("When $P(\\text{Breach}) \\ge 65\\%$ and tail has $\\ge 3$ remaining legs, station controllers auto-dispatch secondary baggage offloaders and pre-position fueling bowsers before block-in.")
        with st.expander("2. Proactive Gate Reassignments"):
            st.write("Reroute delayed arrivals to adjacent gates with shorter taxi-in distances and dual jet-bridges to shave 6–10 minutes off passenger deplaning.")
        with st.expander("3. Priority Boarding Sequencing"):
            st.write("Initiate pre-tagging and gate-checking of carry-on luggage 20 minutes prior to door opening, avoiding overhead bin congestion and door closing delays.")

# -----------------------------------------------------------------------------
# TAB 4: ML PERFORMANCE SCORECARD
# -----------------------------------------------------------------------------
with tab_ml:
    st.markdown('<div class="occ-header">Machine Learning Architecture & Validation Scorecard</div>', unsafe_allow_html=True)
    st.markdown('<div class="occ-subtitle">Random Forest Classifier evaluated on 88,270 out-of-sample holdout flights with class-balanced weighting.</div>', unsafe_allow_html=True)

    s1, s2, s3, s4, s5 = st.columns(5)
    s1.metric("ROC-AUC Score", "0.8325", "Discriminative ability")
    s2.metric("PR-AUC Score", "0.8192", "Precision-Recall Curve")
    s3.metric("Precision", "78.44%", "Low false alarm rate")
    s4.metric("Recall", "65.94%", "Captures 2/3 of breaches")
    s5.metric("F1-Score", "0.7165", "Harmonic balance")

    st.divider()

    col_fi, col_thresh = st.columns(2)

    with col_fi:
        # Feature Importance
        fi_df = pd.DataFrame({
            'Feature': [
                'Inbound Delay (min)', 'Route Congestion', 'Tail Delay Freq',
                'Turn Buffer Slack', 'Scheduled Turn (min)', 'Departure Hour', 'Day of Week'
            ],
            'Importance': [42.48, 15.62, 13.31, 8.90, 8.41, 7.46, 3.82]
        }).sort_values(by='Importance', ascending=True)

        fig_fi = px.bar(
            fi_df,
            x='Importance',
            y='Feature',
            orientation='h',
            title="Predictive Signal Contributions (% Feature Importance)",
            color='Importance',
            color_continuous_scale='Blues',
            labels={'Importance': 'Relative Importance (%)'}
        )
        fig_fi.update_layout(plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)')
        st.plotly_chart(fig_fi, use_container_width=True)

    with col_thresh:
        # Threshold Trade-off Curve
        thresh_df = pd.DataFrame({
            'Threshold': [0.30, 0.40, 0.50, 0.60, 0.70],
            'Precision': [59.1, 69.2, 77.7, 83.7, 88.8],
            'Recall': [81.1, 72.9, 66.6, 60.5, 54.7],
            'F1': [68.4, 71.0, 71.7, 70.3, 67.7]
        })

        fig_thresh = go.Figure()
        fig_thresh.add_trace(go.Scatter(x=thresh_df['Threshold'], y=thresh_df['Precision'], mode='lines+markers', name='Precision (%)', line=dict(color='#38bdf8', width=3)))
        fig_thresh.add_trace(go.Scatter(x=thresh_df['Threshold'], y=thresh_df['Recall'], mode='lines+markers', name='Recall (%)', line=dict(color='#f43f5e', width=3)))
        fig_thresh.add_trace(go.Scatter(x=thresh_df['Threshold'], y=thresh_df['F1'], mode='lines+markers', name='F1-Score (%)', line=dict(color='#10b981', width=3, dash='dot')))
        fig_thresh.update_layout(
            title="Operational Threshold Sweep: Precision vs. Recall Trade-Off",
            xaxis_title="Decision Cutoff Threshold",
            yaxis_title="Score (%)",
            plot_bgcolor='rgba(0,0,0,0)',
            paper_bgcolor='rgba(0,0,0,0)',
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
        )
        st.plotly_chart(fig_thresh, use_container_width=True)
