# Video Demo Recording Instructions

## 🎥 Recording Setup

### Option 1: Windows Game Bar (Built-in, Easiest)

**Steps:**
1. Press **Win + G** to open Game Bar
2. Click the **Record button** (circle icon) or press **Win + Alt + R**
3. A recording timer will appear in the corner
4. Perform your demo
5. Press **Win + Alt + R** again to stop
6. Video saves to: `C:\Users\[YourName]\Videos\Captures\`

**Settings:**
- Before recording: Win + G → Settings (gear icon)
- Set quality to "High" or "Standard"
- Enable audio if you want voiceover

---

### Option 2: OBS Studio (Professional, Free)

**Download:** https://obsproject.com/download

**Quick Setup:**
1. Install OBS Studio
2. Open OBS → Auto-Configuration Wizard
3. Select "Optimize for Recording"
4. Add source: Sources → + → Display Capture
5. Click "Start Recording"
6. Perform demo
7. Click "Stop Recording"
8. Videos save to: `C:\Users\[YourName]\Videos\`

---

### Option 3: PowerPoint Screen Recording

**Steps:**
1. Open PowerPoint (any blank presentation)
2. Insert → Screen Recording
3. Select area (or full screen)
4. Click Record button
5. Perform demo
6. Press **Win + Shift + Q** to stop
7. Right-click video in PowerPoint → Save Media As

---

## 🎬 Recording Checklist

### Before You Start:
- [ ] Close unnecessary apps and notifications
- [ ] Set browser to full screen (F11)
- [ ] Have DEMO_SCRIPT.md open on second monitor or printed
- [ ] Ensure http://localhost:7860 is loaded and ready
- [ ] Test microphone if doing voiceover
- [ ] Clear browser history/cache if needed for clean demo
- [ ] Disable pop-ups and notifications (Focus Assist: Win + A)

### What to Record:
- [ ] Duration: 2-3 minutes maximum
- [ ] Screen: Browser window with Gradio UI
- [ ] Audio: Optional voiceover (follow DEMO_SCRIPT.md)
- [ ] Quality: At least 720p (1280x720)

---

## 📝 Recording Script (Follow This)

### [0:00-0:15] Opening
1. Show "The Problem" tab briefly
2. Say: "Antimicrobial resistance kills 1.27 million people per year. NDM-1 has no approved inhibitor."

### [0:15-0:30] Navigate to Pipeline
1. Click "Run Pipeline" tab
2. Select "Klebsiella pneumoniae" from dropdown
3. Select "NDM-1" from target dropdown
4. Say: "ResistAI chains 9 AI models to automate drug discovery. Watch this."

### [0:30-0:45] Start Pipeline
1. Click "Run Pipeline" button
2. Say: "One click, and we're analyzing genomes, predicting structures, screening drugs, and generating molecules."

### [0:45-1:45] Explain Stages (While Running)
1. Point out Stage 1: "Evo2-40b finds resistance genes, ESMFold predicts 3D structure"
2. Point out Stage 2: "Boltz-2 predicts binding—0.91 confidence for known inhibitors. MolMIM generates novel molecules."
3. Point out Stage 3: "RFdiffusion designs new protein therapeutics from scratch"
4. Point out Stage 4: "ADMET predicts safety. Qwen3 and DeepSeek explain the results."

### [1:45-2:15] Show Results
1. Results appear—scroll through ranked candidates
2. Click top candidate to show details
3. Point out: "Binding confidence, safety scores, clinical reasoning—all automated."

### [2:15-2:45] Show Other Features
1. Quick click to "Compare" tab
2. Quick click to "3D Viewer" tab
3. Say: "Multiple interfaces—web UI, REST API, Python SDK, CLI."

### [2:45-3:00] Closing
1. Return to results or final summary
2. Say: "9 AI models. 4 stages. Minutes not years. ResistAI—built for Evolved 25. Ready to deploy."

---

## 🎙️ Voiceover Tips

**If Recording Audio:**
- Speak clearly and at moderate pace
- Don't rush—2-3 minutes is plenty
- Emphasize key numbers: "9 models", "0.91 confidence", "1.27 million deaths"
- Show enthusiasm but stay professional
- Pause briefly between sections

**If Silent Video:**
- Add text overlays in post-processing (optional)
- Include key stats as on-screen text
- Background music (optional, keep subtle)

---

## 🎞️ Post-Recording

### Review Checklist:
- [ ] Video plays without errors
- [ ] Demo flow is clear
- [ ] Key numbers are visible/audible
- [ ] Duration is 2-3 minutes
- [ ] Quality is acceptable (readable text)

### File Format:
- **Preferred:** MP4 (most compatible)
- **Resolution:** 720p or 1080p
- **Size:** Keep under 500MB (compress if needed)

### Upload Options:
1. **YouTube** (Unlisted)
   - Upload to YouTube
   - Set visibility to "Unlisted"
   - Copy link for submission

2. **Google Drive / Dropbox**
   - Upload video
   - Set sharing to "Anyone with link"
   - Copy link for submission

3. **Direct Submission** (if hackathon platform allows)
   - Upload MP4 file directly

---

## 🚨 Troubleshooting

### "Pipeline is taking too long"
- Stop recording
- Use cached results or screenshots
- Focus on UI navigation and explanation
- Mention "API rate limiting" if needed

### "Recording is laggy"
- Close background apps
- Lower recording quality
- Use Windows Game Bar (lighter than OBS)
- Record in shorter segments, combine later

### "No audio"
- Check mic permissions (Win + I → Privacy → Microphone)
- Test with Voice Recorder app first
- Silent video is fine—add text overlays

---

## ✅ Quick Start (Fastest Method)

**Right Now:**
1. **Win + G** (open Game Bar)
2. Click **Record button**
3. Open browser to http://localhost:7860
4. Navigate to "Run Pipeline" tab
5. Select pathogen + target
6. Click "Run Pipeline"
7. Narrate stages as they execute (or stay silent)
8. Show results when done
9. **Win + Alt + R** to stop
10. Video saved automatically to Videos\Captures

**Done in 3 minutes!**

---

## 📹 Alternative: Screenshots + Voiceover

If video recording is difficult:
1. Take 8-10 screenshots of key moments
2. Record voiceover separately (Voice Recorder app)
3. Use PowerPoint to combine:
   - Insert screenshots
   - Add audio file
   - Export as video (File → Export → Create Video)

---

## 🎯 What Judges Want to See

1. **Problem** - AMR crisis, statistics
2. **Solution** - 9 models, 4 stages, automation
3. **Live Demo** - Actual pipeline execution
4. **Results** - Real data, confidence scores
5. **Impact** - Lives saved, market opportunity

**Focus on these. Everything else is bonus.**

---

**Ready to record? Follow the Quick Start method above!**

**Good luck! 🚀🎬**
