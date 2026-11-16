import re
from dataclasses import dataclass


TOKEN_PATTERN = re.compile(r"\w+|[^\w\s]", re.UNICODE)


def tokenize(text: str) -> list[str]:
    return TOKEN_PATTERN.findall(text)


def detokenize(tokens: list[str]) -> str:
    text = ""
    for token in tokens:
        if text and token.isalnum() and text[-1].isalnum():
            text += " "
        elif text and token.isalnum() and text[-1] in ".,!?;:":
            text += " "
        text += token
    return text.strip()


@dataclass(frozen=True)
class TextChunk:
    index: int
    text: str
    token_count: int


def chunk_text(
    text: str,
    max_tokens: int = 1800,
    overlap_tokens: int = 150,
) -> list[TextChunk]:
    if max_tokens <= 0:
        raise ValueError("max_tokens must be positive.")
    if overlap_tokens < 0 or overlap_tokens >= max_tokens:
        raise ValueError("overlap_tokens must be less than max_tokens.")

    tokens = tokenize(text)
    chunks: list[TextChunk] = []
    start = 0
    index = 0
    while start < len(tokens):
        end = min(start + max_tokens, len(tokens))
        chunk_tokens = tokens[start:end]
        chunks.append(
            TextChunk(index, detokenize(chunk_tokens), len(chunk_tokens))
        )
        if end == len(tokens):
            break
        start = end - overlap_tokens
        index += 1
    return chunks
