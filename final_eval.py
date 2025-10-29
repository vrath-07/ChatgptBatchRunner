# final_eval.py
# Master controller to run TDI + PFI evaluation for multiple participant folders (P1–P20)

import os
import pandas as pd
from evaluateTDI import run_full_pipeline as run_TDI
from evaluatePFI import run_full_pipeline as run_PFI  # new import

# -------------------- USER CONFIG --------------------
BASE_DIR = r"G:\IITG\Fellowship\Experiment Design\Validation Of Assesment"
N_PARTICIPANTS = 1  # adjust if more/less samples exist

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
                "Global_Macro_TDI": tdi_md["global_macro_tdi"],
                "Bootstrap_Mean_TDI": tdi_md["bootstrap_mean"],
                "Bootstrap_CI_Lower": tdi_md["bootstrap_CI"][0],
                "Bootstrap_CI_Upper": tdi_md["bootstrap_CI"][1],
                "Global_Correlation_Index": tdi_md["GCI"],
                "PFI_Phase1": pfi_md["PFI_Phase1"],
                "PFI_Phase3": pfi_md["PFI_Phase3"],
                "MAAE_Phase1": pfi_md["MAAE_Phase1"],
                "MAAE_Phase3": pfi_md["MAAE_Phase3"],
                "PFI_Change": pfi_md["PFI_Change"],
                "MAAE_Change": pfi_md["MAAE_Change"],
                "Timestamp": tdi_md["timestamp"]
            })
            print(f"✅ {pid} complete.\n")

        except Exception as e:
            print(f"❌ {pid} failed: {e}")
            summary_records.append({
                "Participant": pid,
                "Global_Macro_TDI": None,
                "Bootstrap_Mean_TDI": None,
                "Bootstrap_CI_Lower": None,
                "Bootstrap_CI_Upper": None,
                "Global_Correlation_Index": None,
                "PFI_Phase1": None,
                "PFI_Phase3": None,
                "MAAE_Phase1": None,
                "MAAE_Phase3": None,
                "PFI_Change": None,
                "MAAE_Change": None,
                "Timestamp": None,
                "Error": str(e)
            })

    # -------------------- SAVE SUMMARY --------------------
    summary_df = pd.DataFrame(summary_records)
    summary_path = os.path.join(BASE_DIR, "All_Participants_TDI_PFI_Summary.csv")
    summary_df.to_csv(summary_path, index=False)

    print("\n📊 All participant TDI + PFI analyses complete.")
    print(f"Summary file saved at:\n{summary_path}")

# -------------------- RUN --------------------
if __name__ == "__main__":
    main()
