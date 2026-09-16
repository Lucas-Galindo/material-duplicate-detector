# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec (Sprint 11).

Gera um executavel Windows standalone do Detector de Duplicidade de
Materiais, sem exigir Python instalado na maquina do usuario final.

Uso (em uma maquina Windows, com o requirements.txt instalado):

    pyinstaller packaging/app.spec

O executavel final fica em ``dist/DetectorDuplicidadeMateriais/``
(modo --onedir, escolhido por iniciar mais rapido e gerar menos falsos
positivos de antivirus do que --onefile; ver README.md, secao 11).
Os arquivos de config/*.json sao empacotados como dados e devem ser
lidos em runtime via caminho relativo ao executavel (sys._MEIPASS
quando empacotado, ou app/rules/rule_loader._DEFAULT_CONFIG_DIR fora
do bundle).

IMPORTANTE ao levar o build para outra maquina (sem compilar la):
  1. Copie a pasta ``dist/DetectorDuplicidadeMateriais/`` INTEIRA
     (executavel + subpasta ``_internal``), nunca so o .exe sozinho —
     copiar so o .exe e a causa mais comum de
     "Failed to load Python DLL / LoadLibrary... modulo especificado".
  2. ``upx`` fica desativado de proposito (ver EXE/COLLECT abaixo):
     DLLs comprimidas com UPX falham silenciosamente em algumas
     combinacoes de Windows/antivirus, com o mesmo erro de DLL nao
     encontrada — prioriza-se confiabilidade sobre tamanho do arquivo.
  3. Se o erro persistir na maquina de destino mesmo com a pasta
     completa, instale o Microsoft Visual C++ Redistributable (x64):
     https://aka.ms/vs/17/release/vc_redist.x64.exe — o runtime do
     Python precisa dele e ele pode nao estar presente numa maquina
     "limpa". O ideal e distribuir via ``packaging/installer.iss``
     (Sprint 12), que resolve isso de forma transparente para o
     usuario final.
"""

import sys
from pathlib import Path

block_cipher = None

project_root = Path(SPECPATH).parent

a = Analysis(
    [str(project_root / "app" / "main.py")],
    pathex=[str(project_root)],
    binaries=[],
    datas=[
        (str(project_root / "config"), "config"),
    ],
    hiddenimports=[
        "pandas",
        "openpyxl",
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="DetectorDuplicidadeMateriais",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name="DetectorDuplicidadeMateriais",
)
