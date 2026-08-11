"""Geração dos relatórios de dívida ativa no Regularize (PGFN): o
Relatório Consolidado (FASE 2) e os Relatórios Detalhados por inscrição,
em todas as abas (FASE 3). Ver prompt.md para a especificação completa e
RUNBOOK.md para as descobertas da FASE 0 (ex.: a troca de perfil de
acesso acontece no e-CAC, não no Regularize, e é sempre manual porque a
Receita bloqueia esse clique quando automatizado).
"""

import base64
import concurrent.futures
import json
import time
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from selenium.common.exceptions import (
    ElementClickInterceptedException,
    ElementNotInteractableException,
    StaleElementReferenceException,
    TimeoutException,
)
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.select import Select
from selenium.webdriver.support.ui import WebDriverWait

from src import selectors

_ERROS_CLIQUE_TRANSITORIOS = (ElementClickInterceptedException, ElementNotInteractableException)
_ERROS_ELEMENTO_MUDOU = (*_ERROS_CLIQUE_TRANSITORIOS, StaleElementReferenceException)

_EXECUTOR = concurrent.futures.ThreadPoolExecutor(max_workers=2)


def _com_timeout(func, timeout_s: float, *args, **kwargs):
    """As esperas explícitas (WebDriverWait) já têm timeout, mas um
    comando individual do Selenium (click, find_element) pode travar
    indefinidamente se a aba estiver num estado quebrado — a chamada HTTP
    pro chromedriver nunca retorna. Roda em thread separada e desiste
    depois de timeout_s, mesmo que a thread original fique pra trás."""
    futuro = _EXECUTOR.submit(func, *args, **kwargs)
    try:
        return futuro.result(timeout=timeout_s)
    except concurrent.futures.TimeoutError:
        raise TimeoutException(f"comando não respondeu em {timeout_s}s — aba provavelmente travada.")

FUSO_SP = ZoneInfo("America/Sao_Paulo")


class Logger:
    """Loga cada passo em artifacts/traces/*.jsonl e no console — o
    usuário pediu explicitamente log de todo elemento e validação de
    contagens."""

    def __init__(self, caminho: Path):
        caminho.parent.mkdir(parents=True, exist_ok=True)
        self._arquivo = open(caminho, "w", encoding="utf-8")

    def log(self, evento: str, **dados) -> None:
        registro = {"t": datetime.now(FUSO_SP).isoformat(), "evento": evento, **dados}
        linha = json.dumps(registro, ensure_ascii=False)
        print(linha)
        self._arquivo.write(linha + "\n")
        self._arquivo.flush()

    def fechar(self) -> None:
        self._arquivo.close()


def _timestamp() -> tuple[str, str]:
    agora = datetime.now(FUSO_SP)
    return agora.strftime("%d%m%Y"), agora.strftime("%H%M")


def output_dir(cnpj: str) -> Path:
    digitos = "".join(c for c in cnpj if c.isdigit())
    ddmmyyyy, _ = _timestamp()
    caminho = Path("output") / digitos / ddmmyyyy
    caminho.mkdir(parents=True, exist_ok=True)
    return caminho


def _pagina_carregada(driver) -> bool:
    return driver.execute_script("return document.readyState") == "complete"


def esperar_carregar(driver, timeout_s: float) -> None:
    WebDriverWait(driver, timeout_s).until(_pagina_carregada)


def ir_para_consulta_dividas(driver, timeout_s: float, logger: Logger) -> None:
    """driver.get direto em /consultaDividas ocasionalmente é redirecionado
    de volta pra '/' (a SPA bota uma guarda de rota que às vezes não
    reconhece a sessão a tempo num carregamento a frio) — tenta de novo em
    vez de seguir adiante numa página errada."""
    for tentativa in range(3):
        driver.get(selectors.URL_REGULARIZE_CONSULTA_DIVIDAS)
        try:
            WebDriverWait(driver, timeout_s).until(
                lambda d: "/consultaDividas" in d.current_url
            )
            esperar_spinner_sumir(driver, timeout_s)
            return
        except TimeoutException:
            logger.log(
                "DIVERGENCIA",
                detalhe=f"driver.get(/consultaDividas) voltou pra '{driver.current_url}' (tentativa {tentativa + 1}/3).",
            )
    raise TimeoutException("não consegui chegar em /consultaDividas depois de 3 tentativas.")


