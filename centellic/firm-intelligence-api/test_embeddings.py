from knowledge import embed_texts


def main() -> None:
    sentence = "Profit per equity partner measures firm profitability."
    vectors, tokens = embed_texts([sentence], input_type="document")
    vector = vectors[0]

    print(f"Sentence: {sentence}")
    print(f"Tokens used: {tokens}")
    print(f"Vector length: {len(vector)}")
    print(f"First 5 dims: {vector[:5]}")


if __name__ == "__main__":
    main()