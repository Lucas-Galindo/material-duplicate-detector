# Detector de Duplicidade de Materiais

Aplicação desktop em Python para identificar materiais possivelmente
duplicados em planilhas Excel, com foco no campo **"Texto Dados Básicos"**,
por meio de análise técnica explicável (não apenas similaridade textual).

Este documento é o entregável da **Sprint 0 — Planejamento e Arquitetura**.
Nenhuma lógica de negócio foi implementada ainda: apenas a estrutura de
diretórios, os módulos vazios (com docstring indicando responsabilidade e
sprint de implementação), os arquivos de configuração iniciais e este plano.

---

## 1. Arquitetura Final Proposta

Aplicação desktop monolítica (um processo), organizada em camadas
independentes e testáveis, sem framework web e sem serviços externos:

```
GUI (Tkinter/ttk)
   │  (chama, nunca é chamada por)
   ▼
Services (orquestração: excel, análise, export)
   │
   ▼
Core (normalizer → tokenizer → technical_parser → signature_builder
      → candidate_generator → comparator → classifier)
   │
   ├── Indexes (inverted_index, signature_index, trie)
   ├── Rules (rule_loader + JSON em /config)
   └── Models (dataclasses imutáveis que atravessam o pipeline)
```

Princípios:

- **Separação estrita entre GUI e lógica de negócio.** A GUI nunca contém
  regra de negócio; ela chama `services`, que chama `core`. Isso permite
  testar 100% do `core` e do `services` sem abrir uma janela.
- **Pipeline em estágios, cada um com saída própria e auditável.** Nenhum
  estágio sobrescreve a saída do estágio anterior — tudo fica disponível em
  `ParsedMaterial` (ver seção 4) para explicação e auditoria.
- **Regras fora do código.** Abreviações, equivalências, termos críticos e
  símbolos protegidos vivem em JSON (`/config`), carregados por
  `rule_loader`, nunca hardcoded em `core`.
- **Geração de candidatos separada da comparação profunda.** Índices
  (Hash Map / índice invertido) evitam comparação O(n²); só pares
  candidatos plausíveis chegam ao comparador profundo.
- **Decisão final baseada em regras explícitas, não em score único.**
  Similaridade textual é só um sinal auxiliar, nunca o critério de decisão
  (ver seção 8).
- **Processamento fora da thread de UI**, comunicando-se por fila
  (`queue.Queue`) para manter a interface responsiva.

## 2. Bibliotecas Recomendadas

| Necessidade | Biblioteca | Justificativa |
|---|---|---|
| Leitura/escrita de Excel | `pandas` + `openpyxl` | Padrão de mercado, robusto para múltiplas abas, tipos mistos e exportação `.xlsx`. |
| Interface gráfica | `tkinter` + `ttk` (stdlib) | Já vem com o Python, estável, empacota bem com PyInstaller, sem dependências binárias extras. |
| Testes | `pytest` | Padrão, fixtures simples, boa granularidade para os muitos casos técnicos exigidos. |
| Empacotamento Windows | `PyInstaller` | Gera `.exe` standalone sem exigir Python no computador do usuário. |
| Instalador | `Inno Setup` | Gratuito, amplamente usado para apps Windows, script declarativo simples. |
| Números/frações | `re` + `fractions.Fraction` (stdlib) | Suficiente para parsing de frações/decimais sem dependência extra. |

Não serão usadas bibliotecas de NLP/embeddings nesta fase (ver seção 8) —
mantém o executável pequeno e o comportamento 100% explicável.

## 3. Estrutura de Diretórios

```
material_duplicate_detector/
├── app/
│   ├── main.py
│   ├── gui/            (main_window, import_view, analysis_view, results_view, settings_view)
│   ├── core/            (normalizer, tokenizer, technical_parser, signature_builder,
│   │                     candidate_generator, comparator, classifier)
│   ├── indexes/         (inverted_index, signature_index, trie)
│   ├── rules/            (rule_loader, abbreviations, equivalents, critical_terms, protected_symbols)
│   ├── services/         (excel_service, analysis_service, export_service)
│   └── models/           (material, parsed_material, technical_signature, comparison_result)
├── config/               (abbreviations.json, equivalents.json, critical_terms.json, protected_symbols.json)
├── tests/                (um arquivo de teste por módulo do core/indexes)
├── requirements.txt
├── README.md
└── build/                (saída do PyInstaller — não versionado)
```

