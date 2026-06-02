"""
Generate ResistAI Hackathon Presentation
Creates a professional PowerPoint for demo and submission
"""
from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
from pptx.dml.color import RGBColor

# Create presentation
prs = Presentation()
prs.slide_width = Inches(16)  # 16:9 aspect ratio
prs.slide_height = Inches(9)

# Color scheme
COLOR_PRIMARY = RGBColor(34, 139, 34)  # Green for life/health
COLOR_ACCENT = RGBColor(220, 20, 60)   # Red for urgency/crisis
COLOR_TEXT = RGBColor(44, 62, 80)      # Dark gray
COLOR_BG = RGBColor(245, 245, 245)     # Light gray

def add_title_slide(title, subtitle=""):
    """Add a title slide"""
    slide = prs.slides.add_slide(prs.slide_layouts[6])  # Blank

    # Add background
    background = slide.shapes.add_shape(
        1, 0, 0, prs.slide_width, prs.slide_height
    )
    background.fill.solid()
    background.fill.fore_color.rgb = COLOR_PRIMARY

    # Title
    title_box = slide.shapes.add_textbox(
        Inches(1), Inches(3), Inches(14), Inches(2)
    )
    title_frame = title_box.text_frame
    title_frame.text = title
    title_frame.paragraphs[0].font.size = Pt(60)
    title_frame.paragraphs[0].font.bold = True
    title_frame.paragraphs[0].font.color.rgb = RGBColor(255, 255, 255)
    title_frame.paragraphs[0].alignment = PP_ALIGN.CENTER

    # Subtitle
    if subtitle:
        subtitle_box = slide.shapes.add_textbox(
            Inches(1), Inches(5.5), Inches(14), Inches(1)
        )
        subtitle_frame = subtitle_box.text_frame
        subtitle_frame.text = subtitle
        subtitle_frame.paragraphs[0].font.size = Pt(28)
        subtitle_frame.paragraphs[0].font.color.rgb = RGBColor(255, 255, 255)
        subtitle_frame.paragraphs[0].alignment = PP_ALIGN.CENTER

def add_content_slide(title, content_lines):
    """Add a content slide with bullet points"""
    slide = prs.slides.add_slide(prs.slide_layouts[6])  # Blank

    # Title
    title_box = slide.shapes.add_textbox(
        Inches(0.5), Inches(0.5), Inches(15), Inches(1)
    )
    title_frame = title_box.text_frame
    title_frame.text = title
    title_frame.paragraphs[0].font.size = Pt(44)
    title_frame.paragraphs[0].font.bold = True
    title_frame.paragraphs[0].font.color.rgb = COLOR_PRIMARY

    # Content
    content_box = slide.shapes.add_textbox(
        Inches(1), Inches(2), Inches(14), Inches(6)
    )
    content_frame = content_box.text_frame
    content_frame.word_wrap = True

    for i, line in enumerate(content_lines):
        if i > 0:
            p = content_frame.add_paragraph()
        else:
            p = content_frame.paragraphs[0]

        p.text = line
        p.font.size = Pt(24)
        p.font.color.rgb = COLOR_TEXT
        p.space_after = Pt(12)
        p.level = 0 if not line.startswith("  ") else 1

def add_large_number_slide(title, number, description):
    """Add a slide with a large impactful number"""
    slide = prs.slides.add_slide(prs.slide_layouts[6])

    # Title
    title_box = slide.shapes.add_textbox(
        Inches(0.5), Inches(0.5), Inches(15), Inches(1)
    )
    title_frame = title_box.text_frame
    title_frame.text = title
    title_frame.paragraphs[0].font.size = Pt(40)
    title_frame.paragraphs[0].font.bold = True
    title_frame.paragraphs[0].font.color.rgb = COLOR_PRIMARY

    # Big number
    number_box = slide.shapes.add_textbox(
        Inches(2), Inches(2.5), Inches(12), Inches(2.5)
    )
    number_frame = number_box.text_frame
    number_frame.text = number
    number_frame.paragraphs[0].font.size = Pt(120)
    number_frame.paragraphs[0].font.bold = True
    number_frame.paragraphs[0].font.color.rgb = COLOR_ACCENT
    number_frame.paragraphs[0].alignment = PP_ALIGN.CENTER

    # Description
    desc_box = slide.shapes.add_textbox(
        Inches(2), Inches(5.5), Inches(12), Inches(2)
    )
    desc_frame = desc_box.text_frame
    desc_frame.text = description
    desc_frame.paragraphs[0].font.size = Pt(32)
    desc_frame.paragraphs[0].font.color.rgb = COLOR_TEXT
    desc_frame.paragraphs[0].alignment = PP_ALIGN.CENTER

# ============================================================================
# SLIDE 1: Title
# ============================================================================
add_title_slide(
    "ResistAI",
    "AI-Orchestrated Drug Discovery for Antimicrobial Resistance"
)

# ============================================================================
# SLIDE 2: Team
# ============================================================================
add_content_slide(
    "Team BioHack",
    [
        "📍 Evolved 25 Hackathon",
        "📅 Toronto, ON | March 27-29, 2026",
        "",
        "🏗️ Built in 48 hours",
        "🤖 9 AI models integrated",
        "🚀 Production-ready platform"
    ]
)

