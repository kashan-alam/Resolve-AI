import math

import pytest

from backend.app.ai.embeddings import EmbeddingError, normalize_embedding


def test_embedding_is_l2_normalized() -> None:
    normalized = normalize_embedding([3.0, 4.0], 2)

    assert math.isclose(math.sqrt(sum(value * value for value in normalized)), 1.0)
    assert normalized == pytest.approx([0.6, 0.8])


@pytest.mark.parametrize(
    "values, dimension",
    [([1.0], 2), ([float("nan"), 1.0], 2), ([0.0, 0.0], 2)],
)
def test_invalid_embedding_is_rejected(values: list[float], dimension: int) -> None:
    with pytest.raises(EmbeddingError):
        normalize_embedding(values, dimension)
