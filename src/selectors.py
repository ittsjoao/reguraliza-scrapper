"""Único lugar com seletores CSS/XPath do site."""

URL_GOV_BR = "https://www.gov.br/pt-br"

# botão "Entrar" fica dentro do Shadow DOM do custom element <barra-govbr>
# (web component carregado de barra.sistema.gov.br) — precisa achar o host
# e entrar em .shadow_root antes de procurar BTN_ENTRAR, um find_element
# comum na página não alcança.
HOST_BARRA_GOVBR = "barra-govbr"
BTN_ENTRAR = ".br-sign-in"

# depois do clique em Entrar, cai em sso.acesso.gov.br/login — esse botão
# já está em DOM normal (sem shadow root).
BTN_LOGIN_CERTIFICADO = "#login-certificate"

# --- Regularize (PGFN) — consulta de dívida ativa e relatórios ---
# Ver prompt.md e RUNBOOK.md para o fluxo completo e para as descobertas
# da FASE 0 (confirmadas ao vivo em 2026-08-10, não só nas fixtures em
# docs/pag_exemples/).
URL_ECAC = "https://cav.receita.fazenda.gov.br/ecac/"
URL_REGULARIZE = "https://www.regularize.pgfn.gov.br/"
URL_REGULARIZE_CONSULTA_DIVIDAS = "https://www.regularize.pgfn.gov.br/consultaDividas"

# A troca de "perfil de acesso" (representar outro CNPJ) acontece no e-CAC,
# não no Regularize — ver RUNBOOK.md. #txtNIPapel2 é especificamente o
# campo "Procurador de pessoa jurídica - CNPJ" (dos 3 que existem no modal;
# #txtNIPapel = Responsável Legal, #txtNIPapel1 = Procurador CPF). A
# Receita FEDERAL bloqueia esse clique quando feito via automação
# ("acesso foi bloqueado por possuir atributos que o caracteriza como um
# acesso automatizado") — por isso esse passo é SEMPRE manual (ver
# fluxo.py: pausa em input() antes de continuar).
XPATH_BTN_ALTERAR_PERFIL_ECAC = '//*[contains(text(), "Alterar perfil de acesso")]'
INPUT_CNPJ_PERFIL = "#txtNIPapel2"
BTN_ALTERAR_PERFIL = 'input.submit[value="Alterar"]'
# os 3 botões "Alterar" não têm id nem fieldset ancestor comum — o certo
# pra #txtNIPapel2 é o primeiro que aparece DEPOIS dele no DOM (ver
# RUNBOOK.md).
XPATH_BTN_ALTERAR_APOS_CNPJ = '//input[@id="txtNIPapel2"]/following::input[@value="Alterar"][1]'

# Caminho pra entrar no Regularize a partir do e-CAC já autenticado — em
# vez de navegar direto pra URL_REGULARIZE_CONSULTA_DIVIDAS (a SPA às
# vezes redireciona de volta pra '/' num carregamento a frio direto),
# clicar em "Dívida Ativa da União" (menu do e-CAC) e depois no link do
# Regularize estabelece a sessão pelo caminho que um usuário real usaria.
XPATH_BTN_DIVIDA_ATIVA_UNIAO_ECAC = '//*[contains(text(), "Dívida Ativa da União")]'
XPATH_LINK_REGULARIZE_TODOS_SERVICOS = '//*[contains(text(), "PGFN - Todos os serviços do Regularize")]'

BTN_RELATORIO_CONSOLIDADO = 'button[routerlink="/consultaDividas/relatorio"]'
CHECK_NATUREZA_TODAS = "#natTodosCheck"
CHECK_SITUACAO_TODAS = "#sitTodosCheck"
XPATH_BTN_GERAR_RELATORIO = '//button[contains(., "Gerar Relatório")]'
XPATH_BTN_EXPORTAR = '//button[contains(., "Exportar")]'
XPATH_BTN_IMPRIMIR = '//button[contains(., "Imprimir")]'
IMG_EXPANDIR_TODAS_INSCRICOES = 'img[alt="Exibir o detalhamento de todas as inscrições"]'
# Só no Relatório Consolidado (FASE 2): grupos de dívida "Extinta" ficam
# num painel próprio (legend clicável), separado do
# IMG_EXPANDIR_TODAS_INSCRICOES — precisa clicar nele também antes de
# exportar, senão essas inscrições saem de fora do PDF.
XPATH_LEGENDA_EXTINTA = '//legend[contains(normalize-space(.), "Extinta")]'

ABAS = {
    "tributaria": "aba_TRIBUTARIA_DEMAIS_DEBITOS-link",
    "nao_tributaria": "aba_NAO_TRIBUTARIA-link",
    "previdenciaria": "aba_TRIBUTARIA_PREVIDENCIARIA-link",
    "fgts": "aba_FGTS-link",
}
LINHA_INSCRICAO = 'tr[id^="inscricao_"]'
LINK_DETALHAR = 'a[title="Detalhar"]'
SELECT_PAGE_SIZE = "select.form-select"
OPTION_TODAS = 'option[value="0"]'

