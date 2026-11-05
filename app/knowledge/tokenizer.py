"""Portuguese text normalization, tokenization, and query expansion."""

from __future__ import annotations

import re
import unicodedata

STOPWORDS = frozenset({
    "a", "ao", "aos", "as", "ate", "com", "como", "da", "das", "de",
    "dela", "dele", "do", "dos", "e", "ela", "ele", "em", "essa",
    "esse", "esta", "este", "eu", "foi", "for", "foram", "ha", "isso",
    "isto", "ja", "me", "meu", "minha", "na", "nas", "nem", "no",
    "nos", "o", "os", "ou", "para", "pela", "pelas", "pelo", "pelos",
    "por", "qual", "quando", "que", "quem", "se", "sem", "ser", "sobre",
    "sua", "suas", "seu", "seus", "tambem", "tem", "tenho", "um", "uma",
    "umas", "uns", "voce", "voces", "loja", "cliente",
})

# Small, auditable domain lexicon. It expands customer language without
# pretending to be a general Portuguese stemmer.
SYNONYMS: dict[str, tuple[str, ...]] = {
    "devolver": ("devolucao", "arrependimento", "reembolso", "estorno", "compra", "online"),
    "devolvo": ("devolucao", "arrependimento", "reembolso", "estorno"),
    "devolucao": ("arrependimento", "reembolso", "estorno", "prazo"),
    "arrependi": ("arrependimento", "devolucao", "reembolso", "online"),
    "arrependimento": ("devolucao", "reembolso", "estorno", "online"),
    "dinheiro": ("reembolso", "estorno", "pagamento"),
    "estornar": ("estorno", "reembolso", "devolucao"),
    "estorno": ("reembolso", "devolucao", "pagamento"),
    "trocar": ("troca", "substituicao", "defeito", "preferencia"),
    "troca": ("trocar", "substituicao", "defeito", "preferencia"),
    "quebrou": ("defeito", "garantia", "fabricacao", "troca"),
    "quebrado": ("defeito", "garantia", "reparo"),
    "defeito": ("garantia", "fabricacao", "troca", "reparo"),
    "garantia": ("defeito", "fabricante", "legal", "noventa", "dias"),
    "frete": ("entrega", "envio", "transportadora", "prazo"),
    "entrega": ("frete", "transportadora", "prazo", "rastreamento"),
    "entregar": ("entrega", "frete", "prazo"),
    "rastrear": ("rastreamento", "codigo", "despachado", "entrega"),
    "rastreio": ("rastreamento", "codigo", "transportadora"),
    "parcelar": ("parcelamento", "credito", "parcela", "juros"),
    "parcelamento": ("parcelas", "credito", "juros", "minima"),
    "parcela": ("parcelamento", "credito", "minima", "juros"),
    "pix": ("desconto", "cumulativo", "promocao"),
    "desconto": ("promocao", "promocional", "pix", "preco"),
    "promocao": ("desconto", "oferta", "campanha", "pix"),
    "horario": ("funcionamento", "sabado", "domingo", "feriados"),
    "abre": ("funcionamento", "horario"),
    "fecha": ("funcionamento", "horario", "domingo"),
    "telefone": ("whatsapp", "contato", "numero"),
    "contato": ("telefone", "whatsapp", "email"),
    "email": ("contato", "privacidade", "dados"),
    "acessorio": ("acessorios", "cordas", "palhetas", "cabos", "cases", "pedais"),
    "acessorios": ("instrumentos", "cordas", "palhetas", "cabos", "cases", "pedais"),
    "reclamar": ("reclamacao", "atendimento", "responsavel", "retorno"),
    "vende": ("vendem", "instrumentos", "catalogo", "comercializa"),
    "vendem": ("vende", "instrumentos", "catalogo", "comercializa"),
    "vender": ("venda", "instrumentos", "catalogo", "comercializa"),
    "comercializa": ("comercializacao", "instrumentos", "catalogo", "vende"),
    "cobre": ("desgaste", "danos", "mau", "uso", "modificacoes", "esteticos"),
    "clara": ("duvidas", "consultar", "gerencia", "duvida"),
    "duvida": ("duvidas", "consultar", "gerencia", "clareza"),
    "duvidas": ("duvida", "consultar", "gerencia", "clareza"),
    "reclamacao": ("reclamar", "atendimento", "responsavel", "retorno"),
    "privacidade": ("lgpd", "dados", "exclusao", "consentimento"),
    "excluir": ("exclusao", "dados", "privacidade"),
}


def normalize_text(value: str) -> str:
    """Case-fold and remove accents while preserving readable source text elsewhere."""
    normalized = unicodedata.normalize("NFKD", value.casefold())
    return "".join(char for char in normalized if not unicodedata.combining(char))


def tokenize(value: str) -> list[str]:
    """Return normalized alphanumeric tokens with Portuguese stopwords removed."""
    tokens = re.findall(r"[a-z0-9]+", normalize_text(value))
    return [token for token in tokens if token not in STOPWORDS and len(token) > 1]


def expand_query(value: str) -> list[str]:
    """Expand query terms with a controlled set of store-domain synonyms."""
    base = tokenize(value)
    expanded = list(base)
    for token in base:
        expanded.extend(SYNONYMS.get(token, ()))
    return list(dict.fromkeys(expanded))
