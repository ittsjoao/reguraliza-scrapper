# SPEC — o que o robô faz

## Objetivo atual

1. Listar certificados digitais já instalados no Windows Certificate Store
   (`Cert:\CurrentUser\My` e `Cert:\LocalMachine\My`) que tenham chave
   privada, EKU "Client Authentication" e não estejam expirados.
2. Se nenhum certificado válido for encontrado, avisar e encerrar.
3. Deixar o usuário escolher **um** certificado via menu de setas no
   terminal (Enter confirma).
4. Abrir um Chrome real via `undetected-chromedriver` — que aplica patches
   anti-detecção pra reduzir captcha/bloqueio do gov.br — com seleção
   automática do certificado escolhido (`--auto-select-certificate-for-urls`
   + policy `AutoSelectCertificateForUrls`, sem popup).
5. Ir para `https://www.gov.br/pt-br`, clicar em "Entrar", aguardar
   carregar, clicar em "Seu certificado digital", aguardar carregar (é
   nessa página que o certificado é de fato apresentado ao servidor).
6. Abrir `https://cav.receita.fazenda.gov.br/ecac/` numa aba nova, já
   autenticado pela sessão SSO.
7. Deixar o navegador aberto para inspeção/continuação manual do usuário.

## Objetivo atual — relatórios do Regularize (PGFN)

Além do login, `python -m src.main --regularize <CNPJ>` gera os relatórios
de dívida ativa da União/FGTS no portal Regularize (PGFN), reaproveitando
a mesma sessão autenticada por certificado do e-CAC. Ver `prompt.md` para
a especificação original completa e `RUNBOOK.md` para as descobertas ao
vivo que corrigiram o que estava documentado ali.

1. **FASE 1 — sempre manual.** Abre uma aba em branco e pausa em
   `input()`; o operador loga no gov.br, abre o e-CAC e troca o "perfil de
   acesso" pro CNPJ informado, tudo manualmente. Não automatizar: o login
   automático por certificado tem uma corrida (pode abrir o próximo passo
   antes do handshake terminar) e a troca de perfil é **bloqueada pela
   Receita como acesso automatizado** quando feita via Selenium (confirmado
   ao vivo, ver `RUNBOOK.md`). Depois do `Enter`, o robô clica em "Dívida
   Ativa da União" → "PGFN - Todos os serviços do Regularize" no e-CAC pra
   entrar no Regularize (nunca navega direto pra URL — deep link a frio às
   vezes redireciona pra `/`).
2. **FASE 2 — Relatório Consolidado.** Marca natureza/situação "Todas",
   gera o relatório, expande todos os detalhamentos, exporta e salva um
   PDF via CDP (`Page.printToPDF` — nunca `page.pdf()`/"Imprimir": ver
   `RUNBOOK.md`).
3. **FASE 3 — Relatórios Detalhados.** Enumera todas as inscrições nas 4
   abas (Tributária, Não Tributária, Previdenciária, FGTS), depois gera um
   PDF detalhado por inscrição, re-navegando a cada uma. Loga cada
   elemento clicado e valida a contagem final de PDFs gerados contra o
   total de inscrições enumeradas (checkpoint 3).
4. **FASE 4 — Parcelamentos (SISPAR).** No mesmo navegador da FASE 2+ (a
   sessão do Regularize já autenticado dá acesso ao SISPAR via token na
   URL — sem novo login/troca de perfil), coleta a lista de negociações
   solicitadas e gera um PDF por parcelamento (`PARCELAMENTO-{numero}.pdf`),
   expandindo todos os `fieldset.ui-fieldset-toggleable` (aguarda o
   placeholder AJAX "Consultando X..." ser substituído, nunca sleep fixo).
   Erro num parcelamento não aborta o lote — loga e segue pro próximo. Ver
   `docs/imp/capag.md` para a especificação original.
5. **FASE 5 — CAPAG.** Consulta a capacidade de pagamento individual e
   salva `CAPAG_{DDMMYYYY}-{HHMM}.pdf`; se a consulta vier indisponível
   (ex.: contribuinte omisso), captura o texto de indisponibilidade mesmo
   assim, sem quebrar o fluxo.
6. Toda ação fica logada em `artifacts/traces/regularize_*.jsonl`
   (estruturado, um evento por linha) — inclui divergências, não só
   sucesso.
7. PDFs saem em `./output/{cnpj_digits}/{DDMMYYYY}/`.

## Fora de escopo (por ora)

- Login automatizado dentro do e-CAC (seleção de perfil, captcha, etc.) e
  a troca de perfil de acesso — sempre manual, ver acima.
- Download ou scraping de documentos do e-CAC (fora do fluxo do
  Regularize, que é um sistema separado da PGFN).
- Importar/instalar certificados no Windows — o robô só lista o que já está
  instalado, nunca grava nada no Certificate Store.
- Suporte a NFS-e — esse projeto substitui aquele fluxo pelo e-CAC.

## Pré-requisito de ambiente

- O certificado digital precisa estar instalado no Windows Certificate Store
  do usuário (ou da máquina) antes de rodar o robô.
- Google Chrome precisa estar instalado na máquina — `undetected-chromedriver`
  patcheia o Chrome já instalado, não baixa um Chromium próprio.
- **NUNCA rode o robô inteiro como Administrador** — Chrome/Selenium quebra
  ("chrome not reachable") quando o processo que abre o navegador está
  elevado. A gravação da policy `AutoSelectCertificateForUrls` em `HKLM`
  (que exige admin) roda num processo PowerShell separado que pede UAC só
  para aquele instante — aceite o prompt quando aparecer. Sem aceitar, o
  robô ainda funciona, só depende inteiramente da flag de linha de comando.
