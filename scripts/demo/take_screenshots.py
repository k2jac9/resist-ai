"""
Automated Screenshot Capture for Demo Video
Takes screenshots of the Gradio UI at key moments

Requires:  pip install -r scripts/demo/requirements-demo.txt
"""
import sys

try:
    import pyautogui
except ImportError:
    print("pyautogui not installed. Run: pip install -r scripts/demo/requirements-demo.txt")
    sys.exit(1)

import time
from pathlib import Path
from datetime import datetime

# Create output directory
output_dir = Path("demo_screenshots")
output_dir.mkdir(exist_ok=True)

def take_screenshot(name: str, description: str = ""):
    """Take and save a screenshot"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = output_dir / f"{timestamp}_{name}.png"
    screenshot = pyautogui.screenshot()
    screenshot.save(filename)
    print(f"✓ Captured: {name}")
    if description:
        print(f"  {description}")
    return filename

def wait_for_user(message: str):
    """Pause and wait for user to press Enter"""
    input(f"\n{message}\nPress ENTER when ready...")

print("""
╔══════════════════════════════════════════════════════════╗
║      ResistAI Demo Screenshot Capture Tool              ║
╔══════════════════════════════════════════════════════════╗

This script will guide you through capturing screenshots
for your demo video. Follow the prompts!

SETUP:
1. Open http://localhost:7860 in your browser
2. Maximize the browser window (F11 for full screen)
3. Position this terminal window to the side

Press CTRL+C at any time to stop.
""")

wait_for_user("Setup complete? Browser open and maximized?")

# Screenshot 1: Problem Tab
print("\n📸 Screenshot 1: The Problem")
wait_for_user("Navigate to 'The Problem' tab and position view")
take_screenshot("01_problem_tab", "AMR statistics and crisis overview")

# Screenshot 2: Pipeline Tab - Empty
print("\n📸 Screenshot 2: Pipeline Tab (Before)")
wait_for_user("Click 'Run Pipeline' tab")
take_screenshot("02_pipeline_empty", "Pipeline interface before execution")

# Screenshot 3: Pathogen Selected
print("\n📸 Screenshot 3: Pathogen Selection")
wait_for_user("Select 'Klebsiella pneumoniae' from dropdown")
take_screenshot("03_pathogen_selected", "Pathogen dropdown selected")

# Screenshot 4: Target Selected
print("\n📸 Screenshot 4: Target Selection")
wait_for_user("Select 'NDM-1' from target dropdown")
take_screenshot("04_target_selected", "Both pathogen and target selected")

# Screenshot 5: Pipeline Running - Stage 1
print("\n📸 Screenshot 5: Pipeline Stage 1")
wait_for_user("Click 'Run Pipeline' button, wait for Stage 1 to start")
take_screenshot("05_stage1_running", "Target Discovery in progress")

# Screenshot 6: Pipeline Running - Stage 2
print("\n📸 Screenshot 6: Pipeline Stage 2")
wait_for_user("Wait for Stage 2 (Drug Screening) to be visible")
take_screenshot("06_stage2_running", "Drug Screening in progress")

# Screenshot 7: Pipeline Running - Stage 3
print("\n📸 Screenshot 7: Pipeline Stage 3")
wait_for_user("Wait for Stage 3 (Protein Design) to be visible")
take_screenshot("07_stage3_running", "Protein Design in progress")

# Screenshot 8: Results
print("\n📸 Screenshot 8: Results Overview")
wait_for_user("Wait for pipeline to complete, view results")
take_screenshot("08_results_overview", "Complete results with ranked candidates")

# Screenshot 9: Candidate Details
print("\n📸 Screenshot 9: Candidate Details")
wait_for_user("Click on the top candidate to expand details")
take_screenshot("09_candidate_details", "Detailed view with binding, ADMET, reasoning")

# Screenshot 10: Compare Tab
print("\n📸 Screenshot 10: Compare Tab")
wait_for_user("Navigate to 'Compare' tab")
take_screenshot("10_compare_tab", "Side-by-side comparison interface")

# Screenshot 11: 3D Viewer
print("\n📸 Screenshot 11: 3D Structure Viewer")
wait_for_user("Navigate to 'Structure Viewer' tab")
take_screenshot("11_3d_viewer", "3D protein structure visualization")

# Screenshot 12: API Docs (Bonus)
print("\n📸 Screenshot 12: API Documentation (Bonus)")
wait_for_user("Open http://localhost:8000/docs in a new tab (or skip with ENTER)")
try:
    take_screenshot("12_api_docs", "OpenAPI documentation")
except:
    print("  Skipped")

print(f"""
╔══════════════════════════════════════════════════════════╗
║                  ✓ SCREENSHOTS COMPLETE!                ║
╔══════════════════════════════════════════════════════════╗

Screenshots saved to: {output_dir.absolute()}

Next steps:
1. Review screenshots in the folder
2. Use PowerPoint to create video:
   - Insert → Photo Album → All screenshots
   - Set transitions (2-3 sec per slide)
   - Record audio narration (Slide Show → Record Slide Show)
   - Export as Video (File → Export → Create Video)

Or use screenshots in video editing software!
""")
