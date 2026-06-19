"""Build the chunk vector index from ``data/chunks/``.

Usage::

    python -m src.rag.build_index
"""

from src.rag.index import VectorIndex


def main() -> None:
    print("Building vector index from data/chunks/...")
    index = VectorIndex.build()
    print(f"Indexed {len(index)} chunks -> data/embeddings/index.npz")


if __name__ == "__main__":
    main()
