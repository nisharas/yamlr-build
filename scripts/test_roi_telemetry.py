import yamlr_native
import time

# 1. Initialize Native Telemetry
telemetry = yamlr_native.NativeTelemetry()

print("Starting ROI Telemetry Stress Test...")
start_time = time.time()

# 2. Record 1,000 Scans and 500 Heals
for i in range(1000):
    yamlr_native.native_record_telemetry(telemetry, "SCAN", 0.0, 50)
    
for i in range(500):
    # Each heal reduces risk by 0.15 and takes 200ms
    yamlr_native.native_record_telemetry(telemetry, "HEAL", 0.15, 200)

duration = time.time() - start_time
print(f"Telemetry Recording Completed in {duration:.6f}s")

# 3. Aggregate ROI Metrics
total_saved_hours = telemetry.total_time_saved_ms / (1000 * 60 * 60)
print("\n--- Yamlr ROI Report (Enterprise Grade) ---")
print(f"Scans Completed: {telemetry.scans_completed}")
print(f"Heals Completed: {telemetry.heals_completed}")
print(f"Total Risk Mitigated: {telemetry.total_risk_mitigated:.2f}")
print(f"Total Time Saved: {total_saved_hours:.2f} hours")

# ROI Calculation: Assume SRE cost is $150/hr
dollars_saved = total_saved_hours * 150
print(f"Estimated Cost Savings: ${dollars_saved:,.2f}")
