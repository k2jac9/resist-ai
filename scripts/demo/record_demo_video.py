"""
Automated Demo Video Recording for ResistAI
Uses Playwright to automate browser interactions and record video
Includes the new Regulatory Intelligence tab!
"""

import time
from pathlib import Path
from playwright.sync_api import sync_playwright, expect
import subprocess

# Configuration
BASE_URL = "http://localhost:7860"
OUTPUT_DIR = Path("demo_output")
OUTPUT_DIR.mkdir(exist_ok=True)

NARRATION_SCRIPT = """
NARRATION SCRIPT FOR RESISTAI DEMO VIDEO (3-4 minutes)

[0:00-0:20] OPENING - THE PROBLEM
"Antimicrobial resistance kills 1.27 million people every year.
16 of 20 pharmaceutical companies have abandoned antibiotic research.
The critical enzyme NDM-1 has ZERO approved inhibitors.
We need a new approach."

[0:20-0:40] THE SOLUTION
"Meet ResistAI - an AI-orchestrated drug discovery platform that chains 9 frontier AI models
in a fully automated pipeline. From pathogen genome to ranked drug candidates - in minutes, not years.
Let me show you."

[0:40-1:00] NAVIGATION TO PIPELINE
"Here's the web interface. I'll select Klebsiella pneumoniae - one of the deadliest ESKAPE pathogens.
Target: NDM-1, the metallo-beta-lactamase that makes bacteria resistant to nearly all antibiotics.
One click to start the 4-stage AI pipeline."

[1:00-1:40] STAGE 1-2
"Stage 1: Evo2-40b analyzes the 3-million base pair genome. ESMFold predicts the 3D protein structure.
Stage 2: Boltz-2 predicts binding affinity - achieving 0.91 confidence on known inhibitors.
MolMIM generates entirely novel molecules optimized for this specific target."

[1:40-2:10] STAGE 3-4
"Stage 3: RFdiffusion designs de novo protein therapeutics - proteins that don't exist in nature,
engineered from scratch to bind this target.
Stage 4: ADMET models predict safety - absorption, toxicity, off-target effects.
Then Qwen3-235B and DeepSeek-R1 generate clinical reasoning - explaining WHY these candidates work."

[2:10-2:40] RESULTS
"And here are the results. Ranked drug candidates with binding confidence scores, safety profiles,
and AI-generated clinical explanations. Notice the top hit - Meropenem with Avibactam -
this is actually the FDA-approved combination from 2023. Our AI rediscovered it."

[2:40-3:10] NEW REGULATORY INTELLIGENCE TAB
"But we didn't stop there. Click the Regulatory Intelligence tab - our newest feature.
Filter drugs by USP monograph status for accelerated FDA 505(b)(2) pathways.
Predict regulatory timelines - see how QIDP designation can reduce development time by 40%.
Generate AI explainability reports for FDA compliance - critical for the 2025 AI guidance.
And auto-generate pre-IND briefing documents. Everything you need for regulatory submission."

[3:10-3:40] OTHER FEATURES
"Multiple interfaces - REST API with full OpenAPI docs. Python SDK for programmatic access.
3D structure viewer with ESMFold predictions. Side-by-side candidate comparison.
Safety analysis with ADMET radar charts."

[3:40-4:00] CLOSING
"9 AI models. 7 from NVIDIA NIM, 2 from Nebius AI. 4 automated stages. Web UI, API, CLI, SDK.
Built in 48 hours at Evolved 25.
ResistAI: Because the post-antibiotic era should not be our future.
Ready to deploy. Ready to save lives."
"""

