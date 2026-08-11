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