Já criada nesta Sprint, com módulos vazios (apenas docstring dizendo o que
farão e em qual sprint serão implementados) e os JSON de `/config` com uma
estrutura inicial mínima e comentada.

## 4. Modelos de Dados (visão geral — implementados na Sprint 2/5/6)

```python
@dataclass(frozen=True)
class Material:
    row_index: int
    code: str
    raw_fields: dict[str, str]      # todas as colunas originais da linha
    analysis_text: str              # valor original da coluna escolhida p/ análise

@dataclass(frozen=True)
class ParsedMaterial:
    material: Material
    original_text: str              # nunca alterado
    normalized_text: str
    raw_tokens: list[str]
    technical_tokens: list[str]
    critical_tokens: list[str]
    numbers: list[Number]           # inteiros, decimais, frações, mistos
    units: list[UnitMeasure]        # valor + unidade (ex: "20 CM")
    symbols: list[str]              # símbolos técnicos preservados
    normalized_terms: list[str]     # após abreviação/equivalência

@dataclass(frozen=True)
class TechnicalSignature:
    normalized_signature: str
    token_signature: str
    numeric_signature: str
    unit_signature: str
    critical_terms_signature: str
    ordered_signature: str
    unordered_signature: str        # ex: frozenset ordenável p/ hashing

@dataclass(frozen=True)
class ComparisonResult:
    material_a: Material
    material_b: Material
    classification: Literal["DUPLICADO_CONFIRMADO", "PROVAVEL_DUPLICADO", "SEMELHANTE_DIFERENTE"]
    confidence: float               # sinal auxiliar, não decisório
    equal_elements: list[str]
    formatting_differences: list[str]
    technical_differences: list[str]
    ambiguous: bool
    review_status: Literal["PENDENTE", "APROVADO", "REJEITADO"]
```

`Material` e `ParsedMaterial` são imutáveis (`frozen=True`): o texto
original nunca é sobrescrito em nenhum ponto do pipeline — cada
transformação produz um novo campo, preservando a cadeia completa para
auditoria (ver seção 6 do prompt: "Explicação obrigatória do resultado").

## 5. Múltiplas Representações do Texto

Conforme exigido, cada material carrega simultaneamente (nenhuma substitui
a anterior):

1. Texto original
2. Texto normalizado (maiúsculas, espaços, acentuação segura, separadores)
3. Tokens brutos
4. Tokens técnicos (após remover ruído não técnico)
5. Tokens críticos (termos que nunca podem divergir sem virar "diferente")
6. Números extraídos (inteiro/decimal/fração/misto, com posição)
7. Unidades extraídas (valor + unidade, ex.: `20 CM`, `1/2 MM`)
8. Símbolos técnicos relevantes (protegidos por `protected_symbols.json`)
9. Termos normalizados (após abreviação/equivalência configurável)
10. Assinatura técnica (múltiplas — seção 4)
11. Chaves auxiliares para geração de candidatos (derivadas das
    assinaturas, usadas como chave no índice invertido)

## 6. Fluxo Completo de Processamento

```
Excel → Leitura (excel_service)
      → Material (1 por linha)
      → normalizer            → texto normalizado
      → tokenizer              → tokens brutos/técnicos + números/unidades/símbolos
      → rule_loader (rules)    → termos normalizados (abreviação/equivalência)
      → technical_parser       → estrutura semântica (medida, separador, medida...)
      → signature_builder      → múltiplas assinaturas
      → inverted_index +
        signature_index +
        trie (auxiliar)        → índices para geração de candidatos
      → candidate_generator    → pares candidatos (não todos-contra-todos)
      → comparator              → diferenças por categoria (números, unidades,
                                   termos, símbolos, ordem)
      → classifier               → DUPLICADO_CONFIRMADO / PROVAVEL_DUPLICADO /
                                    SEMELHANTE_DIFERENTE
      → ComparisonResult (explicável) → GUI / export_service → Excel
```

