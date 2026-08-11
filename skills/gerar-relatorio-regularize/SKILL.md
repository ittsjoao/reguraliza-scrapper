---
description: Gera o Relatório Consolidado e os Relatórios Detalhados de dívida ativa (Regularize/PGFN) para um CNPJ, autenticando via certificado digital A1 no gov.br/e-CAC. Use quando o usuário pedir para gerar, baixar ou atualizar o relatório de dívida ativa/Regularize/PGFN de um CNPJ específico.
---

# Gerar relatório Regularize (PGFN)

Este skill roda o CLI Python deste plugin (`src/main.py`), que automatiza
o Regularize da PGFN via Selenium/`undetected-chromedriver`. Você (a IA)
NÃO controla o navegador diretamente — só invoca o CLI e interpreta o
resultado.

## Entrada

`$ARGUMENTS` traz o CNPJ e, opcionalmente, `--limit N`, do jeito que o
usuário digitou depois do nome do skill (ex.: `17462219000105 --limit 10`).
Se o skill foi auto-invocado por linguagem natural (sem `$ARGUMENTS`),
extraia o CNPJ (e um eventual limite) do pedido do usuário — pergunte se
não estiver claro qual CNPJ.

## Restrição crítica — você não consegue rodar isto sozinho até o fim

O fluxo tem duas fases:

1. **FASE 1 (login + troca de perfil de acesso) é sempre manual e precisa
   de um terminal interativo de verdade.** O CLI abre um Chrome visível e
   trava num `input()` esperando o operador logar no gov.br (certificado +
   captcha eventual) e trocar o "perfil de acesso" pro CNPJ no e-CAC. Isso
   é proposital — automatizar esse clique é bloqueado pela Receita Federal
   como "acesso automatizado" (sem workaround conhecido). Se você (a IA)
   rodar o comando abaixo por uma ferramenta de shell não-interativa, ele
   vai travar esperando um Enter que nunca chega.
   **Nunca tente rodar `--regularize` você mesma em background/não-interativo.**
   Diga ao usuário para rodar o comando no terminal dele mesmo, faça a
   parte manual, e avise quando terminar (ou compartilhe o log).
2. **FASE 2/3 (Relatório Consolidado + Detalhados) rodam sozinhas**, num
   segundo Chrome headless que herda a sessão da FASE 1 via cookies — sem
   repetir login nem clique nenhum.

## Comando

Rode sempre a partir da raiz do plugin (`${CLAUDE_PLUGIN_ROOT}`):

```
cd "${CLAUDE_PLUGIN_ROOT}"
python -m src.main --regularize <CNPJ> [--limit N]
```

- `<CNPJ>`: só dígitos ou formatado, tanto faz.
- `--limit N`: opcional, gera no máximo N relatórios detalhados — sugira
  isso na primeira vez que rodar pra um CNPJ novo, pra validar rápido
  antes de rodar tudo (pode ter dezenas de inscrições).

Pré-requisitos (confira antes de instruir o usuário a rodar, e avise se
algo faltar):
- Windows, com Google Chrome instalado.
- Um certificado digital A1 com uso "Client Authentication" já instalado
  no Windows Certificate Store (o robô só lê, nunca importa/gera).
- Dependências Python instaladas: `pip install -r requirements.txt`
  (dentro de `${CLAUDE_PLUGIN_ROOT}`).

## O que esperar depois que o usuário confirmar a FASE 1

- PDFs em `${CLAUDE_PLUGIN_ROOT}/output/{cnpj_sem_pontuacao}/{DDMMYYYY}/`
  — um consolidado + um por inscrição.
- Log estruturado (JSONL, um evento por linha) em
  `${CLAUDE_PLUGIN_ROOT}/artifacts/traces/regularize_*.jsonl` — leia com
  `Read`/`Grep` pra confirmar sucesso; eventos com `"evento":
  "DIVERGENCIA"` indicam algo que não saiu como esperado.
- No fim, o CLI imprime "Relatório consolidado: ..." e "Relatórios
  detalhados gerados: N".

## Se algo falhar

Leia `${CLAUDE_PLUGIN_ROOT}/RUNBOOK.md` antes de propor uma correção —
tem a lista de problemas já resolvidos ao vivo (seletor mudou, timeout
baixo, sessão headless via cookies não autenticou, etc.) com a causa raiz
de cada um. Não invente workaround pra troca de perfil bloqueada — não
tem, é sempre manual.

## Nunca faça

- Nunca tente automatizar a troca de "perfil de acesso" no e-CAC nem o
  login por certificado — ver acima.
- Nunca instrua a clicar em "Imprimir" no Regularize — trava a aba (o
  robô já captura o PDF via CDP, sem precisar disso).
- Nunca rode `--regularize` sem avisar o usuário que a FASE 1 é manual e
  que ele precisa estar no terminal pra fazer login/trocar perfil.
