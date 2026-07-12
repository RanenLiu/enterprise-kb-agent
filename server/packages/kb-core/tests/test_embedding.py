"""Tests for embedding — mocked SentenceTransformer."""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import numpy as np
import pytest

from kb_core.indexing.service import embed_texts


@patch("kb_core.indexing.service._get_embedding_model")
def test_embed_texts(mock_get_model):
    mock_model = MagicMock()
    mock_model.encode.return_value = np.array([[0.1, 0.2, 0.3], [0.4, 0.5, 0.6]])
    mock_get_model.return_value = mock_model

    result = embed_texts(["hello world", "test text"])
    assert len(result) == 2
    assert len(result[0]) == 3
    mock_model.encode.assert_called_once()


@patch("kb_core.indexing.service._get_embedding_model")
def test_embed_normalized(mock_get_model):
    mock_model = MagicMock()
    mock_model.encode.return_value = np.array([[0.1, 0.2, 0.3]])
    mock_get_model.return_value = mock_model

    result = embed_texts(["single"])
    assert len(result) == 1
    # Should have called with normalize_embeddings=True
    mock_model.encode.assert_called_with(["single"], normalize_embeddings=True)
