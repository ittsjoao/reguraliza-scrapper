"""Os passos: listar certificados do Windows Certificate Store, deixar o
usuário escolher um via terminal (setas + Enter) e abrir o navegador
(undetected-chromedriver) com esse certificado selecionado automaticamente.
"""

import json
import subprocess
import tempfile
import winreg
from pathlib import Path

import questionary

from src import selectors

OID_CLIENT_AUTH = "1.3.6.1.5.5.7.3.2"

_SCRIPT_LISTAR = """
# Se o PowerShell 7 também estiver instalado na máquina, ele pode poluir o
# $env:PSModulePath e fazer o Windows PowerShell 5.1 (usado aqui) autocarregar
# a versão errada de Microsoft.PowerShell.Security — aí o drive Cert: nunca
# monta e Get-ChildItem falha em silêncio (-ErrorAction SilentlyContinue).
# Forçar a versão nativa evita isso; se não existir, cai no autoload normal.
Import-Module Microsoft.PowerShell.Security -RequiredVersion 3.0.0.0 -ErrorAction SilentlyContinue
$oid = '1.3.6.1.5.5.7.3.2'
$certs = @()
foreach ($loc in 'CurrentUser','LocalMachine') {
    Get-ChildItem ('Cert:\\' + $loc + '\\My') -ErrorAction SilentlyContinue | Where-Object {
        $_.NotAfter -gt (Get-Date) -and
        ($_.Extensions | Where-Object { $_.Oid.Value -eq '2.5.29.37' } |
            ForEach-Object { $_.EnhancedKeyUsages } | Where-Object { $_.Value -eq $oid })
    } | ForEach-Object {
        $certs += [PSCustomObject]@{
            Subject  = $_.Subject
            Issuer   = $_.Issuer
            Thumbprint = $_.Thumbprint
            NotAfter = $_.NotAfter.ToString('yyyy-MM-dd')
            Store    = $loc
        }
    }
}
ConvertTo-Json -InputObject $certs -Compress
"""


def _extrair_cn(subject: str) -> str:
    for parte in subject.split(","):
        parte = parte.strip()
        if parte.upper().startswith("CN="):
            return parte[3:].strip()
    return subject


def listar_certificados() -> list[dict]:
    """Certificados com EKU 'Client Authentication' e não expirados, em
    CurrentUser\\My e LocalMachine\\My — só leitura, nada é exportado/
    alterado no store.

    Não filtra por chave privada acessível/exportável: certificados de
    token/smart card podem reportar isso de forma inconsistente antes do
    PIN ser digitado — se não houver chave usável, o Chrome falha na hora
    de apresentar o certificado, e não antes, na listagem.
    """
    resultado = subprocess.run(
        ["powershell", "-NoProfile", "-NonInteractive", "-Command", _SCRIPT_LISTAR],
        capture_output=True,
        text=True,
    )
    if resultado.returncode != 0:
        raise RuntimeError(f"PowerShell falhou: {resultado.stderr.strip()}")

    saida = resultado.stdout.strip()
    if not saida:
        return []

    brutos = json.loads(saida)
    if isinstance(brutos, dict):
        brutos = [brutos]

    return [
        {
            "cn": _extrair_cn(c["Subject"]),
            "issuer_cn": _extrair_cn(c["Issuer"]),
            "thumbprint": c["Thumbprint"],
            "validade": c["NotAfter"],
            "store": c["Store"],
        }
        for c in brutos
    ]


def escolher_certificado(certificados: list[dict]) -> dict:
    """Menu de setas no terminal — um certificado por vez."""
    escolha = questionary.select(
        "Selecione o certificado digital:",
        choices=[
            questionary.Choice(
                title=f"{c['cn']}  (válido até {c['validade']}, {c['store']})",
                value=i,
            )
            for i, c in enumerate(certificados)
        ],
    ).ask()

    if escolha is None:
        raise KeyboardInterrupt("seleção cancelada")

    return certificados[escolha]


def _versao_major_chrome() -> int | None:
    """Lê a versão do Chrome instalado no registro do Windows.

    O auto-detect do undetected-chromedriver pode errar a versão (baixa um
    chromedriver mais novo que o Chrome instalado) e derruba a conexão com
    'This version of ChromeDriver only supports Chrome version N' — melhor
    ler a versão real e passar explícito via version_main.
    """
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Google\Chrome\BLBeacon") as chave:
            versao, _ = winreg.QueryValueEx(chave, "version")
        return int(versao.split(".")[0])
    except OSError:
        return None


_POLICY_KEY_PATH = r"HKLM:\Software\Policies\Google\Chrome\AutoSelectCertificateForUrls"


