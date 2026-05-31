---
name: pdf-ocr
description: Use when asked to OCR, convert, extract text from PDF files, or convert PDF to markdown. Takes one or more PDF file paths as arguments. Converts pages to images via pdftoppm, reads each with Claude vision, externalizes embedded figures/charts/diagrams to separate image files, and produces a markdown file referencing them.
---

# PDF OCR (Vision-based)

Convert PDF files to markdown using Claude's vision capabilities. No external libraries — only poppler CLI tools (`pdftoppm`, `pdftotext`, `pdfimages`) and Claude's `Read` tool.

## Arguments

Space-separated PDF file paths passed after the skill invocation.

## Workflow

For each PDF file:

### 1. Setup output directory

```
<pdf-name>/
  <pdf-name>.md        # Final markdown output
  images/              # Externalized figures, charts, diagrams
  pages/               # Intermediate page images (delete after)
```

Create output dir next to the source PDF (sibling directory named after the PDF without extension).

### 2. Convert PDF to page images

```bash
pdftoppm -png -scale-to 1800 "input.pdf" "<output-dir>/pages/page"
```

### 3. Detect figure pages with pdfimages

```bash
pdfimages -list "input.pdf" 2>/dev/null | awk 'NR>2 {p[$1]++} END {for(k in p) if(p[k]>=3) print k}' | sort -n
```

This deterministically identifies which pages contain embedded images (≥3 image objects = likely a figure). Pass this list to each subagent so it knows which pages to externalize — no guessing needed.

### 4. Parallel page processing with subagents

**CRITICAL: Never read more than 3 pages in one agent context.**

Split pages into chunks of max 3 pages each. Dispatch up to 20 subagents in parallel. Pass each subagent:
- Its page image paths
- The list of figure pages from step 3

Each subagent:
1. Reads its 3 (or fewer) page images with the `Read` tool
2. Transcribes ALL text faithfully into markdown — including text that starts or ends mid-sentence at page boundaries
3. For pages flagged as figure pages: copies the page PNG to `images/` with a descriptive name. All text on that page (caption, body text, data tables) is STILL transcribed as markdown text — the image is only for non-text visual content
4. Writes its chunk to `<output-dir>/chunks/chunk_NN.md`

### 5. Assemble final markdown

After all subagents complete:
1. Concatenate chunks in order into `<pdf-name>.md`
2. Insert `---` between chunks (page breaks)
3. **Fix chunk boundaries**: where one chunk ends mid-sentence and the next starts mid-sentence, join them into one continuous sentence (remove the `---` between them)
4. Verify total page count matches expected

### 6. Cleanup

Delete `pages/` and `chunks/` directories. Keep only the final `.md` and `images/`.

## Subagent Prompt Template

```
You are performing PDF OCR using Claude's vision capabilities.

Read the following page images and transcribe ALL content to markdown:
- [list of 1-3 page image paths]

Pages that contain figures (detected by pdfimages): [list of page numbers, e.g. "3, 5, 6"]

Output directory for images: [path to images/]

Rules:
- Transcribe ALL text on your assigned pages, even if it starts or ends mid-sentence
  (the assembly step handles continuity across chunks)
- Tables → markdown tables, preserve ALL numerical data exactly
- For pages listed as figure pages:
  • Copy the full page image to images/ (e.g., page_05_figure2.png)
  • Transcribe ALL text from that page normally:
    - Body text → regular markdown
    - Figure caption → **Figure N.** description as markdown text
    - Data tables within/below figures → markdown tables
  • Insert ![short alt](images/page_NN_figureN.png) at the position where the visual
    content (charts, blots, graphs, photographs) appears
  • The image file supplements the text — everything readable must be transcribed
- For pages NOT listed as figure pages: transcribe text only, no image needed
- Multi-column layouts → linearize left-to-right, top-to-bottom
- Math/formulas → LaTeX $...$ or $$...$$
- Omit repetitive headers/footers (page numbers, journal name, "Downloaded from...")

Write output to: [chunk path]
```

## Rules

- **No pip install, no Python libraries** — only poppler CLI tools (`pdftoppm`, `pdftotext`, `pdfimages`) and `sips` (macOS) or `convert` (ImageMagick) if cropping needed
- **Max 3 pages per subagent** — non-negotiable; context overflow causes truncation and data errors
- **Up to 20 parallel subagents** — for a 60-page PDF, dispatch 20 agents processing 3 pages each
- **Faithful transcription**: reproduce text exactly as written, don't summarize or interpret
- **Tables**: always render as markdown tables, preserve ALL numerical data exactly as printed
- **Math/formulas**: use LaTeX notation `$...$` or `$$...$$`
- **Multi-column layouts**: linearize sensibly (left-to-right, top-to-bottom)
- **Poor quality pages**: flag with `[LOW QUALITY - may contain errors]`
- **Languages**: preserve original language, don't translate
- **Mid-sentence boundaries**: transcribe everything — don't drop text at page edges

## Post-completion verification

### Structural checks
- Number of `---` separators ≈ number of pages (no chunks missing)
- File is not truncated (ends with complete content, not mid-sentence)
- Every figure page detected in step 3 has a corresponding file in `images/`
- No mid-sentence breaks remain (fix during assembly)

### Numerical verification via pdftotext

Vision OCR can misread digits (8→6, 5→3, 0→6). Use `pdftotext` as deterministic ground truth:

```bash
pdftotext -layout "input.pdf" "<output-dir>/raw_text.txt"
```

Then compare numbers:
1. Extract all multi-digit numbers from the vision markdown (especially in table rows)
2. Find the same rows/context in `raw_text.txt`
3. Any mismatch → replace the vision number with the pdftotext number

**Why not just use pdftotext alone?** It loses all structure — tables become space-padded lines, figures disappear, multi-column layouts scramble. Vision gives structure + images; pdftotext gives accurate numbers. Combine both.

Delete `raw_text.txt` after verification.

## Example Output Structure

```
Turner-2024-2/
  Turner-2024-2.md
  images/
    page_05_figure1_study_design.png
    page_08_figure2_kaplan_meier.png
```

In the markdown:
```markdown
# Title of Paper

## Abstract
[transcribed text...]

## Results

[body text above figure...]

**Figure 1.** Study design showing randomization and treatment arms...

![Figure 1 panels: study design flowchart](images/page_05_figure1_study_design.png)

[body text below figure continues naturally...]

| Endpoint | Treatment | Control | HR (95% CI) |
|----------|-----------|---------|--------------|
| PFS      | 15.0 mo   | 7.3 mo  | 0.43 (0.32-0.59) |

**Figure 2.** Kaplan-Meier curves for investigator-assessed PFS...

![Figure 2: KM PFS curves](images/page_08_figure2_kaplan_meier.png)
```

Note: caption and data tables are TEXT (searchable, verifiable). The image is only for visual content that cannot be rendered as text.
