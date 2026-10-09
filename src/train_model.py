import sqlite3
import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import average_precision_score, f1_score, precision_score, recall_score, confusion_matrix
import warnings
warnings.filterwarnings('ignore')

def load_and_engineer_features(db_path='operations.db'):
    print(f"Loading data from {db_path}...")
    conn = sqlite3.connect(db_path)
    
    # SQL query to extract turnaround features directly
    query = """
    WITH FlightSequence AS (
        SELECT 
            Tail_Number, Carrier, Origin, Dest,
            Scheduled_Departure, Actual_Departure, Departure_Delay,
            Scheduled_Arrival, Actual_Arrival, Arrival_Delay,
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
    )
    SELECT * FROM TurnaroundMetrics;
    """
    
    df = pd.read_sql_query(query, conn)
    conn.close()
    
    print(f"Raw turnaround data shape: {df.shape}")
    
    # Target Variable: Ground turnaround buffer breached by >15 mins OR arrival delay >15 min
    # We define turnaround buffer breach as actual turnaround exceeding scheduled by > 15 mins.
    # Alternatively, Departure_Delay > 15 mins is typically the result.
    df['Buffer_Breach'] = (df['Actual_Turnaround_Mins'] > df['Scheduled_Turnaround_Mins'] + 15).astype(int)
    df['Arrival_Delay_15'] = (df['Arrival_Delay'] > 15).astype(int)
    df['Target'] = ((df['Buffer_Breach'] == 1) | (df['Arrival_Delay_15'] == 1)).astype(int)
    
    # Drop rows with null target
    df.dropna(subset=['Target', 'Scheduled_Turnaround_Mins', 'Inbound_Delay_Mins'], inplace=True)

    print("Engineering additional features...")
    df['Scheduled_Departure'] = pd.to_datetime(df['Scheduled_Departure'])
    df['Departure_Hour'] = df['Scheduled_Departure'].dt.hour
    df['Day_of_Week'] = df['Scheduled_Departure'].dt.dayofweek
    
    # Minimum turnaround is typically ~45 mins for narrow-body, let's proxy Turn Buffer
    df['Turn_Buffer'] = df['Scheduled_Turnaround_Mins'] - 45
    
    # Route Congestion: Historical average delay by Origin
    origin_congestion = df.groupby('Origin')['Departure_Delay'].transform(lambda x: x.shift().expanding().mean())
    df['Route_Congestion'] = origin_congestion.fillna(df['Departure_Delay'].mean())
    
    # Historical tail-number delay frequency (delay > 15)
    df['Is_Delayed'] = (df['Departure_Delay'] > 15).astype(int)
    tail_delay_freq = df.groupby('Tail_Number')['Is_Delayed'].transform(lambda x: x.shift().expanding().mean())
    df['Tail_Delay_Freq'] = tail_delay_freq.fillna(df['Is_Delayed'].mean())
    
    return df