def esperar_spinner_sumir(driver, timeout_s: float) -> None:
    """app-spinner fica no DOM (escondido) mesmo quando não está
    carregando nada — contar a existência do elemento nunca chega a zero.
    O que importa é nenhum estar VISÍVEL."""

    def nenhum_spinner_visivel(d):
        return not any(
            el.is_displayed() for el in d.find_elements(By.CSS_SELECTOR, selectors.SPINNER)
        )

    WebDriverWait(driver, timeout_s).until(nenhum_spinner_visivel)


def _url_da_aba(driver, handle: str) -> str:
    atual = driver.current_window_handle
    driver.switch_to.window(handle)
    url = driver.current_url
    driver.switch_to.window(atual)
    return url


def esperar_elemento(driver, by, valor: str, timeout_s: float):
    """Navegação dentro do Angular (routerLink) não recarrega a página —
    document.readyState já está 'complete' antes da rota trocar de fato.
    Esperar por um elemento concreto da PRÓXIMA tela é a âncora real."""
    return WebDriverWait(driver, timeout_s).until(
        EC.presence_of_element_located((by, valor))
    )


def _clicar(driver, elemento) -> None:
    """Clique normal; se algo (banner, widget flutuante, header sticky,
    animação de accordion em andamento) impedir o clique nativo, cai pra
    clique via JS depois de rolar o elemento pro centro da tela."""
    try:
        elemento.click()
    except _ERROS_CLIQUE_TRANSITORIOS:
        driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", elemento)
        driver.execute_script("arguments[0].click();", elemento)


def salvar_pdf(driver, caminho: Path, logger: Logger) -> None:
    driver.execute_cdp_cmd("Emulation.setEmulatedMedia", {"media": "print"})
    resultado = driver.execute_cdp_cmd("Page.printToPDF", {"printBackground": True})
    dados = base64.b64decode(resultado["data"])
    caminho.parent.mkdir(parents=True, exist_ok=True)
    caminho.write_bytes(dados)
    logger.log("pdf_salvo", caminho=str(caminho), bytes=len(dados))


