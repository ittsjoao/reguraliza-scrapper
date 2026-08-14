---
description: Roda src/main.py --regularize (relatórios PGFN + SISPAR + CAPAG) em background, aguarda confirmação de login/troca de perfil no chat, e acompanha os logs até o fim.
---

Rode o fluxo completo do Regularize (Relatório Consolidado, Relatórios Detalhados,
Parcelamentos/SISPAR, CAPAG) para o CNPJ `$ARGUMENTS`, sem depender de `input()`
num terminal interativo. Siga exatamente estes passos, nesta ordem:

1. **Antes de rodar**: se `artifacts/continuar_fase1.flag` já existir de uma
   execução anterior, apague-o — senão o processo nem chega a esperar.
2. **Inicie em background** (`run_in_background: true`):
   `python -m src.main --regularize <CNPJ> --aguardar-sinal` — acrescente
   `--limit 1` se o usuário não pedir a execução completa (ou se for só
   validação). `<CNPJ>` vem de `$ARGUMENTS`; se vier vazio, pergunte antes de
   rodar.
3. **Avise o usuário**: o Chrome vai abrir (FASE 1 sempre visível, é manual
   por definição; FASE 2+ segue `config.navegador.headless`). Ele precisa
   logar com o certificado digital e trocar o perfil de acesso
   manualmente ("Alterar perfil de acesso" → CNPJ → Alterar). **Nunca
   automatize esse clique** — é bloqueado pela Receita como acesso
   automatizado, confirmado ao vivo (ver `RUNBOOK.md`).
4. **Aguarde a confirmação dele no chat**: precisa ser EXPLÍCITA e
   inequívoca de que a troca de perfil já terminou (algo como "loguei e já
   troquei o perfil", "pronto, perfil trocado"). Uma resposta curta e
   ambígua tipo "siga" ou "ok" NÃO conta — pergunte de volta pra confirmar
   antes de criar o sinal. Já aconteceu ao vivo (2026-08-11) de um "siga"
   ambíguo levar a criar o sinal com o perfil ainda errado, gerando
   relatórios pro CNPJ/CPF errado sem travar nem avisar alto (ver
   `RUNBOOK.md`).
5. **Quando ele confirmar de verdade**: crie o arquivo de sinal
   (`touch artifacts/continuar_fase1.flag` ou equivalente). É esse arquivo
   que `regularize.autenticar_e_trocar_perfil` (branch `aguardar_input=False`)
   está esperando aparecer — isso desbloqueia a FASE 1 sem precisar de Enter
   em stdin nenhum. O processo mesmo apaga o arquivo depois de detectar.
   **Logo depois, leia o trace mais recente e confira o evento
   `perfil_confirmado`** — se `encontrado_na_pagina` vier `false`, avise o
   usuário imediatamente: o perfil não estava certo quando o sinal foi
   criado, e os relatórios dessa execução não são confiáveis.
6. **Acompanhe os logs** até o processo terminar: leia o trace mais recente
   em `artifacts/traces/regularize_*.jsonl` (ordenar por mtime) e o output
   do processo em background. Reporte qualquer evento `DIVERGENCIA` que
   aparecer. Você recebe uma notificação automática quando o processo em
   background termina — não fique fazendo polling agressivo enquanto
   espera; só confira o trace quando o usuário perguntar o status ou quando
   a notificação de conclusão chegar.
7. **Ao final** (sucesso ou falha): leia o trace completo e resuma pro
   usuário — checkpoints atingidos (`checkpoint_3_ok`, `checkpoint_sispar_ok`,
   `checkpoint_capag_ok`), quantidade de PDFs por fase, toda `DIVERGENCIA`
   encontrada, e o caminho dos PDFs em `output/{cnpj_digits}/{DDMMYYYY}/`.

Login por certificado e a troca de perfil de acesso continuam **sempre
manuais** — este comando só orquestra o processo (start, sinal, leitura de
log), nunca substitui essa etapa.