O pipeline roda em uma thread de trabalho (`analysis_service`), publicando
progresso em uma `queue.Queue` consumida pela GUI via `after()` do Tk, para
nunca bloquear a interface.

## 7. Estratégia de Geração de Candidatos

Para evitar O(n²) em 5.000–20.000 registros:

- **Índice invertido** termo técnico → lista de materiais (ex.: `PARAFUSO`,
  `M10`, `INOX`), construído uma vez sobre os tokens técnicos.
- **Índice por assinatura** (Hash Map) para as assinaturas normalizada,
  numérica, de unidades e não-ordenada — materiais com a mesma assinatura
  (ou assinaturas com interseção relevante) viram candidatos diretos.
- **União dos conjuntos de candidatos** de cada índice, com deduplicação de
  pares (A,B) == (B,A).
- **Trie auxiliar** apoia o reconhecimento de abreviações/termos colados
  durante a tokenização (não decide duplicidade, apenas alimenta os
  índices acima com termos corretamente segmentados).
- Materiais sem nenhuma interseção de termo/assinatura relevante nunca são
  comparados profundamente — corta o grosso das combinações irrelevantes.

## 8. Estratégia de Comparação Técnica

O comparador nunca decide por uma única métrica de similaridade. Para cada
par candidato, ele produz comparações independentes por categoria:

- **Números**: mesma quantidade e mesmos valores (inteiros/decimais/frações
  tratados por valor equivalente: `1/2` == `0.5`), preservando a unidade
  associada.
- **Unidades**: mesma unidade após normalização segura de agrupamento
  (`20CM` ≡ `20 CM`), mas `1/2"` ≠ `1/2` (símbolo protegido altera
  interpretação).
- **Termos críticos**: qualquer divergência aqui (ex.: `DIANTEIRO` vs
  `TRASEIRO`, `AZUL` vs `PRETO`) força classificação "diferente" ou
  "semelhante, mas diferente", independente da similaridade textual.
- **Termos normalizados/abreviações**: aplicação das equivalências
  configuráveis antes de comparar (`DIANT` ≡ `DIANTEIRO`).
- **Símbolos técnicos protegidos**: comparados literalmente; sua ausência/
  presença é reportada como diferença técnica potencial, não ignorada.
- **Ordem dos elementos**: comparação com e sem ordenação (assinatura
  ordenada vs não-ordenada) para tratar `PARAFUSO INOX M10 X 20` ≡
  `PARAFUSO M10X20 AÇO INOX`.
- **Similaridade textual** (ex.: razão de tokens em comum) é calculada e
  exposta apenas como `confidence` auxiliar — nunca é o campo usado pelo
  `classifier` para decidir a categoria.

O `classifier` combina os resultados por categoria em regras explícitas
(não em um único score) para chegar a `DUPLICADO_CONFIRMADO`,
`PROVAVEL_DUPLICADO` ou `SEMELHANTE_DIFERENTE`, sempre anexando as listas
de semelhanças, diferenças de formatação e diferenças técnicas usadas na
decisão (requisito de explicabilidade).

Embeddings/similaridade semântica ficam fora do escopo atual; poderão ser
avaliados futuramente apenas como fonte adicional de candidatos, nunca como
mecanismo de confirmação.

## 9. Estratégia de Testes

- Um arquivo de teste por módulo central (`tests/test_*.py`), criado desde
  já como placeholder, implementado junto com o módulo correspondente em
  cada sprint — nenhuma sprint é considerada concluída sem seus testes.
- Casos obrigatórios do prompt (`20 CM X 1/2 MM` ≡ `20CMX1/2MM`;
  `1/2"` ≠ `1/2`; `M10` ≠ `M12`; `DIANT` ≡ `DIANTEIRO`; `DIANTEIRO` ≠
  `TRASEIRO`; `MASCULINO` ≠ `FEMININO`; `AZUL` ≠ `PRETO`) serão codificados
  como testes parametrizados de regressão, reexecutados a cada sprint que
  tocar `core/`.
- Testes de índice/candidatos incluirão um teste de "não explosão
  combinatória" (nº de comparações profundas << n²) em um dataset sintético
  de alguns milhares de registros.
