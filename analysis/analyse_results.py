
import pandas as pd
import matplotlib.pyplot as plt
import os
import seaborn as sns
import numpy as np


plt.figure(figsize=(12,12))
# sns.set(font_scale = 2)
sns.set_style({'font.family':'serif', 'font.serif':'Times New Roman'})
base = pd.read_csv("/home/annelot/WARMSTART_PROJECT/analysis/baseline_results_per_epsilon.csv") 
#put your own directories here 
warm = pd.read_csv("/home/annelot/WARMSTART_PROJECT/analysis/results_no_err.csv")
#put your own directories here
base = base.drop(columns=[c for c in ["Unnamed: 0"] if c in base.columns])

base_keep = base[[
    "mps_path", "time", "epsilon_value", "result",
    "network_name", "image_name"
]].copy()

df = warm.merge(
    base_keep.add_prefix("inst2_"),
    left_on="second_mps",
    right_on="inst2_mps_path",
    how="left"
)

df = df.merge(
    base_keep.add_prefix("inst1_"),
    left_on="first_mps",
    right_on="inst1_mps_path",
    how="left"
)

df = df.rename(columns={
    "time": "inst2_time_warmstart",
    "result": "inst2_result_warmstart"
})


df["inst2_time_baseline"] = df["inst2_time"]

out = df[[
    "second_mps",
    "inst2_time_baseline",
    "inst2_time_warmstart",
    "warmstart_type",
    "configuration",

    "inst2_epsilon_value",
    "inst2_result_warmstart",   # warmstart outcome
    "inst2_network_name",
    "inst2_image_name",
    "inst2_mps_path",

    "inst1_epsilon_value",
    "inst1_network_name",
    "inst1_image_name",
    "inst1_mps_path",
]].copy()

# (optional) if you also want baseline result of inst2 in the output:
out["inst2_result_baseline"] = df["inst2_result"]

out.to_csv("combined_results.csv")


out  = pd.read_csv("/home/annelot/WARMSTART_PROJECT/analysis/combined_results.csv")
''' HERE WE START THE SCATTERPLOTS'''


save_dir = "/home/annelot/WARMSTART_PROJECT/analysis/figures/scatterplots"

df = out.copy()

xcol = "inst2_time_baseline"
ycol = "inst2_time_warmstart"


timeout_before = df["inst2_result_baseline"].astype(str).str.upper().eq("TIMEOUT")
err_after = df["inst2_result_warmstart"].astype(str).str.upper().eq("ERR")
df.loc[err_after, ycol] = 3600.0

plot_groups = {
    "UNSAT_warmstarts": ["UNSAT-UNSAT", "UNSAT-TIMEOUT"],
    "SAT_warmstarts": ["SAT-SAT", "SAT-TIMEOUT"],
    "IMAGE_warmstarts": ["IMAGE"],
    "NETWORK_warmstarts": ["NETWORK"],
}

def save_scatter(df_sub, title, filename):
    df_sub = df_sub.dropna(subset=[xcol, ycol]).copy()

    plt.figure(figsize=(6, 5))

    # Boolean masks
    is_timeout_before = timeout_before.loc[df_sub.index]
    is_err = err_after.loc[df_sub.index]
    is_sat = df_sub["inst2_result_warmstart"] == "SAT"

    is_normal =  ~is_timeout_before & ~is_sat

    # Normal (UNSAT, no timeout)
    if any(is_normal):
        plt.scatter(
            df_sub.loc[is_normal, xcol],
            df_sub.loc[is_normal, ycol],
            label="UNSAT",
            alpha=0.7
        )

    # SAT warmstart results (orange)
    if any(is_sat):
        plt.scatter(
            df_sub.loc[is_sat, xcol],
            df_sub.loc[is_sat, ycol],
            color="orange",
            label="SAT",
            alpha=0.8
        )

    # Timeout-before (red)
    plt.scatter(
        df_sub.loc[is_timeout_before, xcol],
        df_sub.loc[ is_timeout_before, ycol],
        color="red",
        label="Timeout before",
        alpha=0.7
    )

    # ERR warmstart (green)
    if any(is_err):
        plt.scatter(
            df_sub.loc[is_err, xcol],
            df_sub.loc[is_err, ycol],
            color="green",
            label="ERR warmstart",
            alpha=0.7
        )

    # y = x reference line
    if len(df_sub) > 0:
        mn = min(df_sub[xcol].min(), df_sub[ycol].min())
        mx = max(df_sub[xcol].max(), df_sub[ycol].max())
        plt.plot([mn, mx], [mn, mx], linestyle="--", linewidth=1)

    plt.xlabel("Baseline running time of target instance (s)")
    plt.ylabel("Warmstarted running time of target instance (s)")
    plt.legend()
    plt.tight_layout()
    plt.xscale("log")
    plt.yscale("log")

    out_path = os.path.join(save_dir, filename)
    plt.savefig(out_path, format="pdf", bbox_inches="tight")
    plt.close()

    print(f"Saved: {out_path}")


