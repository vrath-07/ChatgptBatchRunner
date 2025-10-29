# evaluateTDI.py
# Final integrated TDI pipeline: full output version (importable + standalone)
# Requirements: pandas, numpy, matplotlib, seaborn, sklearn
# pip install pandas numpy matplotlib seaborn scikit-learn

import os
import json
import math
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from sklearn.utils import resample
from datetime import datetime

# -------------------- CONFIG --------------------
# Default folder helper (for standalone use only)
def get_default_paths():
    PHASE1_DIR = r"G:\IITG\Fellowship\Experiment Design\Validation Of Assesment\P1\Phase 1\Mapped Responses"
    PHASE3_DIR = r"G:\IITG\Fellowship\Experiment Design\Validation Of Assesment\P1\Phase 3\Mapped Responses"
    OUTPUT_DIR = os.path.join(os.path.dirname(PHASE1_DIR), "TDI_Outputs")
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    return PHASE1_DIR, PHASE3_DIR, OUTPUT_DIR
TRAITS = [
    "Openness", "Conscientiousness", "Extraversion", "Agreeableness",
    "Neuroticism", "Machiavellianism", "Narcissism", "Psychopathy"
]

SHORT_W, LONG_W = 8, 50
BOOTSTRAP_ITERS, RANDOM_SEED = 2000, 42

# -------------------- UTILITIES --------------------
def ensure_dir(d):
    os.makedirs(d, exist_ok=True)

def timestamp():
    return datetime.now().isoformat()

# -------------------- READ JSON MAPPED RESPONSES --------------------
def read_mapped_folder(folder):
    rows = []
    files = sorted([f for f in os.listdir(folder) if f.endswith(".json")])
    if not files:
        raise FileNotFoundError(f"No .json files found in {folder}")
    for fname in files:
        path = os.path.join(folder, fname)
        with open(path, "r", encoding="utf-8") as fh:
            try:
                data = json.load(fh)
            except Exception as e:
                print(f"Warning: failed to parse {path}: {e}")
                data = []
        row = {"Batch": fname}
        for t in TRAITS:
            row[f"{t}_high"], row[f"{t}_low"] = 0, 0
        for item in data:
            trait, resp = item.get("trait"), item.get("response", "")
            if trait not in TRAITS:
                continue
            if isinstance(resp, str) and resp.startswith("response_high"):
                row[f"{trait}_high"] += 1
            elif isinstance(resp, str) and resp.startswith("response_low"):
                row[f"{trait}_low"] += 1
        for t in TRAITS:
            h, l = row[f"{t}_high"], row[f"{t}_low"]
            total = h + l
            row[f"{t}_pct_high"] = h / total if total > 0 else np.nan
        rows.append(row)
    return pd.DataFrame(rows)

# -------------------- MICRO & ROLLING TDI --------------------
def compute_micro_tdi(df):
    micro_tdi = {}
    for t in TRAITS:
        p = df[f"{t}_pct_high"].astype(float).to_numpy()
        micro_tdi[t] = np.nanmean(np.abs(np.diff(p)))
    rolling = pd.DataFrame(index=df.index)
    for t in TRAITS:
        col = f"{t}_pct_high"
        series = df[col].astype(float)
        rolling[f"{t}_TDI_short"] = series.diff().abs().rolling(window=SHORT_W, min_periods=1).mean()
        rolling[f"{t}_TDI_long"]  = series.diff().abs().rolling(window=LONG_W,  min_periods=1).mean()
    return micro_tdi, rolling

# -------------------- PHASE SUMMARY --------------------
def phase_summary(df):
    mean, sd, entropy = {}, {}, {}
    for t in TRAITS:
        arr = df[f"{t}_pct_high"].astype(float).to_numpy()
        mean[t] = np.nanmean(arr)
        sd[t] = np.nanstd(arr, ddof=1)
        p = mean[t]
        if np.isnan(p) or p in (0.0, 1.0):
            entropy[t] = 0.0
        else:
            entropy[t] = -(p*math.log2(p) + (1-p)*math.log2(1-p))
    return mean, sd, entropy

