"""
parse_notebook.py — Programmatic Project Extractor
Usage: python parse_notebook.py notebook/pipeline.ipynb
Extracts all %%writefile cells into their respective file paths.
"""
import os, re, sys, json

def extract_files_from_notebook(nb_path):
    if not os.path.exists(nb_path):
        print(f"Error: Notebook not found at {nb_path}", file=sys.stderr)
        sys.exit(1)

    with open(nb_path, 'r', encoding='utf-8') as f:
        try:
            notebook = json.load(f)
        except Exception as e:
            print(f"Error parsing JSON: {e}", file=sys.stderr)
            sys.exit(1)

    files_created = []
    cells = notebook.get('cells', [])

    for idx, cell in enumerate(cells):
        if cell.get('cell_type') != 'code':
            continue
        source = cell.get('source', [])
        if not source:
            continue
        first_line = source[0].strip()
        match = re.match(r'^%%writefile\s+(.+)', first_line)
        if match:
            filepath = match.group(1).strip().strip('"\'')
            content  = "".join(source[1:])
            if os.path.dirname(filepath):
                os.makedirs(os.path.dirname(filepath), exist_ok=True)
            with open(filepath, 'w', encoding='utf-8') as out:
                out.write(content)
            files_created.append(filepath)
            print(f"  [idx {idx:02d}] ✅ Extracted → {filepath}")

    print(f"\n{'='*50}")
    print(f" Extraction Complete!")
    print(f" Notebook  : {nb_path}")
    print(f" Files     : {len(files_created)}")
    print(f"{'='*50}")
    for f in files_created:
        print(f"  • {f}")

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: python parse_notebook.py path/to/notebook.ipynb")
    else:
        extract_files_from_notebook(sys.argv[1])

