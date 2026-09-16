"""Modelo bruto do material lido diretamente da planilha (Sprint 2)."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class Material:
    """Representa uma linha da planilha, sem nenhuma transformacao.

    O texto original (``analysis_text``) nunca deve ser alterado em
    nenhum ponto do pipeline; ele existe para auditoria e para ser
    exibido ao usuario final.

    ``short_description`` (coluna "Descricao Curta"/"Descrição Curta",
    quando presente na planilha) e puramente informativa: existe so
    para dar contexto ao usuario na revisao/exportacao. Nunca e usada
    em normalizacao, tokenizacao, assinaturas, geracao de candidatos,
    comparacao ou classificacao — o calculo de similaridade/confianca
    considera exclusivamente ``analysis_text`` (o campo de "Dados
    Basicos"). Ver ``app.services.excel_service.load_materials``.
    """

    row_index: int
    code: str
    analysis_text: str
    short_description: str = ""
    raw_fields: dict[str, str] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.row_index < 0:
            raise ValueError("row_index nao pode ser negativo")
