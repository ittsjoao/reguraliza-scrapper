"""Teste ao vivo, ad hoc e descartável: em vez de refazer o login manual
(FASE 1), sobe um Chrome headless e injeta cookies de uma sessão já
autenticada num navegador real, pra ver se o e-CAC aceita a sessão sem
disparar o bloqueio de "acesso automatizado" (ver RUNBOOK.md). Não faz
parte do fluxo principal — FASE 1 continua manual em src/regularize.py
até este teste confirmar que cookies bastam.

Risco conhecido: os cookies TS* (F5 BIG-IP) costumam embutir o IP de
origem — se este script rodar de uma rede/IP diferente de onde os
cookies foram capturados, o WAF provavelmente rejeita antes mesmo de
carregar a página.

Rodar direto no terminal:
    python teste_cookies_headless.py
"""

from src import fluxo, selectors
from selenium.webdriver.common.by import By

COOKIES = [
    {
        "name": "ASP.NET_SessionId",
        "value": "txmg1hcmkc3vol32etu5ie2a",
        "domain": "cav.receita.fazenda.gov.br",
        "path": "/",
        "secure": False,
        "httpOnly": True,
    },
    {
        "name": "COOKIECAV",
        "value": "2b550a2224debf8fc9bad6d0bc2cebc57cb44c164b2706923ce0980fb35e9da5470fa05e4171b4d36a9378ae9d9ae746f5e5a4a2113acfde279ef05f1b39b2f4",
        "domain": ".cav.receita.fazenda.gov.br",
        "path": "/",
        "secure": True,
        "httpOnly": True,
    },
    {
        "name": "TS014d0691",
        "value": "019e1ebfde9c07832699e9b6304afdf88884b79c293b16c808b26726fab9abf8efaa68b0b7eabcbd1a4d1ef09fad216e42873a5d5add4003818f178112e2f937e8498099260cf1dfacae974d24284e2f1a1870d525",
        "domain": "cav.receita.fazenda.gov.br",
        "path": "/",
        "secure": False,
        "httpOnly": False,
    },
    {
        "name": "assinadoc_cert_type",
        "value": "A1",
        "domain": ".cav.receita.fazenda.gov.br",
        "path": "/",
        "secure": False,
        "httpOnly": False,
    },
    {
        "name": "ecacrlmp",
        "value": "SCQuFbkVQj+ib0Bhatyva+XUq6L4Yllwtk2mcC9nRwM=",
        "domain": "cav.receita.fazenda.gov.br",
        "path": "/",
        "secure": False,
        "httpOnly": False,
    },
    {
        "name": "TS0188162d",
        "value": "019e1ebfdeaf9864c1bb5355f8c2acde41fe799f5e3b16c808b26726fab9abf8efaa68b0b7eabcbd1a4d1ef09fad216e42873a5d5a6131c8ca2491414406f8a4c99465c1ec18b5ee0ed7d6d20f224e98e106993d17c575cdcdc2f4a117ffea07da1692e4cb",
        "domain": ".cav.receita.fazenda.gov.br",
        "path": "/",
        "secure": False,
        "httpOnly": False,
    },
    {
        "name": "TSafd868f7027",
        "value": "082670627aab200043900f1ce4fd66c663ad979706bd82a5b6c6bd8752547dcddeca28af4804c48a08182cc34611300014816ce6f3b47028a1d798cf60ee8163204de7c1f2bdef8149e988a280b4e0690078eef9ed2b122609559b90d79ac126",
        "domain": "cav.receita.fazenda.gov.br",
        "path": "/",
        "secure": False,
        "httpOnly": False,
    },
]


def main() -> None:
    import undetected_chromedriver as uc

    options = uc.ChromeOptions()
    options.add_argument("--headless=new")
    driver = uc.Chrome(options=options, version_main=fluxo._versao_major_chrome())
    try:
        driver.get(selectors.URL_ECAC)
        for cookie in COOKIES:
            driver.add_cookie(cookie)

        driver.get(selectors.URL_ECAC)
        print(f"URL final: {driver.current_url}")

        autenticado = bool(
            driver.find_elements(By.XPATH, selectors.XPATH_BTN_ALTERAR_PERFIL_ECAC)
        )
        if autenticado:
            print(">>> SUCESSO: sessão aceita, e-CAC autenticado (achou 'Alterar perfil de acesso').")
        else:
            print(">>> FALHOU: não achou sinal de sessão autenticada — confira o HTML abaixo.")
            print(driver.page_source[:2000])
    finally:
        driver.quit()


if __name__ == "__main__":
    main()