# ============================================================================
# SLIDE 3: The Problem - Statistics
# ============================================================================
add_large_number_slide(
    "The Crisis",
    "1.27M",
    "Deaths from antimicrobial resistance per year"
)

# ============================================================================
# SLIDE 4: The Problem - Details
# ============================================================================
add_content_slide(
    "The Post-Antibiotic Era",
    [
        "💀 4.95 million deaths associated with AMR annually",
        "",
        "🔬 Zero new antibiotic classes since 1987",
        "",
        "🏥 16 of 20 pharma companies abandoned antibiotics R&D",
        "",
        "⚠️ NDM-1 enzyme (critical pathogen) has NO approved inhibitor",
        "",
        "💰 Traditional discovery: 10+ years, $1+ billion, 90% failure rate"
    ]
)

# ============================================================================
# SLIDE 5: The Solution
# ============================================================================
add_title_slide(
    "ResistAI",
    "9 AI Models • 4 Stages • Minutes Not Years"
)

# ============================================================================
# SLIDE 6: What is ResistAI
# ============================================================================
add_content_slide(
    "What is ResistAI?",
    [
        "🎯 End-to-end AI drug discovery platform",
        "",
        "🔗 Orchestrates 9 frontier AI models in automated pipeline",
        "",
        "⚡ Input: Pathogen name",
        "📊 Output: Ranked drug candidates with safety scores + clinical reasoning",
        "",
        "⏱️ Time: Minutes (not 10+ years)",
        "",
        "💻 Access: Web UI, REST API, CLI, Python SDK"
    ]
)

# ============================================================================
# SLIDE 7: The 9 AI Models
# ============================================================================
add_content_slide(
    "9 AI Models Working Together",
    [
        "🧬 NVIDIA NIM Biology (7 models):",
        "  • Evo2-40b — Genomic analysis",
        "  • ESMFold — Protein structure prediction",
        "  • Boltz-2 — Binding prediction",
        "  • DiffDock — Molecular docking",
        "  • MolMIM — Novel molecule generation",
        "  • RFdiffusion — Protein backbone design",
        "  • ProteinMPNN — Protein sequence design",
        "",
        "🧠 Nebius AI Studio (2 models):",
        "  • Qwen3-235B — Clinical reasoning",
        "  • DeepSeek-R1 — Deep analysis"
    ]
)

# ============================================================================
# SLIDE 8: 4-Stage Pipeline
# ============================================================================
add_content_slide(
    "4-Stage Automated Pipeline",
    [
        "1️⃣ TARGET DISCOVERY",
        "  Evo2-40b → ESMFold",
        "  Genome analysis → 3D structure",
        "",
        "2️⃣ DRUG SCREENING + GENERATION",
        "  Boltz-2 → MolMIM",
        "  Binding prediction → Novel molecules",
        "",
        "3️⃣ PROTEIN DESIGN (De Novo)",
        "  RFdiffusion → ProteinMPNN",
        "  Backbone design → Sequence generation",
        "",
        "4️⃣ SAFETY + REASONING",
        "  ADMET → Qwen3/DeepSeek",
        "  Toxicity prediction → Clinical explanation"
    ]
)

# ============================================================================
# SLIDE 9: Live Demo Announcement
# ============================================================================
add_title_slide(
    "LIVE DEMO",
    "Watch ResistAI in Action"
)

# ============================================================================
# SLIDE 10: Demo Flow
# ============================================================================
add_content_slide(
    "What You'll See",
    [
        "1. Select pathogen: Klebsiella pneumoniae",
        "",
        "2. Select target: NDM-1",
        "",
        "3. Click 'Run Pipeline'",
        "",
        "4. Watch 4 stages execute automatically",
        "",
        "5. View ranked candidates with:",
        "  • Binding confidence scores",
        "  • ADMET safety predictions",
        "  • AI-generated clinical reasoning"
    ]
)

# ============================================================================
# SLIDE 11: Results - Numbers
# ============================================================================
add_large_number_slide(
    "Real Results",
    "0.91",
    "Binding confidence for FDA-approved inhibitors"
)

# ============================================================================
# SLIDE 12: Key Results
# ============================================================================
add_content_slide(
    "Documented Results",
    [
        "✅ Binding Predictions:",
        "  • 0.887-0.913 confidence for known inhibitors",
        "  • Validated on FDA-approved combinations (2023)",
        "",
        "✅ Novel Molecule Generation:",
        "  • QED drug-likeness: 0.82-0.93",
        "  • 10-50 molecules per run",
        "",
        "✅ De Novo Protein Design:",
        "  • 363-residue novel scaffold",
        "  • Sequence recovery: ~42%",
        "",
        "✅ 4 ESKAPE Pathogens Supported:",
        "  • Klebsiella, Acinetobacter, Pseudomonas, Enterobacter"
    ]
)

