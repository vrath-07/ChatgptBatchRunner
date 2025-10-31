# final_eval.py
# Master controller to run TDI + PFI evaluation for multiple participant folders (P1–P20)
# Generates both per-participant outputs (unchanged) and consolidated group-level summary + macro-level trait visuals

import os
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from evaluateTDI import run_full_pipeline as run_TDI
from evaluatePFI import run_full_pipeline as run_PFI

# -------------------- USER CONFIG --------------------
BASE_DIR = r"G:\IITG\Fellowship\Experiment Design\Validation Of Assesment"
N_PARTICIPANTS = 19  # adjust as needed
CONSOLIDATED_DIR = os.path.join(BASE_DIR, "Consolidated_Output")
MACRO_DIR = os.path.join(CONSOLIDATED_DIR, "Macro_Level_Analysis")
os.makedirs(CONSOLIDATED_DIR, exist_ok=True)
os.makedirs(MACRO_DIR, exist_ok=True)

# -------------------- MAIN LOOP --------------------
def main():
    summary_records = []
    extended_trait_rows = []  # NEW: holds export_df data from all participants

    for i in range(1, N_PARTICIPANTS + 1):
        pid = f"P{i}"
        participant_dir = os.path.join(BASE_DIR, pid)
        phase1_dir = os.path.join(participant_dir, "Phase 1", "Mapped Responses")
        phase3_dir = os.path.join(participant_dir, "Phase 3", "Mapped Responses")
        tdi_outdir = os.path.join(participant_dir, "Results", "TDI_Outputs")
        pfi_outdir = os.path.join(participant_dir, "Results", "PFI_Outputs")

        print(f"\n🚀 Processing {pid} ...")
        try:
            # ---- Run TDI ----
            tdi_results = run_TDI(phase1_dir, phase3_dir, tdi_outdir)
            tdi_md = tdi_results["metadata"]
            export_df = tdi_results.get("export_df", pd.DataFrame())
            if not export_df.empty:
                export_df.insert(0, "Participant", pid)
                extended_trait_rows.append(export_df)

            # ---- Run PFI ----
            pfi_results = run_PFI(phase1_dir, phase3_dir, pfi_outdir)
            pfi_md = pfi_results["metadata"]

            # ---- Combine summaries ----
            summary_records.append({
                "Participant": pid,
                "Persona_Type": "Unknown",  # optionally update later if available
                "Timestamp": tdi_md["timestamp"],

                # --- TDI / Stability ---
                "Global_TDI": tdi_md["global_macro_tdi"],
                "Bootstrap_TDI": tdi_md["bootstrap_mean"],
                "Bootstrap_CI_Lower": tdi_md["bootstrap_CI"][0],
                "Bootstrap_CI_Upper": tdi_md["bootstrap_CI"][1],
                "Global_Correlation_Index": tdi_md["GCI"],

                # --- Alignment / Fidelity ---
                "Phase1_PFI": pfi_md["PFI_Phase1"],
                "Phase3_PFI": pfi_md["PFI_Phase3"],
                "ΔPFI": pfi_md["PFI_Change"],

                # --- Accuracy / Deviation ---
                "Phase1_MAAE": pfi_md["MAAE_Phase1"],
                "Phase3_MAAE": pfi_md["MAAE_Phase3"],
                "ΔMAAE": pfi_md["MAAE_Change"],

                # --- Emergent Bias / Dark Triad ---
                "Mean_DTDI_Phase1": np.nanmean(list(pfi_md["DTDI_Phase1"].values())),
                "Mean_DTDI_Phase3": np.nanmean(list(pfi_md["DTDI_Phase3"].values())),
                "ΔDTDI": (
                    np.nanmean(list(pfi_md["DTDI_Phase3"].values())) -
                    np.nanmean(list(pfi_md["DTDI_Phase1"].values()))
                ),
            })
            print(f"✅ {pid} complete.\n")

        except Exception as e:
            print(f"❌ {pid} failed: {e}")
            summary_records.append({
                "Participant": pid,
                "Error": str(e)
            })

    # -------------------- SAVE CONSOLIDATED SUMMARY --------------------
    summary_df = pd.DataFrame(summary_records)
    summary_path = os.path.join(CONSOLIDATED_DIR, "All_Participants_TDI_PFI_Summary.csv")
    summary_df.to_csv(summary_path, index=False)
    print(f"\n📊 All participant TDI + PFI analyses complete.")
    print(f"✅ Consolidated summary saved at:\n{summary_path}")

    # -------------------- NEW: Save per-trait extended consolidated CSV --------------------
    if extended_trait_rows:
        full_trait_df = pd.concat(extended_trait_rows, ignore_index=True)
        trait_csv_path = os.path.join(MACRO_DIR, "All_Participants_TraitDrift_Detailed.csv")
        full_trait_df.to_csv(trait_csv_path, index=False)
        print(f"🧩 Extended trait-level CSV saved at:\n{trait_csv_path}")

        # -------------------- MACRO-LEVEL VISUALIZATIONS --------------------
        print("\n📈 Generating Macro-Level Visualizations...")
        try:
            # Filter out noisy/missing data safely
            clean_df = full_trait_df.replace([np.inf, -np.inf], np.nan).dropna(subset=["Macro_TDI"], how="any")

            # 1️⃣ Global trait drift per trait (mean ± CI)
            plt.figure(figsize=(10,6))
            sns.barplot(data=clean_df, x="Trait", y="Macro_TDI", ci=95, capsize=0.2, palette="coolwarm")
            plt.title("Mean Macro Trait Drift (Phase3 − Phase1) ±95% CI")
            plt.ylabel("Macro TDI (|ΔTrait|)")
            plt.xticks(rotation=45, ha="right")
            plt.tight_layout()
            plt.savefig(os.path.join(MACRO_DIR, "MacroTraitDrift_Bar.png"), dpi=300)
            plt.close()

            # 2️⃣ Entropy change per trait
            plt.figure(figsize=(10,6))
            clean_df["Entropy_Diff"] = clean_df["Entropy_Phase3"] - clean_df["Entropy_Phase1"]
            sns.barplot(data=clean_df, x="Trait", y="Entropy_Diff", palette="crest")
            plt.title("Change in Trait Entropy (Phase3 − Phase1)")
            plt.ylabel("ΔEntropy (bits)")
            plt.xticks(rotation=45, ha="right")
            plt.tight_layout()
            plt.savefig(os.path.join(MACRO_DIR, "EntropyChange_Bar.png"), dpi=300)
            plt.close()

            # 3️⃣ Rolling TDI summary (short & long mean)
            plt.figure(figsize=(10,6))
            sns.scatterplot(
                data=clean_df,
                x="RollingTDI_ShortMean_Ph1",
                y="RollingTDI_ShortMean_Ph3",
                hue="Trait",
                style="Trait",
                s=100
            )
            plt.title("Rolling TDI (Short Window) — Phase1 vs Phase3")
            plt.xlabel("Phase1 Short-Window Mean TDI")
            plt.ylabel("Phase3 Short-Window Mean TDI")
            plt.tight_layout()
            plt.savefig(os.path.join(MACRO_DIR, "RollingTDI_Short_Scatter.png"), dpi=300)
            plt.close()

            # 4️⃣ Correlation heatmap (trait-level numeric)
            num_cols = clean_df.select_dtypes(include=[float, int])
            if not num_cols.empty:
                corr = num_cols.corr()
                plt.figure(figsize=(12,10))
                sns.heatmap(corr, cmap="vlag", center=0, annot=False)
                plt.title("Trait-Level Metric Correlation (Macro CSV)")
                plt.tight_layout()
                plt.savefig(os.path.join(MACRO_DIR, "TraitMetric_Correlation_Heatmap.png"), dpi=300)
                plt.close()

            # 5️⃣ Quality flags distribution
            plt.figure(figsize=(8,5))
            sns.countplot(data=clean_df.melt(value_vars=["Wide_CI_Flag", "Low_N_Flag"]),
                          x="variable", hue="value", palette="Set2")
            plt.title("Quality Flag Distribution Across Participants")
            plt.xlabel("Flag Type")
            plt.ylabel("Count")
            plt.tight_layout()
            plt.savefig(os.path.join(MACRO_DIR, "QualityFlags_Distribution.png"), dpi=300)
            plt.close()

            # 6️⃣ Rolling long-window vs Macro TDI
            plt.figure(figsize=(8,6))
            sns.scatterplot(data=clean_df, x="RollingTDI_LongMean_Ph3", y="Macro_TDI", hue="Trait", s=90)
            plt.title("Macro TDI vs Long-Window Rolling Drift (Phase3)")
            plt.xlabel("Rolling TDI (Long Mean)")
            plt.ylabel("Macro TDI")
            plt.tight_layout()
            plt.savefig(os.path.join(MACRO_DIR, "Macro_vs_RollingLong_Scatter.png"), dpi=300)
            plt.close()

            # 7️⃣ Global trait-level distribution
            plt.figure(figsize=(10,6))
            sns.boxplot(data=clean_df, x="Trait", y="Macro_TDI", palette="Spectral")
            plt.title("Distribution of Macro TDI per Trait (All Participants)")
            plt.ylabel("Macro TDI")
            plt.xticks(rotation=45, ha="right")
            plt.tight_layout()
            plt.savefig(os.path.join(MACRO_DIR, "MacroTDI_Trait_Boxplot.png"), dpi=300)
            plt.close()

            print(f"📊 Macro-level visualizations saved in: {MACRO_DIR}")

        except Exception as e:
            print(f"⚠️ Macro-level visualization failed: {e}")

    print("\n✅ COMPLETE — All outputs consolidated successfully.")

# -------------------- RUN --------------------
if __name__ == "__main__":
    main()
