"""
compute_MAAE_PFI_from_JSON_v2.py
Author: Study 1 — Validation & Trait Consistency Analysis
Version: Final (with OCEAN vs Dark Triad split)

Purpose:
Compute persona-alignment and emergent deviation metrics directly from mapped response JSONs.

Metrics:
1️⃣ Mean Absolute Alignment Error (MAAE)
    → Avg. absolute deviation between induced and expressed trait levels.
    → Based on Bland & Altman (1986), *The Lancet*, agreement via absolute difference.

2️⃣ Persona Fidelity Index (PFI)
    → Cosine similarity between induced and expressed personality vectors.
    → Derived from Cronbach & Gleser (1953), *Psychological Bulletin*.

3️⃣ Dark Triad Deviation Index (DTDI)
    → Measures how much uninduced (neutral) traits deviate from 0.5 baseline.
    → Captures emergent bias in Machiavellianism, Narcissism, and Psychopathy.

Inputs:
- PHASE1_DIR: folder containing mapped response JSONs for Phase 1
- PHASE3_DIR: folder containing mapped response JSONs for Phase 3

Outputs:
- CSV summary (OCEAN MAAE/PFI + DTDI)
- Bar chart and radar chart for comparison
"""

import os
import json
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from sklearn.metrics.pairwise import cosine_similarity
from datetime import datetime

# -------------------- CONFIG --------------------
BIG_FIVE = ["Openness", "Conscientiousness", "Extraversion", "Agreeableness", "Neuroticism"]
DARK_TRIAD = ["Machiavellianism", "Narcissism", "Psychopathy"]
ALL_TRAITS = BIG_FIVE + DARK_TRIAD

# Induced persona (0–1 scale)
INDUCED_PROFILE = {
    "Openness": 0.7039,
    "Conscientiousness": 0.4851,
    "Extraversion": 0.5908,
    "Agreeableness": 0.5536,
    "Neuroticism": 0.2837
}
NEUTRAL_BASELINE = {t: 0.5 for t in DARK_TRIAD}


# -------------------- PATH HELPERS --------------------
def get_default_paths():
    """Default Phase paths for standalone testing."""
    PHASE1_DIR = r"G:\IITG\Fellowship\Experiment Design\Validation Of Assesment\P1\Phase 1\Mapped Responses"
    PHASE3_DIR = r"G:\IITG\Fellowship\Experiment Design\Validation Of Assesment\P1\Phase 3\Mapped Responses"
    OUTPUT_DIR = os.path.join(os.path.dirname(PHASE1_DIR), "Alignment_Outputs_v2")
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    return PHASE1_DIR, PHASE3_DIR, OUTPUT_DIR


# -------------------- CORE FUNCTIONS --------------------
def read_mapped_jsons(folder):
    """Reads mapped JSON responses and computes per-trait percent-high."""
    trait_high, trait_low = {t: 0 for t in ALL_TRAITS}, {t: 0 for t in ALL_TRAITS}

    for fname in sorted(os.listdir(folder)):
        if not fname.endswith(".json"):
            continue
        path = os.path.join(folder, fname)
        try:
            data = json.load(open(path, "r", encoding="utf-8"))
        except Exception as e:
            print(f"⚠️ Failed to parse {fname}: {e}")
            continue

        for item in data:
            trait, resp = item.get("trait"), item.get("response", "")
            if trait not in ALL_TRAITS:
                continue
            if isinstance(resp, str) and resp.startswith("response_high"):
                trait_high[trait] += 1
            elif isinstance(resp, str) and resp.startswith("response_low"):
                trait_low[trait] += 1

    percent_high = {}
    for t in ALL_TRAITS:
        total = trait_high[t] + trait_low[t]
        percent_high[t] = trait_high[t] / total if total > 0 else np.nan

    return percent_high


def compute_MAAE(observed, induced, traits):
    """Mean Absolute Alignment Error across selected traits."""
    return np.nanmean([abs(observed[t] - induced[t]) for t in traits])