def autenticar_e_trocar_perfil(driver, cnpj: str, timeout_s: float, logger: Logger) -> list[dict]:
    """FASE 1 — inteiramente manual, de propósito: o login automático por
    certificado (fluxo._logar_via_govbr) tem uma corrida (o click no
    certificado pode não terminar o handshake antes do próximo passo) e a
    troca de perfil no e-CAC é bloqueada pela Receita quando automatizada
    (ver RUNBOOK.md). Em vez de tentar automatizar e falhar dos dois
    jeitos, usa a aba padrão (já aberta em branco por
    fluxo.abrir_navegador_com_certificado) e deixa o operador fazer tudo à
    mão — sem abrir uma segunda aba em branco desnecessária.

    Depois de confirmado, captura os cookies da sessão (`driver.
    get_cookies()`) e os retorna — quem chamar fecha este driver e abre um
    novo, headless, com `fluxo.abrir_navegador_com_cookies` (ver
    RUNBOOK.md). Esta função NÃO navega mais pro Regularize; isso agora é
    responsabilidade de quem chamar, no driver headless."""
    print(
        "\nFaça manualmente:\n"
        f"  1. Vá para {selectors.URL_ECAC} e logue com o certificado digital.\n"
        f'  2. Clique em "Alterar perfil de acesso".\n'
        f'  3. No campo "Procurador de pessoa jurídica - CNPJ", digite {cnpj}.\n'
        '  4. Clique em "Alterar".\n'
        "  (Login e troca de perfil são sempre manuais — automatizar o clique "
        "do certificado tem corrida, e a troca de perfil é bloqueada como "
        "acesso automatizado pela Receita.)\n"
    )
    input("Pressione Enter aqui depois de confirmar a troca de perfil... ")

    aba_ecac = next(
        (h for h in driver.window_handles if _url_da_aba(driver, h).startswith(selectors.URL_ECAC)),
        None,
    )
    if aba_ecac is None:
        logger.log(
            "DIVERGENCIA",
            detalhe="nenhuma aba está no e-CAC depois do Enter — confira se o login foi feito.",
        )
    else:
        driver.switch_to.window(aba_ecac)

    texto_pagina = driver.find_element(By.TAG_NAME, "body").text
    digitos_cnpj = "".join(c for c in cnpj if c.isdigit())
    perfil_confere = digitos_cnpj in "".join(c for c in texto_pagina if c.isdigit())
    logger.log("perfil_confirmado", cnpj=cnpj, encontrado_na_pagina=perfil_confere)
    if not perfil_confere:
        logger.log(
            "DIVERGENCIA",
            detalhe=f"CNPJ {cnpj} não aparece no texto da página do e-CAC após a troca de perfil — confira manualmente.",
        )

    cookies = driver.get_cookies()
    logger.log("cookies_capturados", total=len(cookies))
    return cookies


def confirmar_sessao_headless_autenticada(driver, timeout_s: float, logger: Logger) -> None:
    """Confere se a sessão herdada via cookies (ver RUNBOOK.md) realmente
    autenticou antes de seguir — sem isso, uma sessão expirada/presa a
    outro IP geraria relatórios vazios ou tela de login em vez de PDFs."""
    try:
        esperar_elemento(driver, By.XPATH, selectors.XPATH_BTN_ALTERAR_PERFIL_ECAC, timeout_s)
    except TimeoutException as erro:
        raise RuntimeError(
            "Sessão headless não autenticou depois de injetar os cookies — "
            "capturados agora mesmo na FASE 1, mas podem já ter expirado ou "
            "estar presos a outro IP (cookies TS*, ver RUNBOOK.md)."
        ) from erro
    logger.log("sessao_headless_autenticada")


def entrar_no_regularize_via_ecac(driver, timeout_s: float, logger: Logger) -> None:
    """A partir do e-CAC já autenticado, clica em "Dívida Ativa da União"
    e depois em "PGFN - Todos os serviços do Regularize" — em vez de
    navegar direto pra URL do Regularize, que às vezes redireciona de
    volta pra '/' num carregamento a frio (ver ir_para_consulta_dividas)."""
    _clicar(driver, driver.find_element(By.XPATH, selectors.XPATH_BTN_DIVIDA_ATIVA_UNIAO_ECAC))
    esperar_elemento(driver, By.XPATH, selectors.XPATH_LINK_REGULARIZE_TODOS_SERVICOS, timeout_s)

    handles_antes = set(driver.window_handles)
    _clicar(driver, driver.find_element(By.XPATH, selectors.XPATH_LINK_REGULARIZE_TODOS_SERVICOS))

    WebDriverWait(driver, timeout_s).until(
        lambda d: set(d.window_handles) - handles_antes
        or "regularize.pgfn.gov.br" in d.current_url
    )
    novas = list(set(driver.window_handles) - handles_antes)
    if novas:
        driver.switch_to.window(novas[0])
    esperar_carregar(driver, timeout_s)
    logger.log("regularize_aberto_via_ecac", url=driver.current_url)


