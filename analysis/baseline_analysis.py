import pandas as pd

# Load baseline
df = pd.read_csv("/home/annelot/WARMSTART_PROJECT/analysis/baseline_results_per_epsilon.csv")

# Drop the unnamed index column if present
df = df.drop(columns=[c for c in ["Unnamed: 0"] if c in df.columns])

# Normalize result strings
df["result"] = df["result"].astype(str).str.upper().str.strip()

# Optional: map any unexpected results to "ERR"
valid = {"SAT", "UNSAT", "TIMEOUT", "ERR"}
df.loc[~df["result"].isin(valid), "result"] = "ERR"

# Create pivot table (counts)
summary = (
    df.pivot_table(
        index="network_name",
        columns="result",
        values="mps_path",   # any column works, we just want counts
        aggfunc="count",
        fill_value=0
    )
    .reset_index()
)

# Ensure all 4 columns exist
for col in ["SAT", "UNSAT", "ERR", "TIMEOUT"]:
    if col not in summary.columns:
        summary[col] = 0

# Reorder columns nicely
summary = summary[["network_name", "SAT", "UNSAT", "ERR", "TIMEOUT"]]

print(summary)
