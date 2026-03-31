import argparse
import json
import os
import re
import shutil
from pathlib import Path

import git
from tqdm import tqdm


def extract_json_from_markdown(md_content: str, block_name: str) -> dict:
    """Extracts a JSON code block from a markdown string."""
    pattern = f"```json\n({{\n  \"{block_name}\": {{\n[\\s\\S]*?}}}}\n)```"
    match = re.search(pattern, md_content)
    if not match:
        raise ValueError(f"Could not find JSON block '{block_name}' in markdown file.")
    return json.loads(match.group(1))


def clean_csharp(code: str) -> str:
    """Basic cleaning for C# code."""
    code = re.sub(r"^\s*//.*$", "", code, flags=re.MULTILINE)  # Remove single-line comments
    code = code.replace("\r\n", "\n")  # Normalize newlines
    # A more advanced cleaner would use Roslyn or similar for using removal, etc.
    return code


def clean_shader(code: str) -> str:
    """Basic cleaning for shader code."""
    code = re.sub(r"^\s*//.*$", "", code, flags=re.MULTILINE)  # Remove single-line comments
    code = code.replace("\r\n", "\n")  # Normalize newlines
    return code


def main(args):
    dataset_path = Path(args.dataset_path)
    resources_path = Path(args.resources_path)

    print(f"Starting dataset preparation in: {dataset_path}")

    # 1. Create directory structure
    raw_path = dataset_path / "raw"
    cleaned_path = dataset_path / "cleaned"
    metadata_path = dataset_path / "metadata"
    
    # Clean slate
    if dataset_path.exists():
        shutil.rmtree(dataset_path)

    for p in [raw_path, cleaned_path, metadata_path]:
        p.mkdir(parents=True, exist_ok=True)

    # 2. Load and save resources.json
    print(f"Loading resources from {resources_path}...")
    md_content = resources_path.read_text(encoding="utf-8")
    resources_data = extract_json_from_markdown(md_content, "UnityDataset")
    
    with open(metadata_path / "resources.json", "w", encoding="utf-8") as f:
        json.dump(resources_data, f, indent=2)

    # 3. Download repositories
    for resource in tqdm(resources_data["UnityDataset"]["resources"], desc="Downloading Repos"):
        repo_url = resource["link"]
        repo_id = resource["id"]
        target_path = raw_path / repo_id
        print(f"Cloning {repo_url} to {target_path}...")
        try:
            git.Repo.clone_from(repo_url, target_path, depth=1)
        except Exception as e:
            print(f"Failed to clone {repo_url}: {e}")
            continue

    # 4. Process files: clean and create index
    print("Processing files: cleaning and creating index...")
    files_index = {"files": []}
    file_id_counter = 1

    file_extensions = {
        ".cs": ("csharp", cleaned_path / "csharp", clean_csharp),
        ".shader": ("shaderlab", cleaned_path / "shaderlab", clean_shader),
        ".hlsl": ("hlsl_glsl", cleaned_path / "hlsl_glsl", clean_shader),
        ".glsl": ("hlsl_glsl", cleaned_path / "hlsl_glsl", clean_shader),
        ".cginc": ("hlsl_glsl", cleaned_path / "hlsl_glsl", clean_shader),
    }

    for lang_path in file_extensions.values():
        lang_path[1].mkdir(exist_ok=True)

    for dirpath, _, filenames in tqdm(os.walk(raw_path), desc="Cleaning Files"):
        for filename in filenames:
            ext = Path(filename).suffix.lower()
            if ext in file_extensions:
                lang, clean_dir, clean_func = file_extensions[ext]
                
                raw_file_path = Path(dirpath) / filename
                
                try:
                    content = raw_file_path.read_text(encoding="utf-8")
                except (UnicodeDecodeError, OSError):
                    print(f"Skipping file with encoding error: {raw_file_path}")
                    continue

                cleaned_content = clean_func(content)
                
                # Avoid empty files
                if not cleaned_content.strip():
                    continue

                file_id = f"file_{file_id_counter:05d}"
                
                # Create a unique name for the cleaned file
                repo_id = Path(dirpath).relative_to(raw_path).parts[0]
                unique_filename = f"{repo_id}_{filename}"
                clean_file_path = clean_dir / unique_filename
                
                clean_file_path.write_text(cleaned_content, encoding="utf-8")

                files_index["files"].append({
                    "id": file_id,
                    "resource_id": repo_id,
                    "relative_path_raw": str(raw_file_path.relative_to(dataset_path.parent)),
                    "relative_path_clean": str(clean_file_path.relative_to(dataset_path)),
                    "language": lang,
                    "ml_tags": [], # Placeholder for more advanced tagging
                    "embedding_vector_path": f"embeddings/{lang}/{file_id}.npy"
                })
                file_id_counter += 1

    # 5. Save file index
    with open(metadata_path / "files_index.json", "w", encoding="utf-8") as f:
        json.dump(files_index, f, indent=2)

    print("\nDataset preparation complete!")
    print(f"Total files processed: {len(files_index['files'])}")
    print(f"Dataset ready at: {dataset_path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Prepare Unity code dataset for training.")
    parser.add_argument("--dataset-path", type=str, required=True, help="Path to the root of the dataset directory.")
    parser.add_argument("--resources-path", type=str, required=True, help="Path to the markdown file containing the resources.json block.")
    args = parser.parse_args()
    main(args)
