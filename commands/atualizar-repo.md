---
description: Sincroniza esta cópia com origin/main via hard reset — sem merge, sem stash, sem perguntar. origin/main é sempre a fonte da verdade; qualquer coisa local que não esteja lá é descartada.
---

Sincronize com `origin/main` de forma destrutiva. Este comando existe pra manter
uma cópia instalada como skill/plugin (`~/.claude/skills/ecac-regularize` ou
equivalente) idêntica ao repositório remoto — não pra preservar edição local.
Siga exatamente estes passos, **sem pedir confirmação e sem parar pra
perguntar nada**:

1. `cd "${CLAUDE_PLUGIN_ROOT}"` (garante que roda na pasta certa, mesmo
   invocado de dentro de outro projeto).
2. `git fetch origin`
3. Guarde o hash atual (`git rev-parse --short HEAD`) só pra poder listar os
   commits novos depois.
4. `git reset --hard origin/main` — descarta commits locais não enviados,
   staged, unstaged e conflitos, sem merge e sem stash. O remoto sempre vence.
5. `git clean -fd` (sem `-x`) — remove arquivos/pastas não rastreados que não
   estejam no `.gitignore` (ex.: cópias soltas de uma instalação antiga antes
   deste comando existir). Preserva o que está no `.gitignore` de propósito
   (`.env`, `output/`, `artifacts/traces/*.jsonl` etc. — são gerados localmente
   pelo próprio robô).
6. Informe ao usuário: `git log --oneline <hash-antigo>..HEAD` (o que veio de
   novo) e se `RUNBOOK.md`/`SPEC.md`/código mudaram (útil pra saber se vale
   reler antes de rodar `/rodar-regularize`).

**Isto é diferente do fluxo de desenvolvimento normal.** Se `${CLAUDE_PLUGIN_ROOT}`
apontar pro repositório onde alguém está editando/committando (não uma cópia
instalada só pra uso do plugin), avise antes de rodar: qualquer commit ou
edição local não enviada a `origin/main` será perdida sem aviso nem stash.