# -------------------- MACRO TDI & BOOTSTRAP --------------------
def compute_macro_tdi(mean1, mean3):
    macro = {t: abs(mean3[t] - mean1[t]) for t in TRAITS}
    vals = [v for v in macro.values() if not np.isnan(v)]
    return macro, np.mean(vals) if vals else np.nan

def bootstrap_macro_tdi(df1, df3, n_boot=2000, seed=RANDOM_SEED):
    rng = np.random.default_rng(seed)
    boot_vals = []
    n1, n3 = df1.shape[0], df3.shape[0]
    for _ in range(n_boot):
        idx1 = rng.integers(0, n1, size=n1)
        idx3 = rng.integers(0, n3, size=n3)
        mean1 = {t: np.nanmean(df1.iloc[idx1][f"{t}_pct_high"]) for t in TRAITS}
        mean3 = {t: np.nanmean(df3.iloc[idx3][f"{t}_pct_high"]) for t in TRAITS}
        _, gtdi = compute_macro_tdi(mean1, mean3)
        boot_vals.append(gtdi)
    mean_boot = np.nanmean(boot_vals)
    lo, hi = np.nanpercentile(boot_vals, [2.5, 97.5])
    return mean_boot, (lo, hi)

# -------------------- SAVE PHASE FILES & PLOTS (keeps previous outputs) --------------------
def save_phase_outputs(df, micro_tdi, rolling, phase_name, outdir):
    pdir = os.path.join(outdir, phase_name)
    ensure_dir(pdir)
    df.to_csv(os.path.join(pdir, f"{phase_name}_batch_percent_high.csv"), index=False)
    pd.DataFrame.from_dict(micro_tdi, orient='index', columns=['micro_TDI']).to_csv(
        os.path.join(pdir, f"{phase_name}_micro_TDI_per_trait.csv"))
    rolling.to_csv(os.path.join(pdir, f"{phase_name}_rolling_TDI.csv"), index=False)

    # heatmap (traits x batches) using vmin=0,vmax=1 for clarity
    pct_matrix = np.vstack([df[f"{t}_pct_high"].astype(float).to_numpy() for t in TRAITS])
    fig, ax = plt.subplots(figsize=(14, 6))
    sns.heatmap(pct_matrix, ax=ax, cmap="vlag", center=0.5, vmin=0, vmax=1,
                xticklabels=False, yticklabels=TRAITS, cbar_kws={'label': 'Percent High (0-1)'})
    ax.set_title(f"{phase_name}: Percent-High Heatmap (traits x batches)")
    ax.set_xlabel("Batch index")
    ax.set_ylabel("Traits")
    fig.tight_layout()
    fig.savefig(os.path.join(pdir, f"{phase_name}_percent_high_heatmap.png"), dpi=300)
    plt.close(fig)

    # rolling TDI plots (short & long)
    fig2, axes = plt.subplots(nrows=4, ncols=2, figsize=(18, 20), sharex=True)
    axes = axes.flatten()
    for i, t in enumerate(TRAITS):
        ax = axes[i]
        ax.plot(rolling[f"{t}_TDI_short"], label=f"short W={SHORT_W}", alpha=0.9)
        ax.plot(rolling[f"{t}_TDI_long"],  label=f"long W={LONG_W}",  alpha=0.9)
        ax.set_title(f"{phase_name} — {t}")
        ax.set_ylabel("Rolling TDI (mean |Δ|)")
        ax.grid(True, linestyle='--', alpha=0.3)
        ax.legend(fontsize=9)
    for ax in axes[-2:]:
        ax.set_xlabel("Batch index")
    plt.suptitle(f"{phase_name}: Rolling TDI (short & long windows)", fontsize=18)
    fig2.tight_layout(rect=[0, 0.03, 1, 0.95])
    fig2.savefig(os.path.join(pdir, f"{phase_name}_rolling_TDI.png"), dpi=300)
    plt.close(fig2)

