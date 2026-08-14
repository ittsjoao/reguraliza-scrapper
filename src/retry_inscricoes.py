"""Reprocessa relatórios detalhados só das inscrições passadas em ALVO —
usado quando gerar_relatorios_detalhados falhou pra algumas poucas
inscrições numa execução anterior (ver artifacts/traces/*.jsonl,
evento DIVERGENCIA "falhou ao gerar relatório de ..."). Pula Consolidado,
SISPAR e CAPAG. FASE 1 (login + troca de perfil) continua manual, igual
ao fluxo normal de main.py."""

import argparse
from pathlib import Path

from src import fluxo, regularize
from src.main import carregar_config, _escolher_certificado_ou_sair


def executar_retry(cnpj: str, alvo: set[str], config: dict, aguardar_sinal: bool = False) -> None:
    escolhido = _escolher_certificado_ou_sair(config)
    if escolhido is None:
        return

    timeout_s = config["navegador"]["timeout_ms"] / 1000
    ddmmyyyy, hhmm = regularize._timestamp()
    logger = regularize.Logger(
        Path("artifacts/traces") / f"regularize_retry_{ddmmyyyy}-{hhmm}.jsonl"
    )

    driver_manual, politica_aplicada = fluxo.abrir_navegador_com_certificado(
        escolhido, config, headless=False
    )
    try:
        cookies = regularize.autenticar_e_trocar_perfil(
            driver_manual, cnpj, timeout_s, logger, aguardar_input=not aguardar_sinal
        )
    finally:
        driver_manual.quit()
        if politica_aplicada:
            fluxo._remover_selecao_automatica()

    driver = fluxo.abrir_navegador_com_cookies(cookies, config)
    try:
        regularize.confirmar_sessao_headless_autenticada(driver, timeout_s, logger)
        regularize.entrar_no_regularize_via_ecac(driver, timeout_s, logger)

        enumeracao = regularize.enumerar_inscricoes(driver, timeout_s, logger)
        enumeracao_filtrada = {
            tab_key: [dom_id for dom_id in ids if any(n in dom_id for n in alvo)]
            for tab_key, ids in enumeracao.items()
        }
        encontrados = {n for ids in enumeracao_filtrada.values() for dom_id in ids for n in alvo if n in dom_id}
        faltando = alvo - encontrados
        if faltando:
            print(f"AVISO: não encontradas na enumeração atual: {sorted(faltando)}")

        caminhos = regularize.gerar_relatorios_detalhados(
            driver, enumeracao_filtrada, cnpj, timeout_s, logger
        )
        print(f"Relatórios detalhados gerados: {len(caminhos)}")
        for c in caminhos:
            print(f"  {c}")
    finally:
        driver.quit()
        logger.fechar()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--cnpj", required=True)
    parser.add_argument("--inscricoes", required=True, help="Lista separada por vírgula.")
    parser.add_argument("--aguardar-sinal", action="store_true")
    args = parser.parse_args()

    alvo = {i.strip() for i in args.inscricoes.split(",") if i.strip()}
    config = carregar_config()
    executar_retry(args.cnpj, alvo, config, aguardar_sinal=args.aguardar_sinal)


if __name__ == "__main__":
    main()
