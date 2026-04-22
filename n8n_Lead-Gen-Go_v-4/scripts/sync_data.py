import os
import shutil

PROJECT_ROOT = "/home/t0n34781/n8n-icp-stack"

TARGET_DIR = os.path.join(PROJECT_ROOT, "data")

# Source file locations (from your scan results)
FILES = {
    "analyzed_leads.json": [
        "/home/t0n34781/Downloads/analyzed_leads.json",
        "/home/t0n34781/prjcts_in_prgrss/n8n_flows/data/input/analyzed_leads.json"
    ],
    "healthcare_leads_30350.csv": [
        "/home/t0n34781/Downloads/healthcare_leads_30350.csv"
    ]
}

def move_file(src, dest_name):
    try:
        if os.path.exists(src):
            dest = os.path.join(TARGET_DIR, dest_name)
            shutil.copy2(src, dest)
            print(f"[OK] Copied {src} → {dest}")
            return True
    except Exception as e:
        print(f"[ERROR] {src}: {e}")
    return False

def ensure_dirs():
    os.makedirs(TARGET_DIR, exist_ok=True)

def main():
    ensure_dirs()

    print("=== SYNCING DATA INTO PROJECT ===")

    for filename, paths in FILES.items():
        moved = False
        for p in paths:
            if move_file(p, filename):
                moved = True
                break

        if not moved:
            print(f"[WARN] Missing file: {filename}")

    print("\n=== SYNC COMPLETE ===")

if __name__ == "__main__":
    main()
