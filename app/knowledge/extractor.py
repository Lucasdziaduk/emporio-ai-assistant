"""PDF extraction that preserves policy section and physical page provenance."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable

from app.domain.errors import SourceUnavailableError
from app.knowledge.tokenizer import normalize_text


@dataclass(frozen=True)
class PolicyParagraph:
    """A logical paragraph with the physical PDF page where it begins."""

    page: int
    text: str


@dataclass(frozen=True)
class ExtractedPolicySection:
    """One numbered policy section before chunking."""

    section: str
    title: str
    page: int
    paragraphs: tuple[PolicyParagraph, ...] = field(default_factory=tuple)

    @property
    def content(self) -> str:
        return "\n\n".join(item.text for item in self.paragraphs)


class PolicyPdfExtractor:
    """Extract numbered sections from the store's policy PDF."""

    HEADING_PATTERN = re.compile(r"^\s*(\d+(?:\.\d+)?)(?:\.)?\s+(.+?)\s*$")
    PAGE_FOOTER_PATTERN = re.compile(r"^pagina\s+\d+$", re.IGNORECASE)
    HEADER_PREFIXES = (
        "emporio da musica manual de politicas",
        "empório da música manual de políticas",
    )

    def extract(self, pdf_path: str | Path) -> list[ExtractedPolicySection]:
        path = Path(pdf_path)
        if not path.is_file():
            raise SourceUnavailableError()

        try:
            import pymupdf as fitz
            document = fitz.open(path)
        except Exception as exc:  # PyMuPDF provides several PDF-specific exception types.
            raise SourceUnavailableError() from exc

        try:
            toc = self._read_toc(document)
            known_headings = {
                (entry[0], normalize_text(entry[1])): entry[1]
                for entry in toc
            }
            sections: list[dict] = [{
                "section": "cover",
                "title": "Capa e dados gerais",
                "page": 1,
                "paragraphs": [],
            }]
            current = sections[0]
            paragraph_lines: list[str] = []
            paragraph_page = 1
            pending_bullet = False

            def flush_paragraph() -> None:
                nonlocal paragraph_lines
                text = " ".join(part.strip() for part in paragraph_lines if part.strip()).strip()
                if text:
                    current["paragraphs"].append(
                        PolicyParagraph(page=paragraph_page, text=text)
                    )
                paragraph_lines = []

            for page_number, page in enumerate(document, start=1):
                page_text = page.get_text("text", sort=True)
                for raw_line in page_text.splitlines():
                    line = raw_line.replace("\u200b", "").replace("\ufeff", "").strip()
                    if not line:
                        flush_paragraph()
                        pending_bullet = False
                        continue

                    normalized_line = normalize_text(line)
                    if normalized_line.startswith(self.HEADER_PREFIXES):
                        continue
                    if self.PAGE_FOOTER_PATTERN.fullmatch(normalized_line):
                        continue

                    heading = self._match_heading(line, known_headings)
                    if heading is not None:
                        flush_paragraph()
                        pending_bullet = False
                        section_id, title = heading
                        current = {
                            "section": section_id,
                            "title": title,
                            "page": page_number,
                            "paragraphs": [],
                        }
                        sections.append(current)
                        continue

                    bullet = self._is_bullet_line(line)
                    if bullet:
                        flush_paragraph()
                        pending_bullet = True
                        bullet_text = self._remove_bullet(line)
                        if bullet_text:
                            paragraph_page = page_number
                            paragraph_lines = [f"• {bullet_text}"]
                            pending_bullet = False
                        continue

                    if pending_bullet:
                        paragraph_page = page_number
                        paragraph_lines = [f"• {line}"]
                        pending_bullet = False
                        continue

                    # Numbered process steps are paragraph boundaries, not policy headings.
                    if re.match(r"^\d+\.\s+", line) and paragraph_lines:
                        flush_paragraph()

                    if not paragraph_lines:
                        paragraph_page = page_number
                    paragraph_lines.append(line)

            flush_paragraph()
            output = [
                ExtractedPolicySection(
                    section=item["section"],
                    title=item["title"],
                    page=(item["paragraphs"][0].page if item["paragraphs"] else item["page"]),
                    paragraphs=tuple(item["paragraphs"]),
                )
                for item in sections
                if item["paragraphs"]
            ]
            if not output or not any(item.section != "cover" for item in output):
                raise SourceUnavailableError()
            return output
        finally:
            document.close()

    @classmethod
    def _read_toc(cls, document) -> list[tuple[str, str]]:
        """Use the PDF outline as the heading authority when available."""
        entries: list[tuple[str, str]] = []
        for item in document.get_toc() or []:
            if len(item) < 2:
                continue
            title = str(item[1]).strip()
            match = cls.HEADING_PATTERN.match(title)
            if match:
                entries.append((match.group(1), title))
        return entries

    @classmethod
    def _match_heading(
        cls,
        line: str,
        known_headings: dict[tuple[str, str], str],
    ) -> tuple[str, str] | None:
        match = cls.HEADING_PATTERN.match(line)
        if not match:
            return None
        section_id, heading_title = match.group(1), match.group(2).strip()
        normalized = normalize_text(heading_title)
        expected_title = known_headings.get((section_id, normalize_text(f"{section_id}. {heading_title}")))
        if expected_title is None:
            # Match against the title text without requiring the outline's exact punctuation.
            for (known_id, _), title in known_headings.items():
                if known_id != section_id:
                    continue
                known_match = cls.HEADING_PATTERN.match(title)
                if known_match and normalize_text(known_match.group(2)) == normalized:
                    expected_title = title
                    break
        if expected_title is not None:
            return section_id, heading_title
        # If the PDF has no useful outline, accept numeric headings as a fallback.
        if not known_headings:
            return section_id, heading_title
        return None

    @staticmethod
    def _is_bullet_line(line: str) -> bool:
        return line.startswith(("•", "▪", "◦", "‣", "●"))

    @staticmethod
    def _remove_bullet(line: str) -> str:
        return re.sub(r"^[•▪◦‣●\s]+", "", line).strip()
