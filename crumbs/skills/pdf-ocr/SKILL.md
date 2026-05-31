---
name: pdf-ocr
description: Vision-based PDF to markdown converter. Converts pages to images via pdftoppm, reads with Claude vision in parallel subagents, externalizes figures, and produces a markdown file with image references.
---

# PDF OCR (Vision-based)

Tools: poppler CLI (`pdftoppm`, `pdftotext`, `pdfimages`), `sips`/`convert` for cropping, Claude `Read`. No pip install, no Python libraries.

Arguments: space-separated PDF file paths.

## Rules

- **Max 3 pages per subagent** — non-negotiable; context overflow causes truncation
- **Up to 20 parallel subagents**
- Faithful transcription — reproduce text exactly, don't summarize or translate
- Tables → markdown tables, preserve ALL numerical data exactly
- Math/formulas → LaTeX `$...$` or `$$...$$`
- Multi-column layouts → linearize left-to-right, top-to-bottom
- Poor quality pages → flag with `[LOW QUALITY - may contain errors]`
- Mid-sentence page boundaries → transcribe everything, assembly step handles continuity
- Figure pages: transcribe ALL text (captions, body, data tables) as markdown AND externalize the page image for non-text visual content

## Workflow

### 1. Setup output

Create sibling directory next to source PDF: `<pdf-name>/` containing `<pdf-name>.md`, `images/`, `pages/` (temp).

### 2. Convert to page images

```bash
pdftoppm -png -scale-to 1800 "input.pdf" "<output-dir>/pages/page"
```

### 3. Detect figure pages

```bash
pdfimages -list "input.pdf" 2>/dev/null | awk 'NR>2 {p[$1]++} END {for(k in p) if(p[k]>=3) print k}' | sort -n
```

Pages with ≥3 image objects are likely figures. Pass this list to every subagent.

### 4. Parallel subagent dispatch

Split into chunks of ≤3 pages. Each subagent receives: page image paths, figure page list, output path `chunks/chunk_NN.md`.

Subagent instructions:
- Read page images, transcribe all text to markdown (including mid-sentence boundaries)
- Figure pages: copy page PNG to `images/page_NN_figureN.png`, insert `![alt](images/...)` at visual content position, transcribe all text normally
- Non-figure pages: text only
- Omit repetitive headers/footers (page numbers, journal name)

### 5. Assemble

1. Concatenate chunks in order, insert `---` between them
2. Fix chunk boundaries — join split sentences, remove `---` between them
3. Verify page count matches

### 6. Verify

**Structural**: separator count ≈ page count, no truncation, every detected figure page has a file in `images/`, no mid-sentence breaks remain.

**Numerical**: vision OCR misreads digits (8→6, 5→3). Cross-check against `pdftotext -layout` output — extract multi-digit numbers from tables, compare, replace mismatches with pdftotext values. Delete raw_text.txt after.

### 7. Cleanup

Delete `pages/` and `chunks/`. Keep `<pdf-name>.md` and `images/`.

## Example Output

```
Turner-2024-2/
  Turner-2024-2.md
  images/
    page_05_figure1_study_design.png
    page_08_figure2_kaplan_meier.png
```

```markdown
## Results

[body text...]

**Figure 1.** Study design showing randomization...

![Figure 1: study design flowchart](images/page_05_figure1_study_design.png)

| Endpoint | Treatment | Control | HR (95% CI) |
|----------|-----------|---------|--------------|
| PFS      | 15.0 mo   | 7.3 mo  | 0.43 (0.32-0.59) |
```

Captions and data tables are TEXT. Images are only for non-text visual content.
