from app.domain.schemas import PolicyEvidence
from app.knowledge.chunker import PolicyChunker
from app.knowledge.extractor import ExtractedPolicySection, PolicyParagraph
from app.knowledge.tokenizer import tokenize


def test_chunker_keeps_sections_separate_and_preserves_page():
    sections = [
        ExtractedPolicySection(
            section="4.1",
            title="Arrependimento",
            page=4,
            paragraphs=(
                PolicyParagraph(page=4, text="Primeiro parágrafo sobre devolução online."),
                PolicyParagraph(page=4, text="Segundo parágrafo sobre reembolso."),
            ),
        ),
        ExtractedPolicySection(
            section="5.1",
            title="Frete",
            page=5,
            paragraphs=(PolicyParagraph(page=5, text="Frete regional e prazo de entrega."),),
        ),
    ]

    chunks = PolicyChunker(max_tokens=40).chunk_sections(sections)

    assert {chunk.section for chunk in chunks} == {"4.1", "5.1"}
    assert all(chunk.page in {4, 5} for chunk in chunks)


def test_chunker_splits_large_paragraphs_to_max_tokens():
    text = " ".join(["instrumento musical possui garantia legal de noventa dias." ] * 80)
    section = ExtractedPolicySection(
        section="8.1",
        title="Garantia Legal",
        page=7,
        paragraphs=(PolicyParagraph(page=7, text=text),),
    )

    chunks = PolicyChunker(max_tokens=35).chunk_sections([section])

    assert len(chunks) > 1
    assert all(len(tokenize(chunk.content)) <= 35 for chunk in chunks)
    assert all(chunk.section == "8.1" for chunk in chunks)


def test_chunker_rechunks_existing_policy_evidence():
    evidence = [PolicyEvidence(
        section="4.1", page=4, title="Devolução",
        content="Regra um para devolução.\n\nRegra dois para reembolso.",
    )]
    chunks = PolicyChunker(max_tokens=35).chunk_evidence(evidence)
    assert chunks
    assert all(chunk.section == "4.1" for chunk in chunks)
