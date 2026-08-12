import argparse
from pathlib import Path

import yaml

from src import fluxo, regularize

CONFIG_PATH = Path(__file__).resolve().parent.parent / "config.yaml"


def carregar_config() -> dict:
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def _escolher_certificado_ou_sair(config: dict) -> dict | None:
    certificados = fluxo.listar_certificados()
    if not certificados:
        print(
            "Nenhum certificado com chave privada e uso 'Client Authentication' "
            "encontrado no Windows Certificate Store."
        )
        return None

    cn_padrao = config.get("certificado", {}).get("cn_padrao")
    if cn_padrao:
        casados = [c for c in certificados if cn_padrao.upper() in c["cn"].upper()]
        if len(casados) == 1:
            print(f"Certificado selecionado automaticamente: {casados[0]['cn']}")
            return casados[0]

    return fluxo.escolher_certificado(certificados)


def _limitar_enumeracao(enumeracao: dict[str, list[str]], limite: int | None) -> dict[str, list[str]]:
    """Trunca a enumeração pro total pedido, preservando a ordem das abas —
    só pra validar rápido (`--limit`) antes de rodar tudo."""
    if limite is None:
        return enumeracao
    limitada: dict[str, list[str]] = {}
    restante = limite
    for chave, ids in enumeracao.items():
        limitada[chave] = ids[:restante] if restante > 0 else []
        restante -= len(limitada[chave])
    return limitada


def executar_regularize(
    cnpj: str, config: dict, limite: int | None = None, aguardar_sinal: bool = False
) -> None:
    escolhido = _escolher_certificado_ou_sair(config)
    if escolhido is None:
        return

    timeout_s = config["navegador"]["timeout_ms"] / 1000
    ddmmyyyy, hhmm = regularize._timestamp()
    logger = regularize.Logger(
        Path("artifacts/traces") / f"regularize_{ddmmyyyy}-{hhmm}.jsonl"
    )

    # FASE 1 (login + troca de perfil) é sempre manual, num navegador
    # visível — ao confirmar, capturamos os cookies da sessão e fechamos
    # este navegador; FASE 2/3 rodam num segundo navegador, headless, com
    # a sessão herdada via cookies (ver RUNBOOK.md).
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

        if limite == 0:
            # --limit 0: pula Consolidado + enumeração/Detalhados inteiros
            # (não só zera a contagem) — útil pra validar SISPAR/CAPAG sem
            # esperar as fases que já sabemos que funcionam.
            print("--limit 0: pulando Relatório Consolidado e Detalhados.")
        else:
            caminho_consolidado = regularize.gerar_relatorio_consolidado(
                driver, cnpj, timeout_s, logger
            )
            print(f"Relatório consolidado: {caminho_consolidado}")

            enumeracao = regularize.enumerar_inscricoes(driver, timeout_s, logger)
            enumeracao = _limitar_enumeracao(enumeracao, limite)
            if limite is not None:
                print(f"--limit {limite}: gerando no máximo {limite} relatório(s) detalhado(s).")
            caminhos = regularize.gerar_relatorios_detalhados(
                driver, enumeracao, cnpj, timeout_s, logger
            )
            print(f"Relatórios detalhados gerados: {len(caminhos)}")

        caminhos_parcelamentos = regularize.gerar_relatorios_parcelamentos(driver, cnpj, timeout_s, logger)
        print(f"Relatórios de parcelamentos (SISPAR) gerados: {len(caminhos_parcelamentos)}")

        caminho_capag = regularize.gerar_relatorio_capag(driver, cnpj, timeout_s, logger)
        print(f"CAPAG: {caminho_capag}")
    finally:
        driver.quit()
        logger.fechar()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--regularize",
        metavar="CNPJ",
        help="Gera os relatórios de dívida ativa no Regularize para o CNPJ informado.",
    )
    parser.add_argument(
        "--limit",
        metavar="N",
        type=int,
        default=None,
        help="Gera no máximo N relatórios detalhados — útil pra validar antes de rodar tudo.",
    )
    parser.add_argument(
        "--aguardar-sinal",
        action="store_true",
        help=(
            "Em vez de pausar em Enter na FASE 1 (sem stdin interativo, ex.: "
            "processo iniciado por outra ferramenta), espera o arquivo "
            "artifacts/continuar_fase1.flag aparecer — alguém cria esse arquivo "
            "manualmente depois de confirmar a troca de perfil. Não é detecção "
            "automática pela página; login/troca de perfil continuam manuais."
        ),
    )
    args = parser.parse_args()

    config = carregar_config()

    if args.regularize:
        executar_regularize(
            args.regularize, config, limite=args.limit, aguardar_sinal=args.aguardar_sinal
        )
        return

    escolhido = _escolher_certificado_ou_sair(config)
    if escolhido is None:
        return
    fluxo.abrir_navegador(escolhido, config)


if __name__ == "__main__":
    main()
