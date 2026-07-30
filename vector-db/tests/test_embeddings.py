import numpy as np
import pytest

from vector_db.embeddings import EmbeddingService


def test_parent_vector_is_normalized_mean() -> None:
    result = EmbeddingService.mean_normalized(
        [
            [1.0, 0.0],
            [0.0, 1.0],
        ]
    )

    assert len(result) == 2
    assert np.linalg.norm(result) == pytest.approx(1.0)
    assert result[0] == pytest.approx(result[1])


def test_parent_vector_rejects_empty_input() -> None:
    with pytest.raises(ValueError, match="without children"):
        EmbeddingService.mean_normalized([])
