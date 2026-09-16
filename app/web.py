"""Interface web (Flask) para o Detector de Duplicidade de Materiais.

Camada fina que reaproveita 100% da logica existente em
``app.services`` / ``app.core`` / ``app.rules`` / ``app.models`` -
nenhum desses modulos foi alterado. Esta e apenas uma "casca" HTTP
alternativa a interface Tkinter (``app.gui``), pensada para rodar em
um servidor Linux (Nginx + Gunicorn) em vez do desktop do usuario.

Fluxo:
  1. GET  /            -> formulario de upload da planilha (.xlsx)
  2. POST /upload      -> salva o arquivo, mostra abas/colunas para escolha
  3. GET  /colunas      -> (AJAX/JSON) lista colunas de uma aba especifica
  4. POST /analisar     -> roda o pipeline completo e devolve o .xlsx de
                            resultado para download

Nao ha banco de dados nem sessao de usuario: cada upload gera um
arquivo temporario identificado por um token aleatorio, removido apos
o download do resultado (ou pelo processo de limpeza periodica).
"""

from __future__ import annotations

import queue
import time
import uuid
from pathlib import Path

from flask import Flask, jsonify, render_template_string, request, send_file
from werkzeug.utils import secure_filename

from app.services.analysis_service import run_analysis
from app.services.excel_service import (
    ColumnNotFoundError,
    ExcelFileError,
    list_columns,
    list_sheet_names,
)
from app.services.export_service import export_results_to_excel

UPLOAD_DIR = Path("/tmp/material_duplicate_detector_uploads")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

# Tempo maximo (segundos) que um arquivo enviado fica disponivel antes
# de ser considerado "expirado" e elegivel para limpeza automatica.
_UPLOAD_TTL_SECONDS = 3600

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 50 * 1024 * 1024  # 50 MB por upload

# ---------------------------------------------------------------------------
# Templates (inline, sem dependencia de arquivos externos em templates/)
# ---------------------------------------------------------------------------

_BASE_STYLE = """
<style>
  :root { color-scheme: light; }
  body {
    font-family: system-ui, -apple-system, Segoe UI, Roboto, sans-serif;
    max-width: 720px; margin: 48px auto; padding: 0 20px; color: #1a1a1a;
    background: #fafafa;
  }
  h1 { font-size: 1.5rem; margin-bottom: 4px; }
  p.subtitle { color: #666; margin-top: 0; }
  .card {
    background: #fff; border: 1px solid #e2e2e2; border-radius: 10px;
    padding: 24px; margin-top: 24px;
  }
  label { display: block; font-weight: 600; margin: 16px 0 6px; font-size: 0.9rem; }
  select, input[type=file] {
    width: 100%; padding: 8px 10px; border: 1px solid #ccc; border-radius: 6px;
    font-size: 0.95rem; box-sizing: border-box;
  }
  button {
    margin-top: 24px; background: #1a56db; color: #fff; border: none;
    padding: 10px 22px; border-radius: 6px; font-size: 0.95rem; cursor: pointer;
  }
  button:hover { background: #1442a8; }
  button:disabled { background: #999; cursor: not-allowed; }
  .error {
    background: #fdecec; color: #a4222a; border: 1px solid #f3c2c2;
    border-radius: 8px; padding: 12px 16px; margin-top: 16px; font-size: 0.9rem;
  }
  .stats {
    background: #eef4ff; border: 1px solid #cfdcfa; border-radius: 8px;
    padding: 16px; margin-top: 16px; font-size: 0.9rem; line-height: 1.6;
  }
  .hint { color: #888; font-size: 0.82rem; margin-top: 4px; }
  a.download {
    display: inline-block; margin-top: 16px; background: #16803c; color: #fff;
    padding: 10px 22px; border-radius: 6px; text-decoration: none; font-weight: 600;
  }
</style>
"""

_UPLOAD_PAGE = """
<!doctype html>
<html lang="pt-br">
<head>
  <meta charset="utf-8">
  <title>Detector de Duplicidade de Materiais</title>
  {{ style|safe }}
</head>
<body>
  <h1>Detector de Duplicidade de Materiais</h1>
  <p class="subtitle">Envie uma planilha .xlsx para identificar materiais possivelmente duplicados.</p>

  {% if error %}<div class="error">{{ error }}</div>{% endif %}

  <div class="card">
    <form method="post" action="/upload" enctype="multipart/form-data">
      <label for="arquivo">Planilha (.xlsx)</label>
      <input type="file" id="arquivo" name="arquivo" accept=".xlsx" required>
      <div class="hint">Tamanho maximo: 50 MB.</div>
      <button type="submit">Enviar e continuar</button>
    </form>
  </div>
</body>
</html>
"""