# ============================================================================
# SLIDE 13: Technical Excellence
# ============================================================================
add_content_slide(
    "Technical Excellence",
    [
        "🏗️ Architecture:",
        "  • 60+ Python files, modular design",
        "  • 4 interfaces: Web UI, REST API, CLI, SDK",
        "  • Async pipeline orchestration",
        "",
        "📚 Documentation:",
        "  • Comprehensive README",
        "  • OpenAPI docs for REST API",
        "  • Installation + usage guides",
        "",
        "✅ Production Ready:",
        "  • Error handling throughout",
        "  • Configurable via YAML",
        "  • Type hints + logging",
        "  • 0 vulnerabilities in dependencies"
    ]
)

# ============================================================================
# SLIDE 14: Business Model
# ============================================================================
add_content_slide(
    "Business Model & Impact",
    [
        "💰 Market Opportunity:",
        "  • $28.2B AMR therapeutics market by 2031",
        "  • 10M projected deaths/year by 2050",
        "",
        "🎯 Target Customers:",
        "  • Biotech startups (usage-based API)",
        "  • Pharma partnerships (co-development)",
        "  • Academic research (free tier)",
        "",
        "🏥 Regulatory Pathway:",
        "  • 505(b)(2) for repurposed drugs",
        "  • QIDP designation for priority review",
        "  • IND-ready output format",
        "",
        "💡 Cost Savings:",
        "  • $0.01 per pipeline vs $1B traditional"
    ]
)

# ============================================================================
# SLIDE 15: Innovation
# ============================================================================
add_content_slide(
    "What Makes ResistAI Unique",
    [
        "🥇 FIRST platform combining:",
        "  • Genomic analysis",
        "  • Molecule generation",
        "  • Protein design",
        "  • Safety prediction",
        "  • Clinical reasoning",
        "",
        "⚡ Dual Paradigm:",
        "  • Small molecule repurposing AND",
        "  • De novo protein therapeutic design",
        "",
        "🤖 AI-Explained Results:",
        "  • Not just predictions — explanations",
        "  • LLMs generate clinical rationale",
        "",
        "⏰ 48-Hour Build:",
        "  • Concept to production in hackathon timeframe"
    ]
)

# ============================================================================
# SLIDE 16: Next Steps
# ============================================================================
add_content_slide(
    "What's Next",
    [
        "🔬 Immediate:",
        "  • Wet-lab validation partnerships",
        "  • Enterprise SaaS deployment",
        "",
        "📈 Short-term:",
        "  • Expand to all ESKAPE pathogens",
        "  • Add fungal resistance (Candida auris)",
        "  • BARDA/CARB-X funding applications",
        "",
        "🌍 Long-term:",
        "  • Clinical trial partnerships",
        "  • Global deployment",
        "  • Save 1.27M lives per year"
    ]
)

# ============================================================================
# SLIDE 17: Key Numbers Summary
# ============================================================================
add_content_slide(
    "ResistAI By The Numbers",
    [
        "🤖 9 AI models orchestrated",
        "",
        "🔄 4 automated pipeline stages",
        "",
        "💻 4 access interfaces (UI, API, CLI, SDK)",
        "",
        "📊 0.887-0.913 binding confidence",
        "",
        "💀 1.27M deaths/year addressed",
        "",
        "💰 $28.2B market opportunity",
        "",
        "⏱️ 48 hours from concept to production"
    ]
)

# ============================================================================
# SLIDE 18: Why ResistAI Wins
# ============================================================================
add_title_slide(
    "Why ResistAI Wins",
    ""
)

# ============================================================================
# SLIDE 19: Why We Win - Details
# ============================================================================
add_content_slide(
    "Why ResistAI Should Win",
    [
        "❤️ Addresses Critical Need",
        "  • 1.27M deaths/year, zero new antibiotics",
        "",
        "⚙️ Technical Excellence",
        "  • 9 models, 4 interfaces, production-ready",
        "",
        "🤝 Uses ALL Sponsor Tech",
        "  • NVIDIA NIM (7 models) + Nebius AI (2 models)",
        "",
        "📈 Real Results",
        "  • Documented predictions, validated accuracy",
        "",
        "🚀 Production Ready",
        "  • Not a demo — deployable platform",
        "",
        "🌍 Impact Potential",
        "  • $28.2B market, saves lives"
    ]
)

# ============================================================================
# SLIDE 20: Closing - Thank You
# ============================================================================
add_title_slide(
    "Thank You",
    "Questions?"
)

# ============================================================================
# SLIDE 21: Contact
# ============================================================================
add_content_slide(
    "ResistAI",
    [
        "🌐 GitHub: github.com/[your-repo]/resist-ai",
        "",
        "👥 Team BioHack",
        "",
        "📧 Contact: biohack@evolved25.dev",
        "",
        "🎯 Built at Evolved 25 Hackathon",
        "   Toronto, ON | March 27-29, 2026",
        "",
        "",
        "💡 Because the post-antibiotic era",
        "   should not be our future."
    ]
)

# Save presentation
output_file = "ResistAI_Presentation.pptx"
prs.save(output_file)
print(f"Presentation created: {output_file}")
print(f"   - {len(prs.slides)} slides")
print(f"   - Ready for demo and video export")