def _rodar_ps1_elevado(conteudo: str) -> bool:
    """Roda um .ps1 temporário elevado (UAC), num PROCESSO SEPARADO.

    A escrita da policy precisa ser em HKLM (exige admin), mas o processo
    principal do robô NÃO pode estar elevado — Chrome/Selenium falha
    ("chrome not reachable") quando quem o lança está rodando como
    Administrador. Por isso o UAC pede consentimento só pra esse toque
    pontual no registro, via Start-Process -Verb RunAs -Wait, enquanto o
    resto do robô (e o Chrome) segue sem elevação.
    """
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".ps1", delete=False, encoding="utf-8"
    ) as f:
        f.write(conteudo)
        caminho_script = f.name

    try:
        lancador = (
            "Start-Process -FilePath powershell -Verb RunAs -WindowStyle Hidden -Wait "
            f"-ArgumentList @('-NoProfile','-NonInteractive','-File','{caminho_script}')"
        )
        resultado = subprocess.run(
            ["powershell", "-NoProfile", "-NonInteractive", "-Command", lancador],
            capture_output=True,
            text=True,
        )
        return resultado.returncode == 0
    finally:
        Path(caminho_script).unlink(missing_ok=True)


def _tentar_definir_selecao_automatica(padrao_json: str) -> bool:
    """Tenta gravar a policy AutoSelectCertificateForUrls em
    HKEY_LOCAL_MACHINE — jeito oficialmente suportado pelo Chrome pra
    selecionar certificado sem popup nativo (mesma lógica do
    PythonLoginWithCertificateSelenium). HKLM evita a ACL de bloqueio que
    máquinas com política de segurança corporativa costumam aplicar em
    HKCU\\Software\\Policies, mas exige admin — daí o UAC separado.

    Se o usuário cancelar o UAC, ignora e deixa o
    --auto-select-certificate-for-urls de linha de comando (sempre
    aplicado) como única camada — avisa no terminal.
    """
    padrao_ps = padrao_json.replace("'", "''")
    script = (
        f"New-Item -Path '{_POLICY_KEY_PATH}' -Force | Out-Null\n"
        f"Set-ItemProperty -Path '{_POLICY_KEY_PATH}' -Name '1' -Value '{padrao_ps}'"
    )
    ok = _rodar_ps1_elevado(script)
    if not ok:
        print(
            "Aviso: não foi possível gravar a policy AutoSelectCertificateForUrls "
            "em HKEY_LOCAL_MACHINE (UAC cancelado ou sem privilégio de admin). "
            "Seguindo só com a flag de linha de comando do Chrome — se o popup "
            "de seleção de certificado ainda aparecer, aceite o UAC na próxima."
        )
    return ok


def _remover_selecao_automatica() -> None:
    """Remove a policy ao final — ela só deve existir durante a execução."""
    _rodar_ps1_elevado(f"Remove-Item -Path '{_POLICY_KEY_PATH}' -Force -ErrorAction SilentlyContinue")


def _clicavel_no_shadow(host_selector: str, inner_selector: str):
    """Como element_to_be_clickable padrão do Selenium não atravessa Shadow
    DOM, replica a mesma checagem (existe, visível, habilitado) manualmente
    a partir do shadow_root do host.
    """
    from selenium.common.exceptions import NoSuchElementException, StaleElementReferenceException
    from selenium.webdriver.common.by import By

    def condicao(driver):
        # WebDriverWait.until não retenta sozinho num StaleElementReference
        # (só ignora NoSuchElement por padrão) — sem isso, um elemento que
        # fica stale entre o find e o is_displayed() no meio de um poll
        # derruba a espera inteira em vez de só tentar de novo.
        try:
            host = driver.find_element(By.CSS_SELECTOR, host_selector)
            el = host.shadow_root.find_element(By.CSS_SELECTOR, inner_selector)
            return el if el.is_displayed() and el.is_enabled() else False
        except (NoSuchElementException, StaleElementReferenceException):
            return False

    return condicao


def _logar_via_govbr(driver, timeout_s: float) -> None:
    """gov.br: clica em "Entrar", depois em "Seu certificado digital" (é
    ali, em certificado.sso.acesso.gov.br, que o Chrome realmente pede o
    certificado cliente — não no e-CAC).
    """
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support import expected_conditions as EC
    from selenium.webdriver.support.ui import WebDriverWait

    def pagina_carregada(d):
        return d.execute_script("return document.readyState") == "complete"

    espera = WebDriverWait(driver, timeout_s)

    driver.get(selectors.URL_GOV_BR)
    espera.until(pagina_carregada)
    espera.until(
        _clicavel_no_shadow(selectors.HOST_BARRA_GOVBR, selectors.BTN_ENTRAR)
    ).click()

    espera.until(pagina_carregada)
    espera.until(EC.element_to_be_clickable((By.CSS_SELECTOR, selectors.BTN_LOGIN_CERTIFICADO))).click()

    # aqui o Chrome apresenta o certificado (auto-selecionado via
    # policy/flag) e o SSO redireciona de volta — espera essa navegação
    # terminar antes de abrir a aba do e-CAC.
    espera.until(pagina_carregada)


