"""Testes de integracao ponta a ponta com planilhas sinteticas (Sprint 10).

Cobrem o fluxo completo: Excel -> importacao -> parsing -> assinaturas ->
geracao de candidatos -> comparacao -> classificacao -> exportacao, com
planilhas pequenas (casos de exatidao) e de maior volume (desempenho).
"""

from __future__ import annotations

import queue
import time

import pandas as pd
import pytest

from app.services.analysis_service import run_analysis
from app.services.export_service import export_results_to_excel


def _write_xlsx(tmp_path, rows: list[dict], filename: str = "materiais.xlsx"):
    path = tmp_path / filename
    df = pd.DataFrame(rows)
    df.to_excel(path, sheet_name="Data", index=False, engine="openpyxl")
    return path


def test_end_to_end_small_spreadsheet_with_known_cases(tmp_path):
    """Planilha pequena reunindo todos os casos obrigatorios do escopo."""
    rows = [
        {"Codigo": "1", "Texto Dados Basicos": "PARAFUSO 20 CM X 1/2 MM"},
        {"Codigo": "2", "Texto Dados Basicos": "PARAFUSO 20CMX1/2MM"},  # duplicado de 1
        {"Codigo": "3", "Texto Dados Basicos": 'CANO 1/2"'},
        {"Codigo": "4", "Texto Dados Basicos": "CANO 1/2"},  # diferenca tecnica (simbolo)
        {"Codigo": "5", "Texto Dados Basicos": "PARAFUSO M10"},
        {"Codigo": "6", "Texto Dados Basicos": "PARAFUSO M12"},  # diferenca tecnica (codigo)
        {"Codigo": "7", "Texto Dados Basicos": "SUPORTE DIANT"},
        {"Codigo": "8", "Texto Dados Basicos": "SUPORTE DIANTEIRO"},  # equivalente
        {"Codigo": "9", "Texto Dados Basicos": "SUPORTE TRASEIRO"},  # incompativel com 7/8
        {"Codigo": "10", "Texto Dados Basicos": "CONECTOR MASCULINO"},
        {"Codigo": "11", "Texto Dados Basicos": "CONECTOR FEMININO"},
        {"Codigo": "12", "Texto Dados Basicos": "TAMPA AZUL"},
        {"Codigo": "13", "Texto Dados Basicos": "TAMPA PRETO"},
    ]
    xlsx_path = _write_xlsx(tmp_path, rows)

    q: "queue.Queue" = queue.Queue()
    run_analysis(str(xlsx_path), "Data", "Codigo", "Texto Dados Basicos", q)

    done = [m for m in _drain(q) if m["type"] == "done"]
    assert len(done) == 1
    results = done[0]["results"]

    by_pair = {(r.code_a, r.code_b): r for r in results}

    assert by_pair[("1", "2")].classification == "DUPLICADO_CONFIRMADO"
    assert by_pair[("3", "4")].classification == "SEMELHANTE_DIFERENTE"
    assert by_pair[("5", "6")].classification == "SEMELHANTE_DIFERENTE"
    assert by_pair[("7", "8")].classification == "DUPLICADO_CONFIRMADO"
    assert by_pair[("7", "9")].classification == "SEMELHANTE_DIFERENTE"
    assert by_pair[("8", "9")].classification == "SEMELHANTE_DIFERENTE"
    assert by_pair[("10", "11")].classification == "SEMELHANTE_DIFERENTE"
    assert by_pair[("12", "13")].classification == "SEMELHANTE_DIFERENTE"

    # Exportacao tambem deve funcionar sobre o resultado real.
    export_path = tmp_path / "resultado_exportado.xlsx"
    export_results_to_excel(results, export_path)
    assert export_path.exists()


@pytest.mark.parametrize("total_materials", [5000])
def test_end_to_end_volume_performance(tmp_path, total_materials):
    """Planilha sintetica de volume (~5.000 registros) com familias de
    materiais duplicados/variantes, medindo tempo total e volume de
    comparacoes geradas (deve ficar bem abaixo de C(n,2))."""
    rows: list[dict] = []
    families = total_materials // 5
    code = 0
    for family in range(families):
        base = f"ITEMFAM{family:04d} MODELO{family:04d}"
        variants = [
            f"{base} 20 CM X 1/2 MM",
            f"{base} 20CMX1/2MM",  # duplicado de formatacao do anterior
            f"{base} M10",
            f"{base} M12",  # tecnicamente diferente do anterior
            f"{base} DIANTEIRO",
        ]
        for text in variants:
            code += 1
            rows.append({"Codigo": str(code), "Texto Dados Basicos": text})

    xlsx_path = _write_xlsx(tmp_path, rows, filename="volume.xlsx")

    q: "queue.Queue" = queue.Queue()
    start = time.perf_counter()
    run_analysis(str(xlsx_path), "Data", "Codigo", "Texto Dados Basicos", q)
    elapsed = time.perf_counter() - start

    messages = _drain(q)
    done = [m for m in messages if m["type"] == "done"]
    assert len(done) == 1
    stats = done[0]["stats"]

    full_cartesian = total_materials * (total_materials - 1) // 2
    assert stats.total_materials == len(rows)
    assert stats.total_candidates < full_cartesian * 0.05
    assert stats.duplicados_confirmados > 0
    assert stats.semelhantes_diferentes > 0

    # "Tempo razoavel em computador comum": generoso para nao ser flaky
    # em maquinas de CI mais lentas, mas suficiente para pegar regressao
    # grave de desempenho (ex.: volta a O(n^2)).
    assert elapsed < 60.0

    print(
        f"\n[Sprint 10] {total_materials} materiais | "
        f"import={stats.import_seconds:.3f}s processamento={stats.processing_seconds:.3f}s | "
        f"candidatos={stats.total_candidates} "
        f"(cartesiano completo={full_cartesian}) | "
        f"confirmados={stats.duplicados_confirmados} "
        f"provaveis={stats.provaveis_duplicados} "
        f"diferentes={stats.semelhantes_diferentes}"
    )


def _drain(q: "queue.Queue") -> list[dict]:
    messages = []
    while not q.empty():
        messages.append(q.get())
    return messages