- Teste de integração ponta a ponta (Sprint 10) com planilhas sintéticas
  representando os casos acima, cobrindo importação → classificação →
  exportação.
- `pytest` como runner único; sem mocks de GUI — a lógica é testada 100%
  fora do Tkinter.

## 10. Estratégia de Desempenho

Ordem de prioridade conforme o prompt: **precisão > explicabilidade >
eficiência > velocidade**.

- Custo evitado por construção (índices em vez de todos-contra-todos), não
  por paralelismo ou otimização prematura.
- Estruturas em memória (Hash Maps, listas) — sem banco de dados; dataset
  alvo (5.000–20.000 linhas) cabe confortavelmente em RAM.
- Métricas coletadas e exibidas ao usuário: tempo de importação, tempo de
  processamento, nº de candidatos gerados, nº de comparações profundas
  executadas e, quando disponível via `resource`/`tracemalloc`, memória
  utilizada — tudo reportado ao final da análise (Sprint 8/9).
- Nenhuma meta de tempo real "duro" é imposta; "tempo razoável em
  computador comum" é validado empiricamente na Sprint 10 com planilhas
  reais/sintéticas de diferentes tamanhos.

## 11. Estratégia de Empacotamento para Windows

- **PyInstaller** (`--onefile` ou `--onedir` — decisão final na Sprint 11
  após medir tempo de start e falsos positivos de antivírus, que costumam
  ser menores em `--onedir`) gerando um `.exe` standalone, sem exigir
  Python nem `pip install` na máquina do usuário.
- Bundle inclui os JSON de `/config` como dados (`--add-data`), lidos em
  runtime por caminho relativo ao executável (resolvido via
  `sys._MEIPASS` quando empacotado).
- **Inno Setup** para gerar um instalador `.exe` que copia os arquivos,
  cria atalho no menu iniciar/desktop e não requer terminal nem comandos
  do usuário final.
- Validação final (Sprint 13) inclui rodar o instalador e o executável em
  uma máquina Windows sem Python instalado.

## 12. Plano de Desenvolvimento (Sprints)

| Sprint | Entrega |
|---|---|
| 0 | Planejamento e arquitetura (este documento) |
| 1 | Importação de Excel (arquivo, abas, colunas) |
| 2 | Modelos de dados e normalização segura |
| 3 | Tokenizador técnico |
| 4 | Regras e equivalências (JSON externo) |
| 5 | Assinaturas técnicas e índices (candidatos) |
| 6 | Comparador técnico profundo e explicável |
| 7 | Classificação (duplicado/provável/semelhante) |
| 8 | Interface: importação, configuração, execução, progresso |
| 9 | Interface de resultados, filtros e exportação Excel |
| 10 | Testes com planilhas reais/sintéticas em volume |
| 11 | Empacotamento com PyInstaller |
| 12 | Instalador (Inno Setup) e distribuição |
| 13 | Teste final completo (unitário, integração, desempenho, executável) |

Cada sprint só é iniciada após aprovação explícita da sprint anterior.

---

## Status Atual

- [x] Sprint 0 — Planejamento e Arquitetura
- [x] Sprint 1 — Importação de Excel (`excel_service`)
- [x] Sprint 2 — Modelos de dados e normalização segura (`normalizer`)
- [x] Sprint 3 — Tokenizador técnico (`tokenizer`)
- [x] Sprint 4 — Regras e equivalências configuráveis via JSON (`rule_loader`)
- [x] Sprint 5 — Assinaturas técnicas e índices de candidatos
      (`signature_builder`, `inverted_index`, `signature_index`, `trie`,
      `candidate_generator`)
- [x] Sprint 6 — Comparador técnico profundo e explicável (`comparator`)
- [x] Sprint 7 — Classificação (`classifier`)
- [x] Sprint 8 — Interface: importação, configuração, execução, progresso
      (`main_window`, `import_view`, `analysis_view`, `analysis_service`)
- [x] Sprint 9 — Resultados, filtros, detalhe do par e exportação Excel
      (`results_view`, `export_service`)
- [x] Sprint 10 — Testes com planilhas sintéticas em volume (até 20.000
      registros) — encontrou e corrigiu um bug real de desempenho
      (explosão combinatória no índice de assinaturas) e um bug real de
      cobertura (grupos grandes de duplicados idênticos podiam ficar de
      fora dos candidatos)