def _clicar_todos_expandir(driver, seletor_css: str, logger: Logger, rotulo: str) -> int:
    """Clica em cada imagem 'expandir' um a um, aguardando cada uma sair
    da lista (o alt muda pra 'Ocultar...' e o seletor de 'Exibir...' já
    não bate mais nela) antes de ir pra próxima. Elementos podem ficar
    momentaneamente não-clicáveis durante a animação do accordion — tenta
    de novo com uma lista fresca em vez de desistir na primeira falha."""
    total = 0
    falhas_seguidas = 0
    while True:
        imagens = driver.find_elements(By.CSS_SELECTOR, seletor_css)
        if not imagens:
            break
        if falhas_seguidas >= 5:
            logger.log(
                "DIVERGENCIA",
                detalhe=f"parei de expandir '{rotulo}' após 5 falhas seguidas; restam {len(imagens)}.",
            )
            break

        imagem = imagens[0]
        try:
            _clicar(driver, imagem)
            try:
                WebDriverWait(driver, 15).until(EC.staleness_of(imagem))
            except Exception:
                WebDriverWait(driver, 15).until(
                    lambda d: len(d.find_elements(By.CSS_SELECTOR, seletor_css)) < len(imagens)
                )
            # a posição de cada painel é calculada no momento do clique —
            # clicar no próximo antes da transição/reflow deste terminar
            # faz o próximo painel calcular a posição com a altura ainda
            # errada dos anteriores, sobrepondo texto no PDF final.
            try:
                WebDriverWait(driver, 5).until(
                    lambda d: d.execute_script("return document.getAnimations().length") == 0
                )
            except TimeoutException:
                pass
        except _ERROS_ELEMENTO_MUDOU:
            falhas_seguidas += 1
            time.sleep(1)
            continue

        falhas_seguidas = 0
        total += 1
        logger.log("expandido", tipo=rotulo, indice=total)
    return total


def _clicar_legendas_extintas(driver, logger: Logger) -> int:
    """Só no Relatório Consolidado: grupos de dívida "Extinta" ficam num
    painel próprio (legend clicável, ver selectors.XPATH_LEGENDA_EXTINTA),
    separado do IMG_EXPANDIR_TODAS_INSCRICOES — clica em cada um antes de
    seguir, senão essas inscrições saem de fora do PDF. Passe único (a
    legend não some do DOM ao clicar, só alterna o painel — diferente de
    _clicar_todos_expandir, que depende do elemento sumir da lista)."""
    legendas = driver.find_elements(By.XPATH, selectors.XPATH_LEGENDA_EXTINTA)
    for legenda in legendas:
        _clicar(driver, legenda)
        try:
            WebDriverWait(driver, 5).until(
                lambda d: d.execute_script("return document.getAnimations().length") == 0
            )
        except TimeoutException:
            pass
    logger.log("legendas_extintas_clicadas", total=len(legendas))
    return len(legendas)