# -------------------- CROSS-PHASE COMPARISONS (NEW) --------------------
def cross_phase_comparison(df1, df3, outdir):
    cdir = os.path.join(outdir, "CrossPhase_Comparison")
    ensure_dir(cdir)

    # align length: use min number of batches to compare pairwise exactly (transparent)
    n = min(len(df1), len(df3))
    df1s, df3s = df1.iloc[:n].reset_index(drop=True), df3.iloc[:n].reset_index(drop=True)

    # 1) ΔMean per trait (Phase3 - Phase1)
    mean1 = {t: np.nanmean(df1s[f"{t}_pct_high"]) for t in TRAITS}
    mean3 = {t: np.nanmean(df3s[f"{t}_pct_high"]) for t in TRAITS}
    delta_mean = {t: mean3[t] - mean1[t] for t in TRAITS}
    mean_diff_df = pd.DataFrame({
        "Trait": TRAITS,
        "Phase1_MeanPct": [mean1[t] for t in TRAITS],
        "Phase3_MeanPct": [mean3[t] for t in TRAITS],
        "DeltaMean": [delta_mean[t] for t in TRAITS]
    })
    mean_diff_df.to_csv(os.path.join(cdir, "Phase_Comparison_MeanDiff.csv"), index=False)

    # Visual: ΔMean bar (colored by direction)
    plt.figure(figsize=(10,5))
    colors = ['#2ca02c' if v>0 else '#d62728' if v<0 else '#777777' for v in mean_diff_df["DeltaMean"]]
    plt.bar(mean_diff_df["Trait"], mean_diff_df["DeltaMean"], color=colors)
    plt.axhline(0, color='k', linewidth=0.6)
    plt.xticks(rotation=45, ha='right')
    plt.ylabel("Phase3 Mean - Phase1 Mean (ΔMean)")
    plt.title("Mean Trait Change (Phase3 minus Phase1)")
    plt.tight_layout()
    plt.savefig(os.path.join(cdir, "Phase_Comparison_DeltaMean_Bar.png"), dpi=300)
    plt.close()

    # Visual: radar plot for ΔMean (absolute magnitude)
    try:
        # radar requires circular axis; prepare values in same order
        labels = TRAITS
        values = [mean_diff_df.loc[mean_diff_df["Trait"]==t, "DeltaMean"].values[0] for t in labels]
        angles = np.linspace(0, 2 * np.pi, len(labels), endpoint=False).tolist()
        values_circ = values + values[:1]
        angles_circ = np.concatenate((angles, [angles[0]]))
        fig = plt.figure(figsize=(7,7))
        ax = fig.add_subplot(111, polar=True)
        ax.plot(angles_circ, values_circ, 'o-', linewidth=2)
        ax.fill(angles_circ, values_circ, alpha=0.25)
        ax.set_thetagrids(np.degrees(angles), labels)
        ax.set_title("Radar: ΔMean per Trait (Phase3 - Phase1)")
        ax.grid(True)
        plt.tight_layout()
        plt.savefig(os.path.join(cdir, "Phase_Comparison_DeltaMean_Radar.png"), dpi=300)
        plt.close(fig)
    except Exception as e:
        print("Radar plot failed:", e)

    # 2) Batch-aligned absolute drift series
    drift_df = pd.DataFrame(index=range(n))
    for t in TRAITS:
        drift_df[t] = (df3s[f"{t}_pct_high"] - df1s[f"{t}_pct_high"]).abs().astype(float)
    drift_df.to_csv(os.path.join(cdir, "Phase_Comparison_BatchDrift.csv"), index=False)

    # Plot a compact multi-panel of drift over batches
    fig, axes = plt.subplots(nrows=4, ncols=2, figsize=(18,20), sharex=True)
    axes = axes.flatten()
    for i, t in enumerate(TRAITS):
        ax = axes[i]
        ax.plot(drift_df[t], linewidth=0.8)
        ax.set_title(f"Batch-aligned absolute drift — {t}")
        ax.set_ylabel("|Phase3 - Phase1|")
        ax.grid(True, linestyle='--', alpha=0.3)
    for ax in axes[-2:]:
        ax.set_xlabel("Batch index")
    plt.suptitle("Batch-aligned absolute drift (Phase3 vs Phase1)", fontsize=16)
    plt.tight_layout(rect=[0, 0.03, 1, 0.95])
    plt.savefig(os.path.join(cdir, "Phase_Comparison_BatchDrift_Panels.png"), dpi=300)
    plt.close(fig)

    # 3) Correlations per trait (Pearson)
    corr_vals = {}
    for t in TRAITS:
        x = df1s[f"{t}_pct_high"].astype(float).to_numpy()
        y = df3s[f"{t}_pct_high"].astype(float).to_numpy()
        # if constant or all-NaN, corr will be nan
        if np.all(np.isnan(x)) or np.all(np.isnan(y)):
            corr_vals[t] = np.nan
        else:
            # mask pairwise NaNs
            mask = ~np.isnan(x) & ~np.isnan(y)
            if mask.sum() < 2:
                corr_vals[t] = np.nan
            else:
                corr_vals[t] = float(np.corrcoef(x[mask], y[mask])[0,1])
    corr_df = pd.DataFrame({
        "Trait": TRAITS,
        "Correlation": [corr_vals[t] for t in TRAITS]
    })
    corr_df.to_csv(os.path.join(cdir, "Phase_Comparison_Correlation.csv"), index=False)

    # Proper correlation heatmap (traits as rows)
    heat_df = corr_df.set_index("Trait")
    plt.figure(figsize=(6,8))
    sns.heatmap(heat_df, annot=True, cmap="coolwarm", vmin=-1, vmax=1, cbar_kws={'label': 'Pearson r'})
    plt.title("Phase1 vs Phase3: Trait Correlation (Pearson r)")
    plt.tight_layout()
    plt.savefig(os.path.join(cdir, "Phase_Comparison_Correlation_Heatmap.png"), dpi=300)
    plt.close()

    # Global Correlation Index (GCI)
    gci = np.nanmean([v for v in corr_vals.values() if not np.isnan(v)])

    return {
        "delta_mean_df": mean_diff_df,
        "batch_drift_df": drift_df,
        "corr_df": corr_df,
        "GCI": gci
    }

