# e-CAC + Regularize (PGFN) — bot de certificado digital

Robô Python + Selenium (`undetected-chromedriver`) que autentica com
certificado digital A1 no gov.br/e-CAC e gera os relatórios de dívida
ativa no Regularize (PGFN) para um CNPJ. Windows only (lê o Windows
Certificate Store).

Também é um **plugin do Claude Code** — dá pra pedir pro Claude gerar o
relatório de um CNPJ em linguagem natural, ou via slash command.

## Requisitos

- Windows, com Google Chrome instalado.
- Um certificado digital A1 com uso "Client Authentication" já instalado
  no Windows Certificate Store (`certmgr.msc`) — o robô só lê, nunca
  importa/exporta/altera nada no store.
- Python 3.12+ e as dependências: `pip install -r requirements.txt`.

## Uso direto (linha de comando)

```
python -m src.main
```
Lista os certificados válidos, deixa escolher um, loga via gov.br e abre
o e-CAC numa aba nova pra continuar manualmente.

```
python -m src.main --regularize <CNPJ> [--limit N]
```
Gera o Relatório Consolidado e os Relatórios Detalhados por inscrição no
Regularize. A FASE 1 (login + troca de perfil de acesso) é **sempre
manual** — o robô abre um navegador visível e espera você confirmar antes
de continuar sozinho, headless, num segundo navegador. `--limit N` gera no
máximo N relatórios detalhados (útil pra validar antes de rodar tudo).
PDFs em `./output/{cnpj}/{DDMMYYYY}/`, log em
`artifacts/traces/regularize_*.jsonl`.

Detalhes de arquitetura, decisões e descobertas ao vivo (o que pode e não
pode ser automatizado, bugs de site já resolvidos etc.) estão em
`CLAUDE.md`, `RUNBOOK.md` e `SPEC.md` — leitura obrigatória antes de
alterar o fluxo.

## Uso via Claude Code (plugin)

Pra testar localmente sem instalar:
```
claude --plugin-dir .
```

Pra deixar carregado automaticamente em toda sessão, copie (ou linke) esta
pasta pra dentro de `~/.claude/skills/`:
```
cp -r . ~/.claude/skills/ecac-regularize
```
Na próxima sessão o Claude Code carrega como `ecac-regularize@skills-dir`
— sem marketplace, sem passo de instalação.

Com o plugin carregado, dois skills ficam disponíveis:

- `/ecac-regularize:gerar-relatorio-regularize <CNPJ> [--limit N]` — ou
  simplesmente peça em linguagem natural ("gera o relatório da PGFN pro
  CNPJ 17462219000105"); o Claude reconhece e invoca sozinho.
- `/ecac-regularize:abrir-ecac` — só abre o e-CAC autenticado, sem gerar
  relatório.

A instrução completa de como o Claude deve operar cada fluxo (o que pode
automatizar, o que é sempre manual, onde ficam os outputs, como
diagnosticar falha) está nos próprios `skills/*/SKILL.md` — é isso que o
Claude lê, não este README nem o `CLAUDE.md` (que só vale enquanto se está
editando este repositório, não quando o plugin roda em outro projeto).
