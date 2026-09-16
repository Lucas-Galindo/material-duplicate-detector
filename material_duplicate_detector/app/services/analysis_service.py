"""Orquestracao do pipeline de analise em thread separada (Sprint 8).

``run_analysis`` executa importacao -> parsing -> assinaturas -> geracao
de candidatos -> comparacao -> classificacao, publicando progresso em uma
``queue.Queue`` para que a GUI (rodando na thread principal) possa
atualizar a interface sem travar, via polling periodico (``after``).

Mensagens publicadas na fila (sempre dicts com chave ``type``):
  - {"type": "progress", "stage": str, "processed": int, "total": int}
  - {"type": "done", "results": list[ComparisonResult], "stats": AnalysisStats}
  - {"type": "error", "message": str}
"""

from __future__ import annotations

import queue
import threading
import time
from dataclasses import dataclass

from app.core.candidate_generator import generate_candidate_pairs
from app.core.classifier import build_comparison_result
from app.core.comparator import compare
from app.core.signature_builder import build_signature
from app.core.technical_parser import parse_material
from app.models.comparison_result import ComparisonResult
from app.rules.rule_loader import RuleSet, load_rules
from app.services.excel_service import load_materials

_PROGRESS_REPORT_INTERVAL = 100


@dataclass(frozen=True)
class AnalysisStats:
    total_materials: int
    total_candidates: int
    duplicados_confirmados: int
    provaveis_duplicados: int
    semelhantes_diferentes: int
    import_seconds: float
    processing_seconds: float


def run_analysis(
    file_path: str,
    sheet_name: str,
    code_column: str,
    analysis_column: str,
    progress_queue: "queue.Queue",
    rules: RuleSet | None = None,
    cancel_event: threading.Event | None = None,
) -> None:
    """Executa o pipeline completo. Deve rodar em uma thread de trabalho.

    Qualquer excecao e capturada e publicada como mensagem de erro na
    fila, para que a GUI possa exibi-la sem travar.
    """
    try:
        start_import = time.perf_counter()
        materials = load_materials(file_path, sheet_name, code_column, analysis_column)
        import_seconds = time.perf_counter() - start_import
        total_materials = len(materials)

        rules = rules or load_rules()

        start_processing = time.perf_counter()

        parsed_materials = []
        for index, material in enumerate(materials):
            if cancel_event is not None and cancel_event.is_set():
                progress_queue.put({"type": "cancelled"})
                return
            parsed_materials.append(parse_material(material, rules))
            if index % _PROGRESS_REPORT_INTERVAL == 0 or index == total_materials - 1:
                progress_queue.put(
                    {
                        "type": "progress",
                        "stage": "ANALISANDO_TEXTOS",
                        "processed": index + 1,
                        "total": total_materials,
                    }
                )

        signatures = [build_signature(p) for p in parsed_materials]
        candidate_pairs = generate_candidate_pairs(parsed_materials, signatures)
        total_candidates = len(candidate_pairs)

        results: list[ComparisonResult] = []
        counts = {
            "DUPLICADO_CONFIRMADO": 0,
            "PROVAVEL_DUPLICADO": 0,
            "SEMELHANTE_DIFERENTE": 0,
        }
        for index, (i, j) in enumerate(candidate_pairs):
            if cancel_event is not None and cancel_event.is_set():
                progress_queue.put({"type": "cancelled"})
                return
            outcome = compare(parsed_materials[i], parsed_materials[j], rules)
            result = build_comparison_result(outcome)
            counts[result.classification] += 1
            results.append(result)
            if index % _PROGRESS_REPORT_INTERVAL == 0 or index == total_candidates - 1:
                progress_queue.put(
                    {
                        "type": "progress",
                        "stage": "COMPARANDO_CANDIDATOS",
                        "processed": index + 1,
                        "total": max(total_candidates, 1),
                    }
                )

        processing_seconds = time.perf_counter() - start_processing

        stats = AnalysisStats(
            total_materials=total_materials,
            total_candidates=total_candidates,
            duplicados_confirmados=counts["DUPLICADO_CONFIRMADO"],
            provaveis_duplicados=counts["PROVAVEL_DUPLICADO"],
            semelhantes_diferentes=counts["SEMELHANTE_DIFERENTE"],
            import_seconds=import_seconds,
            processing_seconds=processing_seconds,
        )
        progress_queue.put({"type": "done", "results": results, "stats": stats})
    except Exception as exc:  # nunca deixar a thread morrer silenciosamente
        progress_queue.put({"type": "error", "message": str(exc)})


def start_analysis_thread(
    file_path: str,
    sheet_name: str,
    code_column: str,
    analysis_column: str,
    progress_queue: "queue.Queue",
    cancel_event: threading.Event | None = None,
) -> threading.Thread:
    """Cria e inicia a thread de analise, retornando-a ja em execucao."""
    thread = threading.Thread(
        target=run_analysis,
        args=(file_path, sheet_name, code_column, analysis_column, progress_queue),
        kwargs={"cancel_event": cancel_event},
        daemon=True,
    )
    thread.start()
    return thread