# -------------------- METADATA & INTEGRITY LOG --------------------
def write_integrity_log(df1, df3, outdir):
    log = {
        "timestamp": timestamp(),
        "phase1_batches": len(df1),
        "phase3_batches": len(df3),
        "phase1_nan_counts": {t: int(df1[f"{t}_pct_high"].isna().sum()) for t in TRAITS},
        "phase3_nan_counts": {t: int(df3[f"{t}_pct_high"].isna().sum()) for t in TRAITS},
        "note": "All downstream analyses use raw percent-high values. No smoothing/normalization applied for cross-phase computations."
    }
    with open(os.path.join(outdir, "Data_Integrity_Log.json"), "w") as fh:
        json.dump(log, fh, indent=2)

# -------------------- MAIN PIPELINE --------------------
def run_full_pipeline(p1_dir, p3_dir, outdir):
    print("Reading Phase 1..."); df1 = read_mapped_folder(p1_dir)
    print("Reading Phase 3..."); df3 = read_mapped_folder(p3_dir)

    # compute and save per-phase outputs (keeps prior behavior)
    micro1, roll1 = compute_micro_tdi(df1)
    micro3, roll3 = compute_micro_tdi(df3)
    ensure_dir(outdir)
    save_phase_outputs(df1, micro1, roll1, "Phase1", outdir)
    save_phase_outputs(df3, micro3, roll3, "Phase3", outdir)

    # phase summaries
    mean1, sd1, ent1 = phase_summary(df1)
    mean3, sd3, ent3 = phase_summary(df3)

    # macro & bootstrap
    macro, global_tdi = compute_macro_tdi(mean1, mean3)
    boot_mean, (boot_lo, boot_hi) = bootstrap_macro_tdi(df1, df3, n_boot=BOOTSTRAP_ITERS)

    # cross-phase comparisons (new)
    cross_res = cross_phase_comparison(df1, df3, outdir)

    # save macro table
    macro_df = pd.DataFrame({
        "Trait": TRAITS,
        "Macro_TDI": [macro[t] for t in TRAITS],
        "Phase1_MeanPct": [mean1[t] for t in TRAITS],
        "Phase3_MeanPct": [mean3[t] for t in TRAITS],
        "Phase1_SD": [sd1[t] for t in TRAITS],
        "Phase3_SD": [sd3[t] for t in TRAITS],
        "Entropy_Phase1_bits": [ent1[t] for t in TRAITS],
        "Entropy_Phase3_bits": [ent3[t] for t in TRAITS]
    })
    macro_df.to_csv(os.path.join(outdir, "Macro_TDI_between_Phase1_Phase3.csv"), index=False)

    # integrity and metadata
    write_integrity_log(df1, df3, outdir)
    metadata = {
        "phase1_dir": p1_dir,
        "phase3_dir": p3_dir,
        "traits": TRAITS,
        "short_window": SHORT_W,
        "long_window": LONG_W,
        "bootstrap_iters": BOOTSTRAP_ITERS,
        "timestamp": timestamp(),
        "global_macro_tdi": global_tdi,
        "bootstrap_mean": boot_mean,
        "bootstrap_CI": [boot_lo, boot_hi],
        "GCI": cross_res["GCI"]
    }
    with open(os.path.join(outdir, "Metadata.json"), "w") as fh:
        json.dump(metadata, fh, indent=2)

    # human readable summary
    with open(os.path.join(outdir, "TDI_Full_Report.txt"), "w", encoding="utf-8") as fh:
        fh.write("Trait Drift Index (TDI) - Full Report\n")
        fh.write("Generated: " + timestamp() + "\n\n")
        fh.write("Phase 1 mean percent-high (per trait):\n")
        for t in TRAITS:
            fh.write(f"{t}: mean={mean1[t]:.4f}, sd={sd1[t]:.4f}, entropy={ent1[t]:.4f}\n")
        fh.write("\nPhase 3 mean percent-high (per trait):\n")
        for t in TRAITS:
            fh.write(f"{t}: mean={mean3[t]:.4f}, sd={sd3[t]:.4f}, entropy={ent3[t]:.4f}\n")
        fh.write("\nMacro TDI (Phase3 vs Phase1) per trait:\n")
        for t in TRAITS:
            fh.write(f"{t}: Macro_TDI={macro[t]:.4f}\n")
        fh.write(f"\nGlobal Macro TDI (mean across traits): {global_tdi:.4f}\n")
        fh.write(f"Bootstrap mean Global TDI: {boot_mean:.4f}; 95% CI = [{boot_lo:.4f}, {boot_hi:.4f}]\n")
        fh.write(f"\nGlobal Correlation Index (GCI): {cross_res['GCI']:.4f}\n")
        fh.write("\nNotes: All computations performed on raw percent-high batch-level data from mapped JSON files. No preprocessing applied for cross-phase comparisons.\n")

    print("✅ COMPLETE — outputs saved to:", outdir)
    return {
        "phase1_df": df1, "phase3_df": df3,
        "macro_df": macro_df,
        "cross_phase": cross_res,
        "metadata": metadata
    }

# -------------------- STANDALONE RUN --------------------
if __name__ == "__main__":
    p1_dir, p3_dir, outdir = get_default_paths()
    run_full_pipeline(p1_dir, p3_dir, outdir)