def gerar_relatorio_consolidado(driver, cnpj: str, timeout_s: float, logger: Logger) -> Path:
    """FASE 2 — Relatório Consolidado (A)."""
    ir_para_consulta_dividas(driver, timeout_s, logger)

    _clicar(driver, driver.find_element(By.CSS_SELECTOR, selectors.BTN_RELATORIO_CONSOLIDADO))
    esperar_elemento(driver, By.CSS_SELECTOR, selectors.CHECK_NATUREZA_TODAS, timeout_s)
    logger.log("relatorio_consolidado_aberto", url=driver.current_url)

    for seletor, nome in (
        (selectors.CHECK_NATUREZA_TODAS, "natureza_todas"),
        (selectors.CHECK_SITUACAO_TODAS, "situacao_todas"),
    ):
        checkbox = driver.find_element(By.CSS_SELECTOR, seletor)
        if not checkbox.is_selected():
            _clicar(driver, checkbox)
        logger.log("checkbox_marcado", nome=nome)

    _clicar(driver, driver.find_element(By.XPATH, selectors.XPATH_BTN_GERAR_RELATORIO))
    esperar_spinner_sumir(driver, timeout_s)
    # a espera por "algum fieldset" não basta: o formulário "Personalizar
    # Relatório" já é um fieldset presente ANTES do relatório carregar. O
    # relatório em si (com os botões de expandir/Exportar) pode continuar
    # renderizando progressivamente por seção — espera a âncora real.
    WebDriverWait(driver, timeout_s).until(
        lambda d: d.find_elements(By.CSS_SELECTOR, selectors.IMG_EXPANDIR_TODAS_INSCRICOES)
        or d.find_elements(By.XPATH, selectors.XPATH_BTN_EXPORTAR)
    )
    total_fieldsets = len(driver.find_elements(By.TAG_NAME, "fieldset"))
    logger.log("relatorio_gerado", total_fieldsets=total_fieldsets)

    _clicar_legendas_extintas(driver, logger)

    total_expandido = _clicar_todos_expandir(
        driver, selectors.IMG_EXPANDIR_TODAS_INSCRICOES, logger, "todas_inscricoes"
    )
    logger.log("expansao_concluida", total_secoes_expandidas=total_expandido)

    # "Imprimir" dispara window.print() nativo do Chrome (abre uma aba
    # chrome://print/ que BLOQUEIA a aba original via JS até ser
    # fechada) — não clicamos nele; a captura via CDP Page.printToPDF não
    # depende dessa etapa, só do conteúdo já expandido na página.
    _clicar(driver, driver.find_element(By.XPATH, selectors.XPATH_BTN_EXPORTAR))
    esperar_elemento(driver, By.XPATH, selectors.XPATH_BTN_IMPRIMIR, timeout_s)

    ddmmyyyy, hhmm = _timestamp()
    caminho = output_dir(cnpj) / f"Regularize_Relatorio_Divida_Ativa_{ddmmyyyy}-{hhmm}.pdf"
    salvar_pdf(driver, caminho, logger)
    return caminho


def _setar_page_size_todas(driver, timeout_s: float, logger: Logger) -> None:
    """Seta cada select.form-select VISÍVEL pra 'Todas' (value=0), um de
    cada vez — reconsulta a lista a cada iteração porque a página pode
    re-renderizar depois de cada troca. Usa Select.select_by_value (dispara
    o evento 'change' de verdade) — clicar direto na <option> sem abrir o
    <select> não atualiza o binding do Angular. Abas inativas deixam seus
    selects no DOM só escondidos (não removidos) — só os visíveis contam."""
    processados = 0
    tentativas_sem_progresso = 0
    while True:
        selects = [
            sel
            for sel in driver.find_elements(By.CSS_SELECTOR, selectors.SELECT_PAGE_SIZE)
            if sel.is_displayed()
        ]
        pendente = next((sel for sel in selects if sel.get_attribute("value") != "0"), None)
        if pendente is None:
            break
        if tentativas_sem_progresso >= 5:
            logger.log(
                "DIVERGENCIA",
                detalhe=f"não consegui setar 'Todas' em {len(selects)} select(s) após várias tentativas.",
            )
            break
        try:
            Select(pendente).select_by_value("0")
            esperar_spinner_sumir(driver, timeout_s)
        except _ERROS_ELEMENTO_MUDOU:
            tentativas_sem_progresso += 1
            time.sleep(1)
            continue
        tentativas_sem_progresso = 0
        processados += 1
    logger.log("page_size_ajustado", quantidade_selects=processados)


