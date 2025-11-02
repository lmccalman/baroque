# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Baroque is a Python application for processing 18th-century French handwritten journal scans through OCR and translation. The project uses Claude (Anthropic) models to extract French text from PDF/image scans, translate to English, and compile the results into formatted LaTeX documents for academic research.

## Development Commands

**Package Management:**
- Use `uv` for dependency management (configured in pyproject.toml)
- Install dependencies: `uv sync`
- Add new packages: `uv add <package>`

**Main Application:**
- Run CLI: `python main.py <command> [options]`
- Available commands: `extract`, `ocr`, `translate`, `collate`

**Example Workflow:**
```bash
# Extract images from PDF
python main.py extract "SP 84.532"

# Perform OCR on extracted images  
python main.py ocr "SP 84.532" --npages 5

# Translate French text to English
python main.py translate "SP 84.532"

# Collate everything into final LaTeX document
python main.py collate "SP 84.532"
```

## Architecture

**Core Modules:**
- `main.py`: CLI interface using Click, orchestrates the full pipeline
- `process.py`: Text processing functions for OCR, translation, and formatting using Claude/OpenAI APIs
- `pdf.py`: PDF processing utilities for extracting images and finding files
- `image.py`: Image processing using PIL for scaling and conversion
- `latex.py`: LaTeX document generation and compilation

**Data Flow:**
1. PDFs in `input_data/` → Extract images → `output/{notebook}/images/`
2. Images → OCR → `output/{notebook}/claude_ocr/` (French text + LaTeX)
3. French text → Translation → `output/{notebook}/claude_ocr_claude_trans/` (English text + LaTeX)  
4. All components → Collation → `output/{notebook}/` (Final PDF)

**AI Model Integration:**
- Uses Claude (Anthropic) models exclusively
- Prompts defined in `process.py` and `metaprompts.md`
- Claude handles OCR, translation, LaTeX formatting, and historical analysis
- Uses structured prompts with `<thinking>` and `<output>` tags

**Configuration:**
- Uses Claude models exclusively (no model selection needed)
- API key via environment variable: `ANTHROPIC_API_KEY`
- LaTeX compilation uses `lualatex` with specific font and layout settings

**File Organization:**
- Input PDFs: `input_data/{notebook_name}*.pdf` (naturally sorted)
- Outputs: `output/{notebook_name}/` with subdirectories for each processing stage
- Images saved as grayscale JPEGs with 4-digit page numbering