def train_and_evaluate(df):
    features = [
        'Scheduled_Turnaround_Mins', 'Turn_Buffer', 'Inbound_Delay_Mins', 
        'Departure_Hour', 'Day_of_Week', 'Route_Congestion', 'Tail_Delay_Freq'
    ]
    
    X = df[features]
    y = df['Target']
    
    print(f"Dataset target distribution:\n{y.value_counts(normalize=True) * 100}")
    
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42, stratify=y)
    
    print("\nTraining Random Forest Classifier (with class_weight='balanced')...")
    clf = RandomForestClassifier(n_estimators=100, class_weight='balanced', random_state=42, n_jobs=-1)
    clf.fit(X_train, y_train)
    
    y_pred = clf.predict(X_test)
    y_prob = clf.predict_proba(X_test)[:, 1]
    
    # Model Evaluation Metrics
    from sklearn.metrics import roc_auc_score
    roc_auc = roc_auc_score(y_test, y_prob)
    pr_auc = average_precision_score(y_test, y_prob)
    f1 = f1_score(y_test, y_pred)
    precision = precision_score(y_test, y_pred)
    recall = recall_score(y_test, y_pred)
    cm = confusion_matrix(y_test, y_pred)
    
    print("\n" + "="*45)
    print("      MODEL EVALUATION METRICS")
    print("="*45)
    print(f"  ROC-AUC Score:      {roc_auc:.4f}")
    print(f"  PR-AUC Score:       {pr_auc:.4f}")
    print(f"  Precision Score:    {precision:.4f}")
    print(f"  Recall Score:       {recall:.4f}")
    print(f"  F1-Score:           {f1:.4f}")
    print("\nConfusion Matrix (TN, FP / FN, TP):")
    print(f"  [[{cm[0,0]:>6}, {cm[0,1]:>6}]")
    print(f"   [{cm[1,0]:>6}, {cm[1,1]:>6}]]")
    
    # Feature Importance Breakdown
    print("\n" + "-"*45)
    print("  FEATURE IMPORTANCE CONTRIBUTIONS")
    print("-"*45)
    importances = clf.feature_importances_
    sorted_idx = np.argsort(importances)[::-1]
    for idx in sorted_idx:
        print(f"  {features[idx]:<28} {importances[idx]*100:>6.2f}%")
        
    # Operational Threshold Sweep
    print("\n" + "-"*45)
    print("  OPERATIONAL DISPATCH THRESHOLD ANALYSIS")
    print("-"*45)
    print("  Threshold | Precision | Recall  | F1-Score")
    print("  " + "-"*41)
    for thresh in [0.30, 0.40, 0.50, 0.60, 0.70]:
        t_pred = (y_prob >= thresh).astype(int)
        t_prec = precision_score(y_test, t_pred, zero_division=0)
        t_rec = recall_score(y_test, t_pred, zero_division=0)
        t_f1 = f1_score(y_test, t_pred, zero_division=0)
        print(f"     {thresh:.2f}   |   {t_prec*100:>5.1f}%  |  {t_rec*100:>5.1f}% |  {t_f1*100:>5.1f}%")
    print("="*45)
    
    # Save Model Artifact for Deployment (Compressed)
    try:
        import joblib
        model_out = 'src/turnaround_rf_model.joblib'
        joblib.dump({'model': clf, 'features': features}, model_out, compress=3)
        print(f"\nModel artifact successfully serialized to {model_out} (git-ignored)")
    except Exception as e:
        print(f"Could not persist model artifact: {e}")
        
    return clf, X_test, y_test, y_pred, df.loc[X_test.index]

def calculate_financial_impact(test_df, y_pred):
    print("\n" + "="*45)
    print("     FINANCIAL IMPACT TRANSLATION")
    print("="*45)
    
    test_df['Predicted_Target'] = y_pred
    cost_per_minute = 75.0 # FAA / Airlines for America standard benchmark
    
    true_positives = test_df[(test_df['Target'] == 1) & (test_df['Predicted_Target'] == 1)]
    tp_delay_mins = true_positives['Arrival_Delay'].clip(lower=0).sum()
    total_cost = tp_delay_mins * cost_per_minute
    
    print(f"  True Positives Intercepted:      {len(true_positives):,d} flights")
    print(f"  Delay Minutes Identified:        {tp_delay_mins:,.0f} mins")
    print(f"  Gross Unmitigated Delay Exposure: ${total_cost:,.2f}")
    
    # 20% Tactical Mitigation ROI (Pre-arrival crew staging, gate swaps)
    mitigation_potential = total_cost * 0.20
    print(f"  Net Annualized Savings (20% ROI): ${mitigation_potential:,.2f}")
    print("="*45 + "\n")

if __name__ == "__main__":
    df = load_and_engineer_features()
    model, X_test, y_test, y_pred, test_df = train_and_evaluate(df)
    calculate_financial_impact(test_df, y_pred)