def enumerar_inscricoes(driver, timeout_s: float, logger: Logger) -> dict[str, list[str]]:
    """FASE 3, Passada 3.1 — enumerar todas as inscrições, de todos os
    grupos, nas 4 abas."""
    ir_para_consulta_dividas(driver, timeout_s, logger)

    enumeracao: dict[str, list[str]] = {}
    for chave, id_aba in selectors.ABAS.items():
        elementos_aba = driver.find_elements(By.ID, id_aba)
        if not elementos_aba:
            logger.log("DIVERGENCIA", detalhe=f"aba '{chave}' (#{id_aba}) não encontrada.")
            enumeracao[chave] = []
            continue

        _clicar(driver, elementos_aba[0])
        esperar_spinner_sumir(driver, timeout_s)
        _setar_page_size_todas(driver, timeout_s, logger)

        # abas inativas deixam suas linhas no DOM só escondidas (mesma
        # razão do app-spinner) — só as visíveis pertencem à aba atual.
        linhas = [
            el
            for el in driver.find_elements(By.CSS_SELECTOR, selectors.LINHA_INSCRICAO)
            if el.is_displayed()
        ]
        ids = list(dict.fromkeys(el.get_attribute("id") for el in linhas))
        enumeracao[chave] = ids
        logger.log("aba_enumerada", aba=chave, total_inscricoes=len(ids))

    total_geral = sum(len(v) for v in enumeracao.values())
    logger.log("enumeracao_concluida", total_geral=total_geral, por_aba={k: len(v) for k, v in enumeracao.items()})
    return enumeracao


def _reabrir_aba_consulta_dividas(driver, timeout_s: float, logger: Logger) -> None:
    """Depois de muitas navegações seguidas, a aba do Regularize às vezes
    degrada (a página para de carregar de verdade — fica presa numa tela
    intermediária/"em branco" mesmo com o DOM tecnicamente presente).
    Fecha a aba travada e abre uma nova do zero em /consultaDividas."""
    aba_antiga = driver.current_window_handle
    handles_antes = set(driver.window_handles)
    driver.execute_cdp_cmd("Target.createTarget", {"url": "about:blank"})
    novas = list(set(driver.window_handles) - handles_antes)
    aba_nova = novas[0] if novas else next(h for h in driver.window_handles if h != aba_antiga)

    driver.switch_to.window(aba_antiga)
    driver.close()
    driver.switch_to.window(aba_nova)
    ir_para_consulta_dividas(driver, timeout_s, logger)
    logger.log("aba_reaberta", motivo="página não avançou dentro do timeout")


def _gerar_relatorio_detalhado_de(
    driver, tab_key: str, inscricao_dom_id: str, cnpj: str, timeout_s: float, logger: Logger
) -> Path:
    """Tenta até 2 vezes: se qualquer espera der timeout (página que
    parou de carregar depois de muitas navegações seguidas), fecha a aba
    e abre outra nova antes de tentar de novo."""
    ultimo_erro = None
    for tentativa in range(2):
        logger.log(
            "tentativa_relatorio_detalhado",
            inscricao=inscricao_dom_id,
            tentativa=f"{tentativa + 1}/2",
            timeout_max_s=timeout_s * 2,
        )
        try:
            return _com_timeout(
                _tentar_gerar_relatorio_detalhado_de,
                timeout_s * 2,
                driver,
                tab_key,
                inscricao_dom_id,
                cnpj,
                timeout_s,
                logger,
            )
        except (TimeoutException, StaleElementReferenceException) as erro:
            ultimo_erro = erro
            logger.log(
                "DIVERGENCIA",
                detalhe=f"falha gerando relatório de {inscricao_dom_id} (tentativa {tentativa + 1}/2): {erro}",
            )
            _reabrir_aba_consulta_dividas(driver, timeout_s, logger)
    raise ultimo_erro