for key, types in plot_groups.items():
    df_sub = df[df["warmstart_type"].isin(types)]
    save_scatter(df_sub, key.replace("_", " "), f"{key}.pdf")
    
    
'''Make table '''

t_base = "inst2_time_baseline"
t_warm = "inst2_time_warmstart"
r_base = "inst2_result_baseline"
r_warm = "inst2_result_warmstart"
network = "inst2_network_name"
warmtype = "warmstart_type"

SOLVED = {"SAT", "UNSAT"}

def is_solved(x):
    return x in SOLVED

def is_timeout(x):
    return x == "TIMEOUT"

def fmt_mu_sigma(s):
    s = pd.to_numeric(s, errors="coerce").dropna()
    if s.empty:
        return "-"
    return f"{s.mean():.3f} ± {s.std(ddof=0):.3f}"

def fmt_number_or_dash(x, fmt="{:.3f}"):
    if x is None or (isinstance(x, float) and (np.isnan(x))):
        return "-"
    try:
        return fmt.format(float(x))
    except Exception:
        return "-"

# --- prepare dataframe ---
df2 = df.copy()
df2[t_base] = pd.to_numeric(df2[t_base], errors="coerce")
df2[t_warm] = pd.to_numeric(df2[t_warm], errors="coerce")

df2["baseline_solved"] = df2[r_base].apply(is_solved)
df2["warm_solved"] = df2[r_warm].apply(is_solved)
df2["baseline_timeout"] = df2[r_base].apply(is_timeout)
df2["warm_timeout"] = df2[r_warm].apply(is_timeout)

# comparison (same logic as before)
def compare(row):
    if row["baseline_timeout"] and row["warm_solved"]:
        return "better"
    if row["baseline_solved"] and row["warm_timeout"]:
        return "worse"
    if row["baseline_solved"] and row["warm_solved"]:
        if pd.notna(row[t_warm]) and pd.notna(row[t_base]):
            if row[t_warm] < row[t_base]:
                return "better"
            if row[t_warm] > row[t_base]:
                return "worse"
    return "equal"

df2["comparison"] = df2.apply(compare, axis=1)

# --- aggregation with reductions ---
rows = []
groups = df2.groupby([network, warmtype], sort=True)
for (net, wtype), g in groups:
    # numeric averages (ignore NaNs)
    avg_base = g[t_base].dropna().mean() if not g[t_base].dropna().empty else np.nan
    avg_warm = g[t_warm].dropna().mean() if not g[t_warm].dropna().empty else np.nan
    
    n_err = len(g[g.inst2_result_warmstart == "ERR"])
    print(n_err)

    # absolute and percentage reductions
    if np.isnan(avg_base) or np.isnan(avg_warm):
        abs_red = np.nan
        pct_red = np.nan
    else:
        abs_red = avg_base - avg_warm
        pct_red = (abs_red / avg_base * 100.0) if (avg_base != 0) else np.nan

    rows.append({
        "network": net,
        "warmstart_type": wtype,
        "results": len(g),
        "time_baseline": fmt_mu_sigma(g[t_base]),
        "time_warmstart": fmt_mu_sigma(g[t_warm]),
        "n_better": int((g["comparison"] == "better").sum()),
        "n_worse": int((g["comparison"] == "worse").sum()),
        "n_timedout_before_solved_now": int(((g["baseline_timeout"]) & (g["warm_solved"])).sum()),
        # new columns (formatted)
        "abs_reduction_avg_time": fmt_number_or_dash(abs_red, "{:.3f}"),
        "pct_reduction_time": fmt_number_or_dash(pct_red, "{:.1f}%"),
        # (optional: include raw numeric averages if you want to inspect)
        "_avg_baseline_numeric": (avg_base if not np.isnan(avg_base) else None),
        "n_err_warmstart": n_err,
        "_avg_warm_numeric": (avg_warm if not np.isnan(avg_warm) else None),
    })

summary_table = pd.DataFrame(rows).sort_values(["network", "warmstart_type"]).reset_index(drop=True)

# drop the helper numeric-average columns if you don't want them visible:
summary_table = summary_table.drop(columns=["_avg_baseline_numeric", "_avg_warm_numeric"])

summary_table
summary_table.to_csv("warmstart_summary.csv", index=False)



g_net = df2[df2[warmtype] == "NETWORK"]

def mean_std_str(s):
    s = pd.to_numeric(s, errors="coerce").dropna()
    if s.empty:
        return "-"
    return f"{s.mean():.3f} ± {s.std(ddof=0):.3f}"

print("=== NETWORK warmstart (aggregated across all networks) ===")
print(f"Baseline time : {mean_std_str(g_net[t_base])}")
print(f"Warmstart time: {mean_std_str(g_net[t_warm])}")
print(f"#instances    : {len(g_net)}")




df3 = df2.loc[df2.inst2_time_warmstart > df2.inst2_time_baseline].copy()

df3["increase"] = (
    df3["inst2_time_warmstart"] - df3["inst2_time_baseline"]
) / df3["inst2_time_baseline"]

print(df3["increase"].sum()/ len(df3["increase"]))