- [x] Sprint 11 — Empacotamento com PyInstaller (`packaging/app.spec`)
- [x] Sprint 12 — Instalador Inno Setup (`packaging/installer.iss`)
- [x] Sprint 13 — Teste final e relatório de limitações conhecidas

## Como executar os testes

```bash
pip install -r requirements.txt
pytest
```

69 testes automatizados cobrindo normalização, tokenização, regras,
assinaturas/índices (incluindo testes de eficiência), comparador,
classificador, importação/exportação de Excel, orquestração em thread e
dois testes de integração ponta a ponta (planilha com todos os casos
obrigatórios do escopo + planilha sintética de 5.000 registros).

## Como executar a aplicação (requer Tkinter — ver Limitações)

```bash
python -m app.main
```

## Como gerar o executável Windows (Sprint 11/12)

Em uma máquina Windows com o `requirements.txt` instalado:

```bash
pyinstaller packaging/app.spec
```

Gera `dist/DetectorDuplicidadeMateriais/` com o executável e os JSON de
`config/` empacotados. Em seguida, compile `packaging/installer.iss` no
Inno Setup Compiler (ou `iscc packaging/installer.iss`) para gerar o
instalador `.exe` em `packaging/output/`.

### Levando o `.exe` para outra máquina sem compilar lá

O modo `--onedir` gera uma **pasta**, não um arquivo único — o erro
`Failed to load Python DLL` / `LoadLibrary... o módulo especificado não
foi encontrado` ao rodar em outra máquina quase sempre significa que
faltou algo nessa cópia. Checklist, na ordem mais provável:

