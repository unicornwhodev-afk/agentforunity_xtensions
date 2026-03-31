import argparse
import json
from pathlib import Path

import numpy as np
import torch
from sentence_transformers import SentenceTransformer
from tqdm import tqdm


def main(args):
    dataset_path = Path(args.dataset_path)
    metadata_path = dataset_path / "metadata"
    files_index_path = metadata_path / "files_index.json"
    embeddings_path = dataset_path / "embeddings"

    print("Loading file index...")
    with open(files_index_path, "r", encoding="utf-8") as f:
        files_index = json.load(f)

    # Ensure embedding directories exist
    (embeddings_path / "csharp").mkdir(parents=True, exist_ok=True)
    (embeddings_path / "shaderlab").mkdir(parents=True, exist_ok=True)
    (embeddings_path / "hlsl_glsl").mkdir(parents=True, exist_ok=True)

    print("Loading embedding model (BGE-M3)... This may take a moment.")
    device = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"Using device: {device}")
    
    # BGE-M3 is a great multilingual model for code and text
    model = SentenceTransformer("BAAI/bge-m3", device=device)

    files_to_embed = files_index["files"]
    
    # Prepare batches of content and paths
    contents = []
    output_paths = []
    for file_info in files_to_embed:
        clean_path = dataset_path / file_info["relative_path_clean"]
        try:
            contents.append(clean_path.read_text(encoding="utf-8"))
            output_paths.append(dataset_path / file_info["embedding_vector_path"])
        except FileNotFoundError:
            print(f"Warning: File not found, skipping: {clean_path}")

    print(f"Generating embeddings for {len(contents)} files...")
    embeddings = model.encode(contents, batch_size=args.batch_size, show_progress_bar=True, normalize_embeddings=True)

    print("Saving embedding vectors...")
    for emb, out_path in tqdm(zip(embeddings, output_paths), total=len(output_paths), desc="Saving Embeddings"):
        out_path.parent.mkdir(parents=True, exist_ok=True)
        np.save(out_path, emb)

    print("\nEmbedding generation complete!")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate embeddings for the prepared dataset.")
    parser.add_argument("--dataset-path", type=str, required=True, help="Path to the root of the dataset directory.")
    parser.add_argument("--batch-size", type=int, default=32, help="Batch size for the embedding model.")
    args = parser.parse_args()
    main(args)