_CONFIGURE_PAGE = """
<!doctype html>
<html lang="pt-br">
<head>
  <meta charset="utf-8">
  <title>Configurar Analise</title>
  {{ style|safe }}
</head>
<body>
  <h1>Configurar Analise</h1>
  <p class="subtitle">Arquivo: <strong>{{ original_name }}</strong></p>

  {% if error %}<div class="error">{{ error }}</div>{% endif %}

  <div class="card">
    <form method="post" action="/analisar" id="form-analisar">
      <input type="hidden" name="token" value="{{ token }}">

      <label for="aba">Aba (planilha)</label>
      <select id="aba" name="aba">
        {% for nome in abas %}
          <option value="{{ nome }}" {{ 'selected' if nome == aba_selecionada else '' }}>{{ nome }}</option>
        {% endfor %}
      </select>

      <label for="coluna_codigo">Coluna de Codigo</label>
      <select id="coluna_codigo" name="coluna_codigo">
        {% for col in colunas %}<option value="{{ col }}">{{ col }}</option>{% endfor %}
      </select>

      <label for="coluna_analise">Coluna de Texto (Dados Basicos)</label>
      <select id="coluna_analise" name="coluna_analise">
        {% for col in colunas %}<option value="{{ col }}">{{ col }}</option>{% endfor %}
      </select>
      <div class="hint">Esta e a coluna comparada para detectar duplicidade (ex.: "Texto Dados Basicos").</div>

      <button type="submit" id="btn-analisar">Rodar Analise</button>
    </form>
  </div>

<script>
const abaSelect = document.getElementById('aba');
const codigoSelect = document.getElementById('coluna_codigo');
const analiseSelect = document.getElementById('coluna_analise');
const token = {{ token|tojson }};

async function carregarColunas(aba) {
  const resp = await fetch(`/colunas?token=${encodeURIComponent(token)}&aba=${encodeURIComponent(aba)}`);
  const data = await resp.json();
  if (!resp.ok) { alert(data.erro || 'Erro ao carregar colunas.'); return; }
  const opcoes = data.colunas.map(c => `<option value="${c}">${c}</option>`).join('');
  codigoSelect.innerHTML = opcoes;
  analiseSelect.innerHTML = opcoes;
}

abaSelect.addEventListener('change', () => carregarColunas(abaSelect.value));

document.getElementById('form-analisar').addEventListener('submit', () => {
  const btn = document.getElementById('btn-analisar');
  btn.disabled = true;
  btn.textContent = 'Analisando... (pode levar alguns segundos)';
});
</script>
</body>
</html>
"""

_RESULT_PAGE = """
<!doctype html>
<html lang="pt-br">
<head>
  <meta charset="utf-8">
  <title>Resultado da Analise</title>
  {{ style|safe }}
</head>
<body>
  <h1>Analise concluida</h1>

  <div class="stats">
    Materiais lidos: <strong>{{ stats.total_materials }}</strong><br>
    Pares candidatos avaliados: <strong>{{ stats.total_candidates }}</strong><br>
    Duplicados confirmados: <strong>{{ stats.duplicados_confirmados }}</strong><br>
    Provaveis duplicados: <strong>{{ stats.provaveis_duplicados }}</strong><br>
    Semelhantes/diferentes: <strong>{{ stats.semelhantes_diferentes }}</strong><br>
    Tempo de importacao: {{ '%.2f'|format(stats.import_seconds) }}s |
    Tempo de processamento: {{ '%.2f'|format(stats.processing_seconds) }}s
  </div>

  <a class="download" href="/download/{{ token }}">Baixar planilha de resultado (.xlsx)</a>
  <p class="hint"><a href="/">Analisar outra planilha</a></p>
</body>
</html>
"""


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _cleanup_expired_uploads() -> None:
    now = time.time()
    for path in UPLOAD_DIR.glob("*"):
        try:
            if now - path.stat().st_mtime > _UPLOAD_TTL_SECONDS:
                path.unlink(missing_ok=True)
        except OSError:
            pass