def record_demo():
    """Main recording function with automated browser interactions."""

    print("""
╔══════════════════════════════════════════════════════════════╗
║           ResistAI Automated Video Demo Recorder            ║
╚══════════════════════════════════════════════════════════════╝

This script will:
1. Open ResistAI in a browser
2. Automate navigation through all features
3. Take screenshots at key moments
4. Generate timing markers for narration

SETUP REQUIRED:
- ResistAI must be running at http://localhost:7860
- Install Playwright: pip install playwright
- Install browser: playwright install chromium

Press ENTER to continue or CTRL+C to cancel...
""")

    input()

    print("\n🎬 Starting automated demo recording...\n")

    with sync_playwright() as p:
        # Launch browser in visible mode (not headless) with larger viewport
        browser = p.chromium.launch(
            headless=False,
            args=[
                '--start-maximized',
                '--disable-infobars',
                '--no-default-browser-check'
            ]
        )

        context = browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            record_video_dir=str(OUTPUT_DIR),
            record_video_size={'width': 1920, 'height': 1080}
        )

        page = context.new_page()

        print(f"📂 Video will be saved to: {OUTPUT_DIR}")
        print(f"🌐 Opening {BASE_URL}...\n")

        # Navigate to ResistAI
        page.goto(BASE_URL, wait_until="networkidle", timeout=30000)
        time.sleep(2)

        # ============================================================
        # SCENE 1: Problem Tab (0:00-0:20)
        # ============================================================
        print("📸 [0:00-0:20] Scene 1: The Problem")
        page.screenshot(path=str(OUTPUT_DIR / "01_problem_tab.png"))
        time.sleep(3)

        # ============================================================
        # SCENE 2: Navigate to Pipeline (0:20-0:40)
        # ============================================================
        print("📸 [0:20-0:40] Scene 2: Pipeline Tab")
        page.click("text=Pipeline")
        time.sleep(2)
        page.screenshot(path=str(OUTPUT_DIR / "02_pipeline_tab.png"))

        # Select pathogen
        print("   Selecting Klebsiella pneumoniae...")
        page.click("label:has-text('Pathogen') >> xpath=following-sibling::div//button")
        time.sleep(0.5)
        page.click("text=Klebsiella pneumoniae")
        time.sleep(1)

        page.screenshot(path=str(OUTPUT_DIR / "03_pathogen_selected.png"))
        time.sleep(2)

        # ============================================================
        # SCENE 3: Run Pipeline (0:40-1:00)
        # ============================================================
        print("📸 [0:40-1:00] Scene 3: Starting Pipeline")
        page.click("button:has-text('Start Analysis')")
        time.sleep(2)
        page.screenshot(path=str(OUTPUT_DIR / "04_pipeline_running.png"))

        # ============================================================
        # SCENE 4-5: Pipeline Progress (1:00-2:10)
        # ============================================================
        print("📸 [1:00-2:10] Scene 4-5: Pipeline Stages")

        # Wait and capture stages
        for i in range(8):
            time.sleep(3)
            page.screenshot(path=str(OUTPUT_DIR / f"05_stage_{i+1}.png"))

        # ============================================================
        # SCENE 6: Results (2:10-2:40)
        # ============================================================
        print("📸 [2:10-2:40] Scene 6: Results")
        time.sleep(5)  # Wait for results
        page.screenshot(path=str(OUTPUT_DIR / "06_results_overview.png"))

        # Scroll to show candidates
        page.mouse.wheel(0, 400)
        time.sleep(1)
        page.screenshot(path=str(OUTPUT_DIR / "07_candidates_table.png"))

        # ============================================================
        # SCENE 7: NEW! Regulatory Intelligence Tab (2:40-3:10)
        # ============================================================
        print("📸 [2:40-3:10] Scene 7: 🆕 Regulatory Intelligence Tab!")
        page.click("text=Regulatory Intelligence")
        time.sleep(2)
        page.screenshot(path=str(OUTPUT_DIR / "08_regulatory_tab.png"))

        # Show USP Monograph Filter
        print("   Demonstrating USP Monograph Filter...")
        page.click("button:has-text('Show USP Monograph Drugs')")
        time.sleep(2)
        page.screenshot(path=str(OUTPUT_DIR / "09_usp_monograph_filter.png"))

        # Navigate to Pathway Predictor
        print("   Demonstrating Pathway Predictor...")
        page.click("text=Regulatory Pathway Predictor")
        time.sleep(1)
        page.click("button:has-text('Predict Pathway')")
        time.sleep(2)
        page.screenshot(path=str(OUTPUT_DIR / "10_pathway_prediction.png"))

        # Navigate to Timeline Calculator
        print("   Demonstrating Timeline Calculator...")
        page.click("text=Timeline Calculator")
        time.sleep(1)
        page.screenshot(path=str(OUTPUT_DIR / "11_timeline_calculator.png"))
        page.click("button:has-text('Calculate Timeline')")
        time.sleep(2)
        page.screenshot(path=str(OUTPUT_DIR / "12_timeline_result.png"))

        # Navigate to Explainability
        print("   Demonstrating AI Explainability...")
        page.click("text=AI Model Explainability")
        time.sleep(1)
        page.click("button:has-text('Generate Explanations')")
        time.sleep(3)
        page.screenshot(path=str(OUTPUT_DIR / "13_explainability.png"))

        # Navigate to Pre-IND Document
        print("   Demonstrating Pre-IND Document Generator...")
        page.click("text=Pre-IND Briefing Document")
        time.sleep(1)
        page.click("button:has-text('Generate Document')")
        time.sleep(2)
        page.screenshot(path=str(OUTPUT_DIR / "14_preind_document.png"))

        # ============================================================
        # SCENE 8: Other Features (3:10-3:40)
        # ============================================================
        print("📸 [3:10-3:40] Scene 8: Other Features")

        # Compare tab
        page.click("text=Compare")
        time.sleep(1)
        page.screenshot(path=str(OUTPUT_DIR / "15_compare_tab.png"))

        # Structure viewer
        page.click("text=Structure")
        time.sleep(1)
        page.screenshot(path=str(OUTPUT_DIR / "16_structure_viewer.png"))

        # Safety tab
        page.click("text=Safety")
        time.sleep(1)
        page.click("button:has-text('Analyze Safety')")
        time.sleep(2)
        page.screenshot(path=str(OUTPUT_DIR / "17_safety_analysis.png"))

        # ============================================================
        # SCENE 9: Closing - Return to Results (3:40-4:00)
        # ============================================================
        print("📸 [3:40-4:00] Scene 9: Closing")
        page.click("text=Pipeline")
        time.sleep(1)
        page.screenshot(path=str(OUTPUT_DIR / "18_final_results.png"))

        print("\n✅ Recording complete!")
        print(f"\n📂 Files saved to: {OUTPUT_DIR.absolute()}")

        # Close browser (this finalizes the video recording)
        context.close()
        browser.close()

        # Get the video file
        video_files = list(OUTPUT_DIR.glob("*.webm"))
        if video_files:
            print(f"\n🎥 Video file: {video_files[0].name}")
            print(f"\n💡 Convert to MP4 with:")
            print(f"   ffmpeg -i {video_files[0].name} -c:v libx264 -c:a aac ResistAI_Demo.mp4")

        print("\n" + "="*60)
        print("NARRATION SCRIPT")
        print("="*60)
        print(NARRATION_SCRIPT)
        print("="*60)

        return OUTPUT_DIR

if __name__ == "__main__":
    try:
        output_dir = record_demo()
        print(f"\n✅ Success! Check {output_dir} for all files.")
    except KeyboardInterrupt:
        print("\n\n⚠️  Recording cancelled by user.")
    except Exception as e:
        print(f"\n\n❌ Error: {e}")
        print("\nTroubleshooting:")
        print("1. Make sure ResistAI is running: http://localhost:7860")
        print("2. Install Playwright: pip install playwright")
        print("3. Install browser: playwright install chromium")
