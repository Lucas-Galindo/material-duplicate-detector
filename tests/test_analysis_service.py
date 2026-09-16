"""Testes da orquestracao do pipeline em thread (Sprint 8)."""

from __future__ import annotations

import queue
import threading

import pandas as pd
import pytest

from app.services.analysis_service import run_analysis, start_analysis_thread


@pytest.fixture
def sample_xlsx(tmp_path):
    path = tmp_path / "materiais.xlsx"
    df = pd.DataFrame(
        {
            "Codigo": ["1", "2", "3", "4"],
            "Texto Dados Basicos": [
                "PARAFUSO 20 CM X 1/2 MM",
                "PARAFUSO 20CMX1/2MM",
                "PARAFUSO M10",
                "PARAFUSO M12",
            ],
        }
    )
    df.to_excel(path, sheet_name="Data", index=False, engine="openpyxl")
    return path


def test_run_analysis_reports_progress_and_done(sample_xlsx):
    q: "queue.Queue" = queue.Queue()
    run_analysis(str(sample_xlsx), "Data", "Codigo", "Texto Dados Basicos", q)

    messages = []
    while not q.empty():
        messages.append(q.get())

    assert any(m["type"] == "progress" for m in messages)
    done_messages = [m for m in messages if m["type"] == "done"]
    assert len(done_messages) == 1

    stats = done_messages[0]["stats"]
    results = done_messages[0]["results"]
    assert stats.total_materials == 4
    assert stats.total_candidates == len(results)
    assert any(r.classification == "DUPLICADO_CONFIRMADO" for r in results)
    assert any(r.classification == "SEMELHANTE_DIFERENTE" for r in results)


def test_run_analysis_reports_error_for_missing_column(sample_xlsx):
    q: "queue.Queue" = queue.Queue()
    run_analysis(str(sample_xlsx), "Data", "Coluna Inexistente", "Texto Dados Basicos", q)

    messages = []
    while not q.empty():
        messages.append(q.get())

    assert any(m["type"] == "error" for m in messages)


def test_start_analysis_thread_runs_in_background(sample_xlsx):
    q: "queue.Queue" = queue.Queue()
    thread = start_analysis_thread(str(sample_xlsx), "Data", "Codigo", "Texto Dados Basicos", q)
    assert isinstance(thread, threading.Thread)
    thread.join(timeout=10)
    assert not thread.is_alive()

    messages = []
    while not q.empty():
        messages.append(q.get())
    assert any(m["type"] == "done" for m in messages)


def test_run_analysis_respects_cancel_event(sample_xlsx):
    q: "queue.Queue" = queue.Queue()
    cancel_event = threading.Event()
    cancel_event.set()
    run_analysis(str(sample_xlsx), "Data", "Codigo", "Texto Dados Basicos", q, cancel_event=cancel_event)

    messages = []
    while not q.empty():
        messages.append(q.get())
    assert messages[0]["type"] == "cancelled"