def _upload_path(token: str) -> Path:
    return UPLOAD_DIR / f"{token}.xlsx"


def _result_path(token: str) -> Path:
    return UPLOAD_DIR / f"{token}.resultado.xlsx"


# ---------------------------------------------------------------------------
# Rotas
# ---------------------------------------------------------------------------


@app.get("/")
def index():
    _cleanup_expired_uploads()
    return render_template_string(_UPLOAD_PAGE, style=_BASE_STYLE, error=None)


@app.post("/upload")
def upload():
    arquivo = request.files.get("arquivo")
    if arquivo is None or arquivo.filename == "":
        return render_template_string(
            _UPLOAD_PAGE, style=_BASE_STYLE, error="Selecione um arquivo .xlsx."
        )

    filename = secure_filename(arquivo.filename)
    if not filename.lower().endswith(".xlsx"):
        return render_template_string(
            _UPLOAD_PAGE, style=_BASE_STYLE, error="O arquivo precisa ser .xlsx."
        )

    token = uuid.uuid4().hex
    destino = _upload_path(token)
    arquivo.save(destino)

    try:
        abas = list_sheet_names(destino)
        if not abas:
            raise ExcelFileError("A planilha nao possui nenhuma aba.")
        colunas = list_columns(destino, abas[0])
    except ExcelFileError as exc:
        destino.unlink(missing_ok=True)
        return render_template_string(_UPLOAD_PAGE, style=_BASE_STYLE, error=str(exc))

    return render_template_string(
        _CONFIGURE_PAGE,
        style=_BASE_STYLE,
        token=token,
        original_name=filename,
        abas=abas,
        aba_selecionada=abas[0],
        colunas=colunas,
        error=None,
    )


@app.get("/colunas")
def colunas():
    token = request.args.get("token", "")
    aba = request.args.get("aba", "")
    caminho = _upload_path(token)
    if not caminho.exists():
        return jsonify(erro="Arquivo expirado ou nao encontrado. Envie novamente."), 404
    try:
        return jsonify(colunas=list_columns(caminho, aba))
    except ExcelFileError as exc:
        return jsonify(erro=str(exc)), 400


@app.post("/analisar")
def analisar():
    token = request.form.get("token", "")
    aba = request.form.get("aba", "")
    coluna_codigo = request.form.get("coluna_codigo", "")
    coluna_analise = request.form.get("coluna_analise", "")

    caminho = _upload_path(token)
    if not caminho.exists():
        return render_template_string(
            _UPLOAD_PAGE,
            style=_BASE_STYLE,
            error="Arquivo expirado ou nao encontrado. Envie novamente.",
        )

    progress_queue: "queue.Queue" = queue.Queue()
    try:
        run_analysis(str(caminho), aba, coluna_codigo, coluna_analise, progress_queue)
    finally:
        pass

    final_message = None
    while not progress_queue.empty():
        message = progress_queue.get()
        if message["type"] in ("done", "error", "cancelled"):
            final_message = message

    caminho.unlink(missing_ok=True)

    if final_message is None or final_message["type"] == "error":
        erro = final_message["message"] if final_message else "Falha desconhecida na analise."
        try:
            abas = list_sheet_names(caminho) if caminho.exists() else [aba]
        except ExcelFileError:
            abas = [aba]
        return render_template_string(_UPLOAD_PAGE, style=_BASE_STYLE, error=erro)

    results = final_message["results"]
    stats = final_message["stats"]

    resultado_path = _result_path(token)
    export_results_to_excel(results, resultado_path)

    return render_template_string(
        _RESULT_PAGE, style=_BASE_STYLE, stats=stats, token=token
    )


@app.get("/download/<token>")
def download(token: str):
    caminho = _result_path(token)
    if not caminho.exists():
        return "Resultado nao encontrado ou expirado.", 404
    return send_file(
        caminho,
        as_attachment=True,
        download_name="resultado_duplicidade.xlsx",
        mimetype=(
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        ),
    )


@app.get("/healthz")
def healthz():
    """Endpoint simples de verificacao de saude (util para monitoramento)."""
    return jsonify(status="ok")


if __name__ == "__main__":
    # Uso apenas em desenvolvimento local. Em producao, rodar via
    # Gunicorn (ver DEPLOY.md), nunca com este servidor embutido.
    app.run(host="0.0.0.0", port=3000, debug=False)
