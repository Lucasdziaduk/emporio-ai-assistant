import fitz
import pytest

from app.domain.errors import SourceUnavailableError
from app.knowledge.extractor import PolicyPdfExtractor


def create_sample_policy_pdf(path):
    document = fitz.open()
    page1 = document.new_page()
    page1.insert_text((72, 72), "EMPÓRIO DA MÚSICA")
    page1.insert_text((72, 110), "1. Sobre a Empório da Música")
    page1.insert_text((72, 140), "A loja comercializa instrumentos musicais.")
    page1.insert_text((72, 180), "1.1 Missão")
    page1.insert_text((72, 210), "Democratizar o acesso a instrumentos.")
    page2 = document.new_page()
    page2.insert_text((72, 72), "Empório da Música Manual de Políticas e Procedimentos")
    page2.insert_text((72, 110), "2. Horário de Funcionamento")
    page2.insert_text((72, 140), "Segunda a sexta, das 09:00 às 18:00.")
    page2.insert_text((72, 780), "Página 2")
    document.set_toc([
        [1, "1. Sobre a Empório da Música", 1],
        [2, "1.1 Missão", 1],
        [1, "2. Horário de Funcionamento", 2],
    ])
    document.save(path)
    document.close()


def test_extractor_uses_outline_and_preserves_page_numbers(tmp_path):
    path = tmp_path / "sample_policy.pdf"
    create_sample_policy_pdf(path)

    sections = PolicyPdfExtractor().extract(path)
    indexed = {section.section: section for section in sections}

    assert {"1", "1.1", "2"}.issubset(indexed)
    assert indexed["1"].page == 1
    assert indexed["1.1"].title == "Missão"
    assert indexed["2"].page == 2
    assert "09:00" in indexed["2"].content


def test_extractor_does_not_treat_numbered_process_steps_as_headings(tmp_path):
    path = tmp_path / "sample_policy.pdf"
    document = fitz.open()
    page = document.new_page()
    page.insert_text((72, 72), "7.1 Diretrizes de Atendimento")
    page.insert_text((72, 110), "1. Saudação: cumprimentar o cliente.")
    page.insert_text((72, 140), "2. Consulta: pesquisar o pedido.")
    document.set_toc([[1, "7.1 Diretrizes de Atendimento", 1]])
    document.save(path)
    document.close()

    sections = PolicyPdfExtractor().extract(path)
    assert [section.section for section in sections] == ["7.1"]
    assert "1. Saudação" in sections[-1].content
    assert "2. Consulta" in sections[-1].content


def test_extractor_requires_existing_pdf(tmp_path):
    with pytest.raises(SourceUnavailableError):
        PolicyPdfExtractor().extract(tmp_path / "missing.pdf")