1. **Copie a pasta `dist\DetectorDuplicidadeMateriais\` inteira**, não
   só o `.exe`. Ela inclui uma subpasta `_internal` com o `python3xx.dll`
   e todas as dependências (`pandas`, `openpyxl`, Tkinter) — sem ela o
   executável não tem como rodar. Copiar só o `.exe` é a causa mais
   comum desse erro especificamente.
2. Se copiou a pasta inteira e o erro persiste, **instale o Microsoft
   Visual C++ Redistributable (x64)** na máquina de destino:
   https://aka.ms/vs/17/release/vc_redist.x64.exe — o runtime do Python
   depende dele e uma máquina "limpa" pode não tê-lo.
3. Confira se o antivírus da máquina de destino não removeu/colocou em
   quarentena algum arquivo de dentro de `_internal` durante a cópia
   (isso quebra o bundle silenciosamente).
4. A partir desta correção, `upx` foi desativado no `packaging/app.spec`
   (`upx=False` no `EXE`/`COLLECT`): DLLs comprimidas com UPX podem
   falhar em decodificar em certas combinações de Windows/antivírus,
   gerando exatamente esse mesmo erro. Se você já tinha gerado um build
   com uma versão anterior da spec (`upx=True`), gere um novo com
   `pyinstaller packaging/app.spec` antes de testar em outra máquina.
5. O caminho mais robusto para distribuir é o instalador do Inno Setup
   (`packaging/installer.iss`, Sprint 12): ele empacota a pasta inteira
   corretamente e evita o erro de "copiei só o `.exe`" por completo —
   recomendado em vez de copiar a pasta manualmente.

## Limitações conhecidas

- **GUI não testada visualmente em Windows real.** O ambiente Linux
  deste projeto não tem Tkinter disponível para o interpretador Python
  usado pelo `pytest` (por isso não há testes automatizados de GUI na
  suíte). A interface foi validada com um smoke test end-to-end headless
  (Xvfb + Tkinter do Python de sistema): abrir planilha, selecionar
  colunas, rodar a análise em thread, carregar resultados na tabela e
  abrir o diálogo de detalhe — tudo funcionou sem erros. Isso confirma
  que o código da GUI é estruturalmente correto, mas o teste manual em
  Windows (aparência, atalhos de teclado, comportamento de diálogos
  nativos) ainda precisa ser feito por um usuário em máquina real.
- **`.exe` Windows não gerado nem testado neste ambiente.** PyInstaller
  não faz cross-compilation: rodar `pyinstaller packaging/app.spec`
  neste container Linux gera um binário Linux, não um `.exe` Windows.
  A spec foi validada localmente (build Linux completo, sem erros,
  aceitando os hidden imports `pandas`/`openpyxl` e embutindo `config/`)
  mas o `.exe` real, o instalador Inno Setup e a execução em um Windows
  sem Python instalado (o requisito final do projeto) precisam ser
  gerados e testados em uma máquina Windows.
- **Índices de bloqueio só entram em cena acima de `EXHAUSTIVE_THRESHOLD`
  (4.000 materiais).** Até esse tamanho, `candidate_generator` gera
  TODOS os pares (i, j) diretamente — nenhum indice de bloqueio é
  usado, então não há nenhuma chance de um duplicado real "sumir" por
  causa de um corte de frequência. Acima de 4.000 materiais,
  `InvertedIndex`/`SignatureIndex` entram em ação com um limite mais
  generoso que antes (ignoram termos/assinaturas presentes em mais de
  ~5% dos materiais, mínimo 300 — antes era 20) para reduzir ainda mais
  o risco de perda nessa faixa, com duplicados exatos sempre cobertos
  por um agrupamento dedicado sem limite algum (Sprint 10). Continua
  sendo, em tese, uma limitação arquitetural para bases muito grandes
  (> 4.000 linhas) e extremamente homogêneas, mas não é mais um risco
  para o caso de uso típico (catálogos de alguns milhares de itens).
- **Não há tela de configuração de regras (`settings_view`) nem edição
  de abreviações/equivalências pela interface.** As regras (Sprint 4)
  só podem ser editadas diretamente nos arquivos `config/*.json`.

## Filtro de confiança mínima na exportação (70%)

A tela de Resultados tem um campo "Confiança minima (%)" (padrão 70%)
que filtra a tabela e o arquivo exportado juntos — o que você vê na
tela é exatamente o que sai no Excel. `export_service.export_results_to_excel`
também aplica esse filtro por padrão (`min_confidence=0.70`) quando
chamado fora da GUI.

Importante: `confidence` é a similaridade textual bruta (um sinal
auxiliar), não o critério que decide a classificação — por desenho, a
classificação (`DUPLICADO_CONFIRMADO`/`PROVAVEL_DUPLICADO`/
`SEMELHANTE_DIFERENTE`) nunca depende só de percentual (ver seção
"Estratégia de Comparação Técnica"). Isso significa que um par
tecnicamente confirmado como duplicado (sem nenhuma diferença técnica)
mas com textos muito reordenados ou reescritos pode, em casos raros,
ter menos de 70% de similaridade textual e ficar de fora do arquivo
filtrado. Se isso for um problema no seu uso, baixe o limite para 0%
na tela antes de exportar (ou passe `min_confidence=None` chamando o
serviço diretamente) para conferir todos os pares gerados.

## Coluna "Descrição Curta" (contexto, não entra no cálculo)

Se a planilha de origem tiver uma coluna chamada "Descrição Curta" ou
"Descricao Curta" (detecção tolerante a acentuação/caixa/espaços — ver
`excel_service.find_short_description_column`), ela é carregada
automaticamente em `Material.short_description` e aparece no arquivo
final como duas colunas, **"Descricao Curta A"** e **"Descricao Curta
B"**, uma para cada material do par. Também aparece no diálogo de
detalhe do par na tela de Resultados, quando presente.

Esse campo é **puramente informativo**: existe porque duas linhas
podem ter "Texto Dados Básicos" idênticos mas descrições curtas
diferentes, e ajuda o revisor a entender o contexto de cada item. Ele
**nunca** entra em `normalizer`, `tokenizer`, `technical_parser`,
`signature_builder`, `candidate_generator`, `comparator` ou
`classifier` — o cálculo de similaridade/confiança e a decisão de
classificação consideram exclusivamente o campo de "Dados Básicos"
(`analysis_text`). `short_description` só é lido, no fim do pipeline,
por `classifier.build_comparison_result` para popular o resultado
final — depois que classificação e confiança já foram decididas.
Se a coluna não existir na planilha, o campo fica vazio e nada muda no
restante do fluxo.
