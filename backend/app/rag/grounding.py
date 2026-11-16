from dataclasses import dataclass


@dataclass(frozen=True)
class EvidenceResult:
    classification: str
    chunks: tuple[dict, ...]


def classify_evidence(
    chunks: list[dict],
    threshold: float | None,
) -> EvidenceResult:
    if not chunks:
        return EvidenceResult("insufficient", ())
    if threshold is not None and max(
        float(chunk["similarity"]) for chunk in chunks
    ) < threshold:
        return EvidenceResult("insufficient", tuple(chunks))
    return EvidenceResult("sufficient", tuple(chunks))