def abrir_navegador_com_certificado(certificado: dict, config: dict, headless: bool | None = None):
    """Abre o Chrome via undetected-chromedriver com seleção automática do
    certificado escolhido (sem popup nativo) — NÃO navega nem loga em
    lugar nenhum, fica na aba padrão (nova guia em branco). Retorna o
    driver (e a flag de policy, pra quem chamou decidir quando remover) —
    quem chamar é responsável por fechar o driver.

    `headless=None` usa `config.navegador.headless`; passe True/False pra
    sobrescrever — a FASE 1 do Regularize (login manual) precisa sempre de
    um navegador visível, independente do que estiver no config.yaml.
    """
    import undetected_chromedriver as uc

    if headless is None:
        headless = config["navegador"]["headless"]
    timeout_s = config["navegador"]["timeout_ms"] / 1000

    # pattern "*" (não travado no host de destino): o clique em "entrar com
    # certificado" costuma redirecionar pro domínio de SSO do gov.br pra
    # fazer o handshake mTLS, não pro host original — travar o pattern no
    # host de destino faz o filtro nunca casar com a origem real que pede o
    # certificado. Quem restringe QUAL certificado sai é o filtro
    # SUBJECT/ISSUER, não o pattern.
    padrao_certificado = json.dumps({
        "pattern": "*",
        "filter": {
            "SUBJECT": {"CN": certificado["cn"]},
            "ISSUER": {"CN": certificado["issuer_cn"]},
        },
    })

    politica_aplicada = _tentar_definir_selecao_automatica(padrao_certificado)

    options = uc.ChromeOptions()
    options.add_argument(f"--auto-select-certificate-for-urls={padrao_certificado}")
    if headless:
        # ponytail: headless ainda é WIP no undetected-chromedriver e reduz
        # o efeito stealth — evite em sites com bot-detection agressivo.
        options.add_argument("--headless=new")

    driver = uc.Chrome(options=options, version_main=_versao_major_chrome())
    driver.set_page_load_timeout(timeout_s)
    return driver, politica_aplicada


def abrir_navegador_com_cookies(cookies: list[dict], config: dict):
    """Sobe um Chrome headless sem seleção de certificado nenhuma e injeta
    cookies de uma sessão já autenticada manualmente num outro navegador
    (ver RUNBOOK.md, seção "sessão headless via cookies") — não repete
    login nem clique nenhum, só reaproveita a sessão. Retorna o driver já
    navegado (de novo) pro e-CAC; quem chamar é responsável por fechá-lo.

    Cookies do tipo TS* (F5 BIG-IP) costumam prender o IP de origem — só
    funciona rodando da mesma rede/IP de onde os cookies foram capturados,
    e são cookies de sessão (sem `expiry`), então cada execução precisa da
    FASE 1 manual de novo pra gerar cookies novos.
    """
    import undetected_chromedriver as uc

    timeout_s = config["navegador"]["timeout_ms"] / 1000
    options = uc.ChromeOptions()
    options.add_argument("--headless=new")

    driver = uc.Chrome(options=options, version_main=_versao_major_chrome())
    driver.set_page_load_timeout(timeout_s)

    driver.get(selectors.URL_ECAC)
    for cookie in cookies:
        driver.add_cookie(cookie)
    driver.get(selectors.URL_ECAC)
    return driver


def abrir_navegador_autenticado(certificado: dict, config: dict):
    """Igual abrir_navegador_com_certificado, mas já loga via gov.br
    automaticamente antes de retornar."""
    timeout_s = config["navegador"]["timeout_ms"] / 1000
    driver, politica_aplicada = abrir_navegador_com_certificado(certificado, config)
    _logar_via_govbr(driver, timeout_s)
    return driver, politica_aplicada


def abrir_navegador(certificado: dict, config: dict) -> None:
    """Abre o Chrome autenticado e abre o destino configurado numa aba
    nova, deixando aberto pra inspeção manual até o usuário confirmar.
    """
    url = config["destino"]["url"]
    driver, politica_aplicada = abrir_navegador_autenticado(certificado, config)
    try:
        driver.switch_to.new_window("tab")
        driver.get(url)
        print(f"Navegador aberto em: {driver.current_url}")

        input("Pressione Enter para fechar o navegador...")
    finally:
        driver.quit()
        if politica_aplicada:
            _remover_selecao_automatica()
