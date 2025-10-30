# final_eval.py
# Master controller to run TDI + PFI evaluation for multiple participant folders (P1–P20)
# Generates both per-participant outputs (unchanged) and consolidated group-level summary + visuals

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
os.makedirs(CONSOLIDATED_DIR, exist_ok=True)

# -------------------- MAIN LOOP --------------------
def main():
    summary_records = []

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

    # -------------------- VISUALIZATIONS --------------------
    if not summary_df.empty:
        try:
            # 1️⃣ PFI vs TDI scatter
            plt.figure(figsize=(7,6))
            sns.scatterplot(data=summary_df, x="Global_TDI", y="Phase3_PFI", s=100)
            plt.title("Persona Fidelity (PFI) vs Stability (TDI)")
            plt.xlabel("Global Trait Drift Index (TDI)")
            plt.ylabel("Phase 3 Persona Fidelity (PFI)")
            plt.grid(True, linestyle="--", alpha=0.4)
            plt.tight_layout()
            plt.savefig(os.path.join(CONSOLIDATED_DIR, "PFI_vs_TDI_Scatter.png"), dpi=300)
            plt.close()

            # 2️⃣ ΔPFI and ΔMAAE bar plot
            plt.figure(figsize=(10,6))
            summary_df.plot(
                x="Participant",
                y=["ΔPFI", "ΔMAAE"],
                kind="bar",
                figsize=(10,6),
                color=["#1f77b4", "#ff7f0e"]
            )
            plt.title("Change in Alignment Metrics (ΔPFI & ΔMAAE)")
            plt.ylabel("Change (Phase 3 − Phase 1)")
            plt.xticks(rotation=45, ha="right")
            plt.tight_layout()
            plt.savefig(os.path.join(CONSOLIDATED_DIR, "Change_PFI_MAAE_Bar.png"), dpi=300)
            plt.close()

            # 3️⃣ Correlation heatmap
            numeric_df = summary_df.select_dtypes(include=[float, int]).dropna(axis=1, how="all")
            corr = numeric_df.corr()
            plt.figure(figsize=(10,8))
            sns.heatmap(corr, annot=True, cmap="coolwarm", center=0)
            plt.title("Correlation Matrix — TDI, PFI, MAAE, and DTDI Metrics")
            plt.tight_layout()
            plt.savefig(os.path.join(CONSOLIDATED_DIR, "Metric_Correlation_Heatmap.png"), dpi=300)
            plt.close()

            # 4️⃣ ΔDTDI change bar plot
            plt.figure(figsize=(10,6))
            sns.barplot(data=summary_df, x="Participant", y="ΔDTDI", color="#9467bd")
            plt.title("Emergent Bias Change (ΔDTDI across Participants)")
            plt.ylabel("ΔDTDI (Phase 3 − Phase 1)")
            plt.xticks(rotation=45, ha="right")
            plt.tight_layout()
            plt.savefig(os.path.join(CONSOLIDATED_DIR, "Change_DTDI_Bar.png"), dpi=300)
            plt.close()

            # 5️⃣ Optional — save README summary
            with open(os.path.join(CONSOLIDATED_DIR, "README_Summary.txt"), "w", encoding="utf-8") as fh:
                fh.write("📘 Study 1 — Consolidated Persona Evaluation Summary\n\n")
                fh.write(f"Total Participants: {len(summary_df)}\n")
                fh.write(f"CSV: {summary_path}\n\n")
                fh.write("Generated Visualizations:\n")
                fh.write("- PFI_vs_TDI_Scatter.png\n")
                fh.write("- Change_PFI_MAAE_Bar.png\n")
                fh.write("- Metric_Correlation_Heatmap.png\n")
                fh.write("- Change_DTDI_Bar.png\n")
                fh.write("\nAll visualizations are cross-participant summaries.\n")

            print(f"📈 Consolidated visualizations saved to: {CONSOLIDATED_DIR}")

        except Exception as e:
            print(f"⚠️ Visualization step failed: {e}")

# -------------------- RUN --------------------
if __name__ == "__main__":
    main()
