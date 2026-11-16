from backend.app.rag.chunker import chunk_text, tokenize


def test_chunker_enforces_token_limit_and_overlap() -> None:
    source = " ".join(f"policy-word-{index}" for index in range(120))

    chunks = chunk_text(source, max_tokens=40, overlap_tokens=5)

    assert len(chunks) > 1
    assert all(chunk.token_count <= 40 for chunk in chunks)
    assert chunks[0].index == 0
    assert chunks[1].index == 1
    assert set(tokenize(chunks[0].text)[-5:]).intersection(
        tokenize(chunks[1].text)[:5]
    )
