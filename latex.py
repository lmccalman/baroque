from pathlib import Path
import subprocess
import os

def create_latex_document(pages: list[tuple[Path, Path, Path]], output_path: Path):
    """
    Create a LaTeX document with multiple pages, each containing three columns:
    image, French text, and English text.

    Args:
        pages: List of 3-tuples containing (image_path, french_md_path, english_md_path)
        output_path: Path where the LaTeX file should be saved
    """
    # Ensure output directory exists
    print(f"Output file: {output_path.absolute()}")

    # LaTeX template
    latex_template = r"""\documentclass{{article}}
\usepackage{{fontspec}}
\usepackage{{graphicx}}
\usepackage{{multicol}}
\usepackage{{geometry}}
\usepackage[french,english]{{babel}}
\usepackage{{microtype}}
\usepackage{{xcolor}}
\usepackage{{framed}}
\usepackage{{lscape}}
\usepackage{{hyperref}}
\usepackage{{adjustbox}}
\usepackage{{parskip}}

\geometry{{a4paper, landscape, margin=1cm}}
\setmainfont{{Baskervald ADF Std}}

\setlength{{\columnseprule}}{{0.4pt}}
\setlength{{\columnsep}}{{2em}}

% Consistent paragraph spacing
\setlength{{\parskip}}{{0.8em}}
\setlength{{\parindent}}{{0pt}}

% Consistent list spacing
\setlength{{\itemsep}}{{0.4em}}
\setlength{{\parsep}}{{0.4em}}

\begin{{document}}
{content}
\end{{document}}
"""

    # Process each page
    content = []
    for image_path, french_md_path, english_md_path in pages:
        # Read text files directly
        with open(french_md_path, 'r', encoding='utf-8') as f:
            french_text = f.read()
        with open(english_md_path, 'r', encoding='utf-8') as f:
            english_text = f.read()

        # Create relative paths for images
        image_rel_path = os.path.relpath(image_path, output_path.parent)
        print(f"Image path: {image_path.absolute()}")
        print(f"Relative image path: {image_rel_path}")

        # Create page LaTeX
        page_tex = f"""
\\begin{{multicols}}{{3}}
\\begin{{adjustbox}}{{max width=\\columnwidth, max height=\\textheight, keepaspectratio, center}}
\\includegraphics{{{image_rel_path}}}
\\end{{adjustbox}}

\\columnbreak

\\selectlanguage{{french}}
\\raggedright
\\small
{french_text}

\\columnbreak

\\selectlanguage{{english}}
\\raggedright
\\small
{english_text}
\\end{{multicols}}
\\newpage
"""
        content.append(page_tex)

    # Combine all content
    final_tex = latex_template.format(content='\n'.join(content))

    # Write the LaTeX file
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(final_tex)

    print(f"Created LaTeX document with {len(pages)} pages: {output_path}")

    # Compile the LaTeX document
    try:
        # Change to the output directory
        os.chdir(output_path.parent)
        print(f"Current working directory: {os.getcwd()}")

        # First run to generate the PDF
        subprocess.run(['lualatex', '-interaction=nonstopmode', output_path.name],
                      check=True)
        # Second run to resolve references
        subprocess.run(['lualatex', '-interaction=nonstopmode', output_path.name],
                      check=True)
        #print(f"Compiled LaTeX document to PDF: {output_path.with_suffix('.pdf')}")
    except subprocess.CalledProcessError as e:
        pass
        #print(f"Error compiling LaTeX document: {e}")
        #print("The .tex file was created but compilation failed. You can try compiling it manually.")
    finally:
        # Change back to the original directory
        os.chdir(Path.cwd())