def compute_PFI(observed, induced, traits):
    """Persona Fidelity Index (cosine similarity)."""
    v_ind = np.array([induced[t] for t in traits]).reshape(1, -1)
    v_obs = np.array([observed[t] for t in traits]).reshape(1, -1)
    return float(cosine_similarity(v_ind, v_obs)[0][0])


def compute_DTDI(observed, baseline):
    """Dark Triad Deviation Index (absolute deviation from 0.5 neutral baseline)."""
    return {t: abs(observed[t] - baseline[t]) for t in baseline}


# -------------------- VISUALIZATION --------------------
def plot_trait_bars(phase1, phase3, induced, dark_baseline, outpath):
    """Bar chart for induced (Big Five) and neutral (Dark Triad) traits."""
    all_traits = list(induced.keys()) + list(dark_baseline.keys())
    df = pd.DataFrame({
        "Induced/Neutral": [(induced.get(t) or dark_baseline.get(t)) * 100 for t in all_traits],
        "Phase 1": [phase1[t] * 100 for t in all_traits],
        "Phase 3": [phase3[t] * 100 for t in all_traits]
    }, index=all_traits)

    df.plot(kind="bar", figsize=(10, 6))
    plt.title("Induced vs Observed Trait Profiles (Phase 1 & 3)")
    plt.ylabel("Percent High (%)")
    plt.xticks(rotation=45)
    plt.ylim(0, 100)
    plt.grid(axis="y", linestyle="--", alpha=0.4)
    plt.tight_layout()
    plt.savefig(outpath, dpi=300)
    plt.close()


def plot_radar_chart(phase1, phase3, induced, dark_baseline, outpath):
    """Radar (spider) chart comparing profiles across all traits."""
    all_traits = list(induced.keys()) + list(dark_baseline.keys())
    labels = all_traits + [all_traits[0]]
    stats_ind = [(induced.get(t) or dark_baseline.get(t)) for t in all_traits] + [list(induced.values())[0]]
    stats_p1 = [phase1[t] for t in all_traits] + [phase1[all_traits[0]]]
    stats_p3 = [phase3[t] for t in all_traits] + [phase3[all_traits[0]]]

    angles = np.linspace(0, 2 * np.pi, len(labels))
    fig, ax = plt.subplots(figsize=(8, 8), subplot_kw=dict(polar=True))
    ax.plot(angles, stats_ind, "o-", linewidth=2, label="Induced/Neutral", color="gray")
    ax.plot(angles, stats_p1, "o-", linewidth=2, label="Phase 1", color="blue")
    ax.plot(angles, stats_p3, "o-", linewidth=2, label="Phase 3", color="red")
    ax.fill(angles, stats_p3, "r", alpha=0.1)
    ax.fill(angles, stats_p1, "b", alpha=0.1)
    ax.set_thetagrids(angles[:-1] * 180 / np.pi, all_traits)
    ax.set_ylim(0, 1)
    ax.set_title("Persona Profile Comparison (Induced/Neutral vs Phase 1 vs Phase 3)", size=13)
    ax.legend(loc="upper right", bbox_to_anchor=(1.25, 1.1))
    plt.tight_layout()
    plt.savefig(outpath, dpi=300)
    plt.close()