XPATH_ABA_RELATORIO_DETALHADO = '//span[contains(., "Relatório detalhado")]'
CHECK_TODOS_DETALHADO = "#todosCheck"
XPATH_BTN_GERAR_RELATORIO_DETALHADO = '//button[contains(., "Gerar relatório detalhado")]'
IMG_EXPANDIR_DEBITO = 'img[alt="Exibir o detalhamento deste débito"]'

SPINNER = "app-spinner"

# --- SISPAR (PGFN) — parcelamentos e CAPAG (ver docs/imp/capag.md) ---
# App é JSF/PrimeFaces clássico (IDs j_idt* dinâmicos entre renders) — só
# seletores estáveis aqui: texto/classe, nunca id$=/id*= com sufixo j_idt.
# Alcançado a partir da sessão já autenticada do Regularize (sem login/troca
# de perfil nova — reaproveita a mesma sessão via token na URL).
URL_SISPAR = "https://www.regularize.pgfn.gov.br/sispar/sisparnet"
# confirmado ao vivo em 2026-08-11 (docs/pag_exemples/Regularize_consultar.htm
# + home_qAYj.htm): a página embute o app Angular do simulador SISPAR
# (outro domínio, pro-frontend-simulador-sispar.estaleiro.serpro.gov.br)
# dentro de um <iframe id="sisparFrame"> — os cards ("CONSULTAR",
# "SIMULAR/NEGOCIAR", "CAPACIDADE DE PAGAMENTO" etc.) vivem DENTRO desse
# iframe, nunca no documento principal. Sempre trocar de frame
# (EC.frame_to_be_available_and_switch_to_it) antes de procurar qualquer
# um deles.
IFRAME_SISPAR = "#sisparFrame"
XPATH_CARD_CONSULTAR = '//*[contains(@class, "place-info-box-text") and normalize-space(text())="CONSULTAR"]'
IMG_CARD_CONSULTAR = 'img[alt="base"][src*="consultar"]'
# botão "Continuar" (dentro do mesmo iframe, na tela seguinte ao clique no
# card) — ainda sem fixture local, texto/classe exatos não confirmados.
XPATH_BTN_CONTINUAR_SISPAR = '//button[contains(@class, "btn-primary") and contains(normalize-space(.), "Continuar")]'

# a partir daqui (nova guia, sisparInternet/*.jsf) é JSF/PrimeFaces clássico —
# confirmado contra docs/pag_exemples/parcelamentos.htm e
# parcelamento_consolidado.htm.
TBODY_LISTA_PARCELAMENTOS = 'tbody[id$="idListaParcelamentos_data"]'
TR_LINHA_PARCELAMENTO = "tr.conteudoGrid"
XPATH_BTN_CONSULTA_PARCELAMENTO = '//*[contains(@class, "ui-button-text") and normalize-space(text())="Consulta"]'
XPATH_BTN_RETORNAR_PARCELAMENTO = '//*[contains(@class, "ui-button-text") and normalize-space(text())="Retornar"]'

# confirmado ao vivo em 2026-08-11: aviso de cookies do PGFN aparece numa
# página nova a cada navegação (recarga completa, sem SPA) — sobrava no
# texto extraído dos PDFs de CAPAG. "Permitir" é o botão que aceita.
XPATH_BTN_COOKIE_PERMITIR = '//button[contains(normalize-space(.), "Permitir")] | //a[contains(normalize-space(.), "Permitir")]'

# diálogo global "Aguarde / Solicitação em processamento..." do
# PrimeFaces (confirmado contra parcelamentos.htm E
# parcelamento_consolidado.htm) — fica no DOM sempre (display:block), só
# a visibilidade muda durante um AJAX; mesmo padrão do app-spinner do
# Angular. Sem esperar isso sumir, um print pode capturar essa tela.
STATUS_AGUARDE_JSF = "#statusAguarde"

FIELDSET_TOGGLEAVEL = "fieldset.ui-fieldset-toggleable"
LEGENDA_FIELDSET = ".ui-fieldset-legend"
TOGGLER_COLAPSADO = ".ui-fieldset-toggler.ui-icon-plusthick"

# CAPAG — sem fixture local (docs/imp/capag.md descreve, não há .htm salvo);
# validar contra a página real antes de confiar cegamente.
URL_SISPAR_CAPAG = "https://sisparnet.pgfn.fazenda.gov.br/sisparInternet/consultarCapag.jsf"
XPATH_BTN_PESQUISAR_CAPAG = '//*[contains(@class, "ui-button-text") and normalize-space(text())="Pesquisar"]'
TEXTO_LEGENDA_CAPAG_VALORES = "Valores para cálculo da capacidade de pagamento individual"
