# Contexto do projeto — bot e-CAC (certificado digital) + relatórios Regularize (PGFN)

**Leitura obrigatória no início de toda conversa:** `CLAUDE.md` (este
arquivo), `RUNBOOK.md` e `SPEC.md`. **Atualização obrigatória a cada
mudança:** qualquer alteração de comportamento, fluxo ou descoberta nova
sobre o site deve ser refletida nesses três arquivos antes de considerar a
mudança concluída — não deixar a documentação dessincronizar do código.

Robô em Python + Selenium (`undetected-chromedriver`, para reduzir captcha/
bot-detection do gov.br) para autenticar com certificado digital A1
instalado no Windows, e a partir daí gerar os relatórios de dívida ativa
no portal Regularize (PGFN). Dois modos, via `src/main.py`:

- `python -m src.main` — lista os certificados válidos do Windows
  Certificate Store, deixa o usuário escolher um via menu de setas no
  terminal, loga via gov.br (https://www.gov.br/pt-br → "Entrar" → "Seu
  certificado digital") e abre o e-CAC
  (https://cav.receita.fazenda.gov.br/ecac/) numa aba nova, já autenticado
  pela sessão SSO. Deixa o navegador aberto pro usuário continuar
  manualmente.
- `python -m src.main --regularize <CNPJ> [--limit N]` — FASE 1 (login
  gov.br + e-CAC + troca de perfil de acesso pro CNPJ) é **sempre
  manual**, num navegador visível; ao confirmar, o robô captura os
  cookies da sessão, fecha esse navegador e abre um segundo, headless,
  com a sessão herdada via cookies — é nesse segundo navegador que roda
  o resto (Relatório Consolidado e Relatórios Detalhados por inscrição).
  Ver `src/regularize.py` e `RUNBOOK.md` (seção "sessão headless via
  cookies") pro porquê e os riscos conhecidos; `prompt.md`/`SPEC.md` pra
  especificação original. `--limit N` trunca os relatórios detalhados
  gerados na FASE 3 (útil pra validar antes de rodar tudo). PDFs em
  `./output/{cnpj_digits}/{DDMMYYYY}/`, log estruturado em
  `artifacts/traces/regularize_*.jsonl`.

## Estrutura

- `src/selectors.py` — único lugar com seletores CSS/XPath do site (login
  via gov.br + e-CAC + Regularize).
- `src/fluxo.py` — listar certificados, escolher via terminal, abrir
  navegador (com ou sem login automático via gov.br já embutido) e
  `abrir_navegador_com_cookies` (headless, injeta cookies de uma sessão
  já autenticada — ver RUNBOOK.md).
- `src/regularize.py` — geração dos relatórios do Regularize: troca de
  perfil manual (FASE 1, retorna os cookies da sessão pro chamador),
  Relatório Consolidado (FASE 2), enumeração + Relatórios Detalhados por
  inscrição (FASE 3), Parcelamentos via SISPAR (FASE 4) e CAPAG (FASE 5)
  — todas rodam no segundo navegador aberto com os cookies da FASE 1
  (`fluxo.abrir_navegador_com_cookies`, que agora respeita
  `config.navegador.headless` igual o navegador #1). FASE 4/5
  reaproveitam a mesma sessão pra entrar no SISPAR (app JSF/PrimeFaces
  separado do Regularize, alcançado via token na URL — sem novo login/
  troca de perfil). Logger estruturado (`Logger.log`) e todas as esperas/
  cliques do módulo — nenhum seletor literal aqui, sempre de
  `selectors.py`.
- `src/main.py` — entrypoint, escolhe entre o fluxo e-CAC simples e o
  `--regularize <CNPJ>`.
- `config.yaml` — o que o usuário ajusta (URL de destino, headless,
  timeout — `navegador.timeout_ms` também controla todas as esperas do
  fluxo Regularize).
- `.env` — reservado para credenciais futuras, fora do git.
- `artifacts/traces` e `artifacts/screenshots` — evidências de execução.
- `output/{cnpj_digits}/{DDMMYYYY}/` — PDFs gerados pelo fluxo Regularize.

## Convenções

- Certificados são só **lidos** do Windows Certificate Store
  (`Cert:\CurrentUser\My` e `Cert:\LocalMachine\My`, via PowerShell) — nada é
  importado, exportado, removido ou alterado no store. O certificado já
  precisa estar instalado no Windows antes de rodar o robô.
- Filtro de listagem: EKU "Client Authentication" (`1.3.6.1.5.5.7.3.2`) e
  não estar expirado — mesmo critério usado pelo app de origem
  (`app_pdf_downloader`/`CertificateService.cs`) para e-CNPJ. **Não** filtra
  por chave privada exportável/acessível: isso é só informativo lá (não
  exclui certificado da lista) porque tokens/smart cards podem reportar
  acesso à chave de forma inconsistente antes do PIN — se a chave não
  estiver realmente disponível, o Chrome falha ao apresentar o certificado
  na hora da conexão, não antes.
- A seleção automática do certificado no Chrome é em duas camadas, na mesma
  lógica do
  [PythonLoginWithCertificateSelenium](https://github.com/JimmyelsonSilvaPeres/PythonLoginWithCertificateSelenium):
  (1) tenta gravar a policy `AutoSelectCertificateForUrls` em
  `HKEY_LOCAL_MACHINE\Software\Policies\Google\Chrome` — jeito oficialmente
  suportado pelo Chrome, mas exige admin pra gravar em HKLM (HKCU\Software\
  Policies costuma vir com ACL de escrita bloqueada em máquina com política
  de segurança corporativa, então nem vale tentar lá); (2) sempre define
  também a flag de linha de comando `--auto-select-certificate-for-urls`
  (confirmado, via `chrome://version`, que chega intacta no processo do
  Chrome — sem bug de escaping na cadeia Selenium→ChromeDriver→Chrome).
  **Importante:** o processo principal do robô (o que abre o Chrome) NUNCA
  pode rodar elevado — Chrome/Selenium falha com "chrome not reachable"
  quando o processo que o lança está como Administrador (confirmado em
  produção, é bug conhecido do próprio Chrome/chromedriver no Windows). Por
  isso a gravação em HKLM roda num **processo PowerShell separado e
  elevado** (`_rodar_ps1_elevado`, via `Start-Process -Verb RunAs -Wait`,
  script escrito num `.ps1` temporário) — o UAC aparece só naquele instante,
  e o processo do robô/Chrome continua sem elevação. Se o usuário cancelar o
  UAC, cai pra usar só a flag de linha de comando (avisa no terminal, não
  crasha). O filtro JSON usa `SUBJECT.CN` **e** `ISSUER.CN` (extraído do
  certificado, igual ao repo de referência) pra casar mais especificamente.
  O `pattern` é `"*"` (não travado no host de `destino.url`): clicar em
  "entrar com certificado" no e-CAC redireciona pro domínio de SSO do
  gov.br pra fazer o handshake mTLS, não fica no host original — travar o
  pattern no host de destino faz o filtro nunca casar com a origem real que
  pede o certificado. Quem restringe qual certificado sai é o filtro
  SUBJECT/ISSUER, não o pattern. Se mesmo assim aparecer o popup nativo
  listando todos os certificados, ver `RUNBOOK.md`.
- O login não vai direto pro e-CAC: passa por `https://www.gov.br/pt-br`
  (botão "Entrar", `selectors.BTN_ENTRAR`) → "Seu certificado digital"
  (`selectors.BTN_LOGIN_CERTIFICADO`) — é nessa página
  (`certificado.sso.acesso.gov.br`) que o handshake mTLS de fato acontece.
  Só depois disso o e-CAC abre numa aba nova (`driver.switch_to.new_window`),
  já com a sessão SSO autenticada.
- O botão "Entrar" vive dentro do **Shadow DOM** do custom element
  `<barra-govbr>` (web component de `barra.sistema.gov.br`) — confirmado
  com Selenium real, `find_element` comum na página não alcança, só via
  `barra.shadow_root.find_element(...)`. `fluxo._clicavel_no_shadow` existe
  só por causa disso; o segundo clique (`#login-certificate`, já em
  `sso.acesso.gov.br`) é DOM normal, sem shadow.
- `setuptools` está em `requirements.txt` só porque `undetected-chromedriver`
  ainda faz `from distutils.version import LooseVersion`, removido do stdlib
  no Python 3.12+ — sem isso o `import undetected_chromedriver` quebra.
- `tzdata` está em `requirements.txt` porque `zoneinfo.ZoneInfo("America/
  Sao_Paulo")` (usado pros nomes de arquivo/timestamps do Regularize) dá
  `ZoneInfoNotFoundError` no Windows sem ele — a stdlib não traz o banco
  IANA nessa plataforma.
- **FASE 1 do fluxo Regularize é sempre manual — nunca automatizar login
  nem o clique de troca de perfil.** Login por certificado automático tem
  uma corrida (pode seguir antes do handshake terminar) e a troca de
  "perfil de acesso" no e-CAC é **bloqueada pela Receita como acesso
  automatizado** quando feita via Selenium — confirmado ao vivo, sem
  workaround conhecido (ver `RUNBOOK.md`). `regularize.
  autenticar_e_trocar_perfil` só abre uma aba em branco, pausa em
  `input()` e, ao confirmar, captura `driver.get_cookies()` da sessão.
- **A partir da FASE 2, o fluxo roda num segundo navegador headless com a
  sessão herdada via cookies (`fluxo.abrir_navegador_com_cookies`) —
  não é o mesmo navegador da FASE 1.** Isso não automatiza login nem
  troca de perfil (continuam manuais, feitos por um humano no navegador
  #1); só reaproveita a sessão já autenticada. Confirmado ao vivo em
  2026-08-11 (`teste_cookies_headless.py`). Risco conhecido sem
  workaround: os cookies `TS*` (F5 BIG-IP) prendem o IP de origem — só
  funciona rodando da mesma rede de onde a FASE 1 manual aconteceu, e são
  cookies de sessão (expiram), então a FASE 1 manual se repete a cada
  execução. Ver `RUNBOOK.md` pra arquitetura completa.
- **Nunca clicar no botão "Imprimir"** do Regularize — dispara
  `window.print()` nativo, que abre uma aba `chrome://print/` e bloqueia a
  aba original via JS até ela ser fechada. PDF sempre via CDP
  (`driver.execute_cdp_cmd("Page.printToPDF", ...)`), nunca `page.pdf()`
  nem o "Imprimir" do site — sua presença na tela só serve como sinal de
  que a página terminou de montar a view, não é clicado.
- Depois de clicar em "expandir" num painel de débito, espere
  `document.getAnimations().length == 0` antes do próximo clique — a
  posição de cada painel é calculada no momento do clique, e clicar rápido
  demais (comum quando há poucos débitos) faz o texto de vários painéis se
  sobrepor no PDF final.
- Qualquer seletor de site vai em `selectors.py`, nunca inline em `fluxo.py`.
- Antes de alterar o fluxo por causa de mudança no site, ver `RUNBOOK.md`.
- `SPEC.md` define o que está dentro/fora de escopo — não expandir sem alinhar.
