---
description: Verifica se o repositório local está sincronizado com origin/main e atualiza (git pull --ff-only) se estiver limpo.
---

Verifique e sincronize o repositório com `origin/main`. Siga exatamente estes passos:

1. `git fetch origin`
2. `git status` — se houver mudanças não commitadas (staged ou não), **pare aqui** e avise
   o usuário quais arquivos estão sujos; pergunte se quer commitar/stash antes de continuar.
   Nunca descarte trabalho local sozinho.
3. Compare local `main` com `origin/main` (`git rev-list --left-right --count main...origin/main`):
   - **Igual** (0/0): já está sincronizado, avise e pare.
   - **Só atrás** (0 ahead / N behind): rode `git pull --ff-only origin main` e resuma os
     commits novos (`git log --oneline HEAD..origin/main` antes do pull).
   - **Só à frente** (N ahead / 0 behind): avise que há commits locais não enviados; não
     dê push sozinho, só informe.
   - **Divergiu** (ambos > 0): **não** faça merge/rebase automático — reporte a divergência
     (quantos commits de cada lado) e pergunte como o usuário quer resolver.
4. Ao final, informe o estado atual do branch (`git status` curto) e se
   `RUNBOOK.md`/`SPEC.md`/código mudaram na atualização (útil pra saber se vale reler antes
   de rodar `/rodar-regularize`).
