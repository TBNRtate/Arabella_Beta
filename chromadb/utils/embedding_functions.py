class DefaultEmbeddingFunction:
    def __call__(self, input_texts):
        return [[0.0] * 3 for _ in input_texts]
