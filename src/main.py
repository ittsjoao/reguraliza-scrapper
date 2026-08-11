import argparse
from pathlib import Path

import yaml

from src import fluxo, regularize

CONFIG_PATH = Path(__file__).resolve().parent.parent / "config.yaml"


def carregar_config() -> dict:
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def _escolher_certificado_ou_sair() -> dict | None:
    certificados = fluxo.listar_certificados()
    if not certificados:
        print(
            "Nenhum certificado com chave privada e uso 'Client Authentication' "
            "encontrado no Windows Certificate Store."
        )
        return None
    return fluxo.escolher_certificado(certificados)


def executar_regularize(cnpj: str, config: dict) -> None:
    escolhido = _escolher_certificado_ou_sair()
    if escolhido is None:
        return

    timeout_s = config["navegador"]["timeout_ms"] / 1000
    ddmmyyyy, hhmm = regularize._timestamp()
    logger = regularize.Logger(
        Path("artifacts/traces") / f"regularize_{ddmmyyyy}-{hhmm}.jsonl"
    )

    driver, politica_aplicada = fluxo.abrir_navegador_com_certificado(escolhido, config)
    try:
        regularize.autenticar_e_trocar_perfil(driver, cnpj, timeout_s, logger)

        caminho_consolidado = regularize.gerar_relatorio_consolidado(
            driver, cnpj, timeout_s, logger
        )
        print(f"Relatório consolidado: {caminho_consolidado}")

        enumeracao = regularize.enumerar_inscricoes(driver, timeout_s, logger)
        caminhos = regularize.gerar_relatorios_detalhados(
            driver, enumeracao, cnpj, timeout_s, logger
        )
        print(f"Relatórios detalhados gerados: {len(caminhos)}")
    finally:
        input("Pressione Enter para fechar o navegador...")
        driver.quit()
        if politica_aplicada:
            fluxo._remover_selecao_automatica()
        logger.fechar()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--regularize",
        metavar="CNPJ",
        help="Gera os relatórios de dívida ativa no Regularize para o CNPJ informado.",
    )
    args = parser.parse_args()

    config = carregar_config()

    if args.regularize:
        executar_regularize(args.regularize, config)
        return

    escolhido = _escolher_certificado_ou_sair()
    if escolhido is None:
        return
    fluxo.abrir_navegador(escolhido, config)


if __name__ == "__main__":
    main()
