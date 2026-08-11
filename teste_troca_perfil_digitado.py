"""Teste ao vivo, ad hoc e descartável: reavalia se digitar o CNPJ
caractere-a-caractere (send_keys por char, com pequeno atraso) em vez de
colar/setar o valor direto evita o bloqueio de "acesso automatizado" da
Receita ao trocar o perfil de acesso no e-CAC — ver RUNBOOK.md, seção
"BLOQUEIO DE AUTOMAÇÃO CONFIRMADO". Não faz parte do fluxo principal
(FASE 1 continua manual em src/regularize.py até este teste confirmar o
contrário).

Rodar direto no terminal (precisa de stdin/tela reais pro login manual):
    python teste_troca_perfil_digitado.py
"""

import random
import time
from pathlib import Path

import yaml
from selenium.webdriver.common.by import By

from src import fluxo, regularize, selectors

CNPJ_TESTE = "17462219000105"


def main() -> None:
    with open("config.yaml", "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)

    certificados = fluxo.listar_certificados()
    cn_padrao = config.get("certificado", {}).get("cn_padrao", "")
    escolhido = next(
        (c for c in certificados if cn_padrao.upper() in c["cn"].upper()),
        certificados[0],
    )
    print(f"Usando certificado: {escolhido['cn']}")

    timeout_s = config["navegador"]["timeout_ms"] / 1000
    ddmmyyyy, hhmm = regularize._timestamp()
    logger = regularize.Logger(
        Path("artifacts/traces") / f"teste_troca_perfil_digitado_{ddmmyyyy}-{hhmm}.jsonl"
    )

    driver, politica_aplicada = fluxo.abrir_navegador_com_certificado(escolhido, config)
    try:
        print(
            "\nFaça manualmente, no seu ritmo:\n"
            f"  1. Vá para {selectors.URL_GOV_BR} → Entrar → Seu certificado digital "
            "(resolva o captcha se aparecer).\n"
            f"  2. Abra {selectors.URL_ECAC} numa aba.\n"
            "Pressione Enter aqui quando o e-CAC estiver aberto e autenticado.\n"
        )
        input("> ")

        aba_ecac = next(
            (
                h
                for h in driver.window_handles
                if regularize._url_da_aba(driver, h).startswith(selectors.URL_ECAC)
            ),
            None,
        )
        if aba_ecac is None:
            print("Nenhuma aba no e-CAC encontrada — abra o e-CAC antes de continuar.")
            return
        driver.switch_to.window(aba_ecac)

        logger.log(
            "teste_iniciado",
            hipotese="digitar caractere-a-caractere em vez de colar/setar valor direto",
        )

        regularize._clicar(
            driver, driver.find_element(By.XPATH, selectors.XPATH_BTN_ALTERAR_PERFIL_ECAC)
        )
        campo = regularize.esperar_elemento(
            driver, By.CSS_SELECTOR, selectors.INPUT_CNPJ_PERFIL, timeout_s
        )
        regularize._clicar(driver, campo)
        campo.clear()

        logger.log("digitando_cnpj", cnpj=CNPJ_TESTE)
        for caractere in CNPJ_TESTE:
            campo.send_keys(caractere)
            time.sleep(0.08 + random.random() * 0.08)

        botao_alterar = driver.find_element(By.XPATH, selectors.XPATH_BTN_ALTERAR_APOS_CNPJ)
        regularize._clicar(driver, botao_alterar)

        time.sleep(2)
        texto_pagina = driver.find_element(By.TAG_NAME, "body").text
        bloqueado = "acesso automatizado" in texto_pagina.lower()
        cnpj_na_pagina = CNPJ_TESTE in "".join(c for c in texto_pagina if c.isdigit())

        logger.log(
            "resultado_teste",
            bloqueado=bloqueado,
            cnpj_confirmado_na_pagina=cnpj_na_pagina,
        )
        if bloqueado:
            print(
                "\n>>> BLOQUEADO: a Receita detectou como acesso automatizado "
                "(mesma mensagem de antes, ver RUNBOOK.md)."
            )
        elif cnpj_na_pagina:
            print(
                "\n>>> SUCESSO: perfil trocado, CNPJ aparece na página — "
                "digitar não foi bloqueado!"
            )
        else:
            print("\n>>> INCONCLUSIVO — confira manualmente a tela antes de fechar.")

        input("\nPressione Enter para fechar o navegador...")
    finally:
        driver.quit()
        if politica_aplicada:
            fluxo._remover_selecao_automatica()
        logger.fechar()


if __name__ == "__main__":
    main()