# -------------------- MAIN PIPELINE --------------------
def run_full_pipeline(phase1_dir, phase3_dir, outdir):
    """Run the full MAAE + PFI + DTDI computation pipeline (importable + standalone)."""
    os.makedirs(outdir, exist_ok=True)
    print("📘 Reading Phase 1 mapped responses...")
    phase1_means = read_mapped_jsons(phase1_dir)
    print("📗 Reading Phase 3 mapped responses...")
    phase3_means = read_mapped_jsons(phase3_dir)

    print("\n🔍 Computing metrics...")
    # Big Five alignment
    maae_phase1 = compute_MAAE(phase1_means, INDUCED_PROFILE, BIG_FIVE)
    maae_phase3 = compute_MAAE(phase3_means, INDUCED_PROFILE, BIG_FIVE)
    pfi_phase1 = compute_PFI(phase1_means, INDUCED_PROFILE, BIG_FIVE)
    pfi_phase3 = compute_PFI(phase3_means, INDUCED_PROFILE, BIG_FIVE)

    # Dark Triad deviation
    dtdi_phase1 = compute_DTDI(phase1_means, NEUTRAL_BASELINE)
    dtdi_phase3 = compute_DTDI(phase3_means, NEUTRAL_BASELINE)

    # Save summary CSV
    results = pd.DataFrame({
        "Metric": ["MAAE (OCEAN)", "PFI (OCEAN)"],
        "Phase 1": [maae_phase1, pfi_phase1],
        "Phase 3": [maae_phase3, pfi_phase3],
        "Change (P3 - P1)": [maae_phase3 - maae_phase1, pfi_phase3 - pfi_phase1]
    })
    results_path = os.path.join(outdir, "MAAE_PFI_summary.csv")
    results.to_csv(results_path, index=False)

    # Trait-level table
    traits_df = pd.DataFrame({
        "Trait": ALL_TRAITS,
        "Induced/Neutral (Prop)": [(INDUCED_PROFILE.get(t) or NEUTRAL_BASELINE.get(t)) for t in ALL_TRAITS],
        "Phase1 (Prop)": [phase1_means[t] for t in ALL_TRAITS],
        "Phase3 (Prop)": [phase3_means[t] for t in ALL_TRAITS],
        "Induced/Neutral (%)": [(INDUCED_PROFILE.get(t) or NEUTRAL_BASELINE.get(t)) * 100 for t in ALL_TRAITS],
        "Phase1 (%)": [phase1_means[t] * 100 for t in ALL_TRAITS],
        "Phase3 (%)": [phase3_means[t] * 100 for t in ALL_TRAITS],
    })

    # Add DTDI columns
    for t in DARK_TRIAD:
        traits_df.loc[traits_df["Trait"] == t, "DTDI_Phase1"] = dtdi_phase1[t]
        traits_df.loc[traits_df["Trait"] == t, "DTDI_Phase3"] = dtdi_phase3[t]

    traits_df.to_csv(os.path.join(outdir, "Trait_Level_Comparison.csv"), index=False)

    # Plots
    bar_path = os.path.join(outdir, "Trait_Profile_Bars.png")
    radar_path = os.path.join(outdir, "Persona_Profile_Radar.png")
    plot_trait_bars(phase1_means, phase3_means, INDUCED_PROFILE, NEUTRAL_BASELINE, bar_path)
    plot_radar_chart(phase1_means, phase3_means, INDUCED_PROFILE, NEUTRAL_BASELINE, radar_path)

    # ---------------- RETURN METADATA ----------------
    metadata = {
        "MAAE_Phase1": maae_phase1,
        "MAAE_Phase3": maae_phase3,
        "PFI_Phase1": pfi_phase1,
        "PFI_Phase3": pfi_phase3,
        "MAAE_Change": maae_phase3 - maae_phase1,
        "PFI_Change": pfi_phase3 - pfi_phase1,
        "DTDI_Phase1": dtdi_phase1,
        "DTDI_Phase3": dtdi_phase3,
        "timestamp": datetime.now().isoformat()
    }

    print("\n📊 Summary:")
    print(results.to_string(index=False))
    print(f"\n✅ Saved CSV: {results_path}")
    print(f"✅ Trait details: {os.path.join(outdir, 'Trait_Level_Comparison.csv')}")
    print(f"📈 Bar chart: {bar_path}")
    print(f"🕸️ Radar chart: {radar_path}")
    print("✅ COMPLETE — outputs saved to:", outdir)

    return {
        "metadata": metadata,
        "results": results,
        "traits_df": traits_df,
        "output_dir": outdir
    }


# -------------------- STANDALONE EXECUTION --------------------
if __name__ == "__main__":
    p1_dir, p3_dir, outdir = get_default_paths()
    run_full_pipeline(p1_dir, p3_dir, outdir)