def _tentar_gerar_relatorio_detalhado_de(
    driver, tab_key: str, inscricao_dom_id: str, cnpj: str, timeout_s: float, logger: Logger
) -> Path:
    inscricao_id = inscricao_dom_id.removeprefix("inscricao_")

    ir_para_consulta_dividas(driver, timeout_s, logger)
    _clicar(driver, driver.find_element(By.ID, selectors.ABAS[tab_key]))
    esperar_spinner_sumir(driver, timeout_s)
    _setar_page_size_todas(driver, timeout_s, logger)

    # a linha pode re-renderizar (stale) entre localizá-la e clicar no link
    # de dentro dela — refaz a busca do zero em cada tentativa, não só o
    # clique, já que o problema é a referência à <tr>, não ao <a>.
    for tentativa in range(3):
        try:
            linha = driver.find_element(By.ID, inscricao_dom_id)
            link_detalhar = linha.find_element(By.CSS_SELECTOR, selectors.LINK_DETALHAR)
            _clicar(driver, link_detalhar)
            break
        except StaleElementReferenceException:
            if tentativa == 2:
                raise
            time.sleep(0.5)
    esperar_elemento(driver, By.XPATH, selectors.XPATH_ABA_RELATORIO_DETALHADO, timeout_s)

    _clicar(driver, driver.find_element(By.XPATH, selectors.XPATH_ABA_RELATORIO_DETALHADO))
    esperar_elemento(driver, By.CSS_SELECTOR, selectors.CHECK_TODOS_DETALHADO, timeout_s)

    checkbox_todos = driver.find_element(By.CSS_SELECTOR, selectors.CHECK_TODOS_DETALHADO)
    if not checkbox_todos.is_selected():
        _clicar(driver, checkbox_todos)

    fieldsets_antes = len(driver.find_elements(By.TAG_NAME, "fieldset"))
    _clicar(driver, driver.find_element(By.XPATH, selectors.XPATH_BTN_GERAR_RELATORIO_DETALHADO))
    esperar_spinner_sumir(driver, timeout_s)
    WebDriverWait(driver, timeout_s).until(
        lambda d: len(d.find_elements(By.TAG_NAME, "fieldset")) > fieldsets_antes
    )

    total_expandido = _clicar_todos_expandir(
        driver, selectors.IMG_EXPANDIR_DEBITO, logger, "debito"
    )
    logger.log("debitos_expandidos", inscricao=inscricao_id, total=total_expandido)

    # o botão "Imprimir" só fica presente/estável depois que a página
    # termina de renderizar os débitos expandidos — esperar por ele em vez
    # de um tempo fixo evita capturar o PDF com a transição do accordion
    # ainda em andamento (conteúdo sobreposto, visto com poucos débitos
    # que terminam de clicar rápido demais).
    esperar_elemento(driver, By.XPATH, selectors.XPATH_BTN_IMPRIMIR, timeout_s)

    ddmmyyyy, _ = _timestamp()
    caminho = output_dir(cnpj) / f"Regularize_{inscricao_id}_{ddmmyyyy}.pdf"
    salvar_pdf(driver, caminho, logger)
    return caminho


def gerar_relatorios_detalhados(
    driver, enumeracao: dict[str, list[str]], cnpj: str, timeout_s: float, logger: Logger
) -> list[Path]:
    """FASE 3, Passada 3.2 — processa cada (aba, inscrição), re-navegando
    a cada uma."""
    total_esperado = sum(len(v) for v in enumeracao.values())
    caminhos: list[Path] = []

    for tab_key, ids in enumeracao.items():
        for inscricao_dom_id in ids:
            try:
                caminho = _gerar_relatorio_detalhado_de(
                    driver, tab_key, inscricao_dom_id, cnpj, timeout_s, logger
                )
                caminhos.append(caminho)
            except Exception as erro:
                logger.log(
                    "DIVERGENCIA",
                    detalhe=f"falhou ao gerar relatório de {inscricao_dom_id} (aba {tab_key}): {erro}",
                )
                continue
            logger.log(
                "progresso_detalhados",
                gerados=len(caminhos),
                total_esperado=total_esperado,
            )

    if len(caminhos) != total_esperado:
        logger.log(
            "DIVERGENCIA",
            detalhe=(
                f"checkpoint 3 falhou: {len(caminhos)} PDFs gerados, "
                f"{total_esperado} inscrições enumeradas."
            ),
        )
    else:
        logger.log("checkpoint_3_ok", total=len(caminhos))

    return caminhos
