# RUNBOOK — o site mudou, o que fazer

## "Nenhum certificado encontrado" mas o certificado está instalado

- Confira em `certmgr.msc` (Certificados - Usuário Atual → Pessoal →
  Certificados) se ele aparece ali. Se só aparecer em "Certificados - Computador
  Local", ele precisa estar acessível por `Cert:\LocalMachine\My` (o robô já
  lê os dois, mas leitura de `LocalMachine` pode depender de permissão).
- Confirme que não está expirado (`certmgr.msc` mostra a validade).
- Confirme que tem o uso estendido "Autenticação de Cliente" (Client
  Authentication, OID `1.3.6.1.5.5.7.3.2`) — certificados só de assinatura/
  e-mail (S/MIME) não entram no filtro.
- Se a máquina tiver **PowerShell 7 instalado junto com o Windows PowerShell
  5.1**, o `$env:PSModulePath` pode ficar poluído e o 5.1 autocarregar a
  versão errada de `Microsoft.PowerShell.Security`, quebrando o drive
  `Cert:` (falha em silêncio, retorna lista vazia sem erro nenhum). O
  `fluxo.py` já força `Import-Module ... -RequiredVersion 3.0.0.0` antes de
  usar `Cert:\` pra contornar isso; se ainda assim vier vazio, rode
  `Get-Module -ListAvailable Microsoft.PowerShell.Security` num
  `powershell.exe` (não `pwsh`) e confira se a versão `3.0.0.0` aparece.

## O menu de setas não aparece certo / trava no terminal

- Use Windows Terminal ou PowerShell — o `cmd.exe` antigo às vezes renderiza
  mal menus interativos (`questionary`/`prompt_toolkit`).
- Se rodar via SSH ou terminal sem suporte a cores/cursor, o menu pode falhar
  — teste direto no terminal local primeiro.

## Ainda aparece o popup nativo de "Selecionar certificado" (lista todos os certs)

- Confirme que o CN exibido no menu é exatamente o CN que o site está
  pedindo (às vezes o certificado tem múltiplos CNs/SANs).
- O `pattern` da policy é `"*"` de propósito (casa qualquer origem) —
  clicar em "entrar com certificado" no e-CAC normalmente redireciona pra
  um domínio de SSO do gov.br diferente do `destino.url`, e travar o
  pattern nesse host original faz o filtro nunca disparar na origem real.
  Não volte a travar isso num host específico sem antes conferir, na barra
  de endereço no momento do popup, qual é o domínio que está realmente
  pedindo o certificado.
- A gravação da policy em HKLM abre um **prompt de UAC** durante a execução
  (processo PowerShell separado, `_rodar_ps1_elevado`) — clique em "Sim". Se
  cancelar o UAC, o robô avisa no terminal e segue só com a flag de linha de
  comando.
- **NUNCA rode o `python -m src.main`/`executar.bat` inteiro como
  Administrador.** Isso quebra o Chrome com
  `SessionNotCreatedException: ... chrome not reachable` — é um bug
  conhecido do Chrome/chromedriver no Windows quando o processo que lança o
  browser está elevado. Só o toque pontual no registro (via UAC separado)
  deve ser elevado, nunca o robô todo.
- Pra confirmar que a flag de linha de comando está chegando certa no
  Chrome, abra `chrome://version` numa sessão manual do robô e confira a
  "Linha de comando" — o valor de `--auto-select-certificate-for-urls` deve
  aparecer com o JSON completo (`SUBJECT.CN` e `ISSUER.CN`), sem corrupção.
- Pra confirmar que a policy em HKLM foi mesmo gravada, confira em
  `regedit`:
  `HKEY_LOCAL_MACHINE\SOFTWARE\Policies\Google\Chrome\AutoSelectCertificateForUrls`
  — deve existir um valor `1` com o JSON durante a execução (o robô remove
  ao final, também via UAC separado).
- Se mesmo com HKLM gravado e a flag chegando intacta, e o robô rodando SEM
  elevação, o popup ainda listar todos os certs, o problema precisa ser
  reavaliado com quem pediu essa parte do fluxo antes de tentar mais
  workarounds.

## e-CAC mudou a URL ou o layout de login

- Atualize `destino.url` em `config.yaml` — não precisa tocar em código.
- Quando o fluxo de scraping dentro do e-CAC for implementado, todo seletor
  novo vai em `src/selectors.py` — nunca inline em `fluxo.py`.

## Login via gov.br travou/parou de funcionar (TimeoutException clicando)

- **O botão "Entrar" (`.br-sign-in`) vive dentro do Shadow DOM** do custom
  element `<barra-govbr>` (web component carregado de
  `barra.sistema.gov.br`) — um `find_element` comum na página NUNCA acha
  esse botão, por isso o `element_to_be_clickable` padrão do Selenium dava
  timeout (confirmado: 0 elementos via `find_elements` normal, 1 elemento
  via `barra.shadow_root.find_element(...)`). `_clicavel_no_shadow` em
  `fluxo.py` existe só por causa disso — se voltar a dar timeout nesse
  primeiro clique, confirme no DevTools (aba Elements) se o botão ainda
  está dentro de `<barra-govbr>` `#shadow-root` e se `selectors.
  HOST_BARRA_GOVBR` (`barra-govbr`) ainda é a tag certa.
- `#login-certificate` (segundo clique) já está em DOM normal — sem
  Shadow DOM — porque é uma página diferente (`sso.acesso.gov.br/login`,
  fora do `<barra-govbr>`).
- O gov.br é feito em Svelte com classes com hash (`svelte-qdqhy1` etc.) que
  mudam a cada deploy — por isso `selectors.BTN_ENTRAR` usa só a classe
  semântica `.br-sign-in` (sem o hash) e `selectors.BTN_LOGIN_CERTIFICADO`
  usa o `id` (`#login-certificate`, mais estável que classe). Se algum dos
  dois parou de casar, inspecione o elemento no site (F12, lembrando de
  abrir o shadow root pra achar o primeiro) e atualize o seletor em
  `src/selectors.py` — nunca inline em `fluxo.py`.
- `_logar_via_govbr` espera `document.readyState == 'complete'` depois de
  cada clique — em SPA isso pode retornar "completo" antes do conteúdo
  real renderizar. Se o clique seguinte falhar por elemento ainda não
  existir, aumente `navegador.timeout_ms` primeiro; se persistir, pode ser
  necessário trocar a espera por uma condição mais específica (esperar o
  elemento do próximo passo aparecer, em vez do readyState).

## `undetected_chromedriver` não abre / erro de versão do Chrome

- Precisa do Google Chrome instalado (a lib patcheia o Chrome existente, não
  baixa um Chromium). Atualize o Chrome se a versão estiver muito nova/velha
  em relação ao pacote instalado.

## Ainda cai em captcha / bloqueio do gov.br

- Evite `navegador.headless: true` — headless no `undetected-chromedriver`
  ainda é WIP e reduz bastante o efeito stealth.
- Rode a máquina com um perfil "limpo" (sem extensões suspeitas) — fingerprint
  de extensões também é sinal usado por bot-detection.

## Navegador abre mas fica em branco / trava

- Aumente `navegador.timeout_ms` em `config.yaml`.
- Rode com `navegador.headless: false` (padrão) para ver o que está
  acontecendo na tela.

## Regularize (PGFN) — descoberta ao vivo (FASE 0 do fluxo de relatórios)

Confirmado em execução real (login com certificado de VICTOR HUGO SOUZA
MEDEIROS, perfil trocado pro CNPJ 17462219000105) em 2026-08-10:

- **A troca de perfil (`#txtNIPapel2` / `input.submit[value="Alterar"]`)
  acontece no e-CAC, não no Regularize.** No e-CAC autenticado, clique em
  "Alterar perfil de acesso" (canto superior direito) — abre um modal com
  3 opções, cada uma com seu próprio input e botão "Alterar":
  1. "Responsável Legal do CNPJ perante a RFB" → `#txtNIPapel`
  2. "Procurador de pessoa física - CPF" → `#txtNIPapel1`
  3. "Procurador de pessoa jurídica - CNPJ" → `#txtNIPapel2` ← este é o
     documentado no `prompt.md`, confirmado certo. Os 3 inputs têm
     `name="NIPapel"` igual — só o `id` diferencia. Os 3 botões "Alterar"
     não têm `id`; localize o botão certo por ordem no DOM (`following::`
     a partir do input, primeiro `input.submit[value="Alterar"]` depois
     dele) — não têm `fieldset` ancestor comum pra usar como contexto.
  - Depois de mudar o perfil no e-CAC, a sessão é reconhecida pelo
    Regularize (mesma sessão/SSO) — não é preciso repetir a troca de CNPJ
    dentro do próprio Regularize.
  - O `prompt.md` original descrevia esse passo como parte do fluxo do
    Regularize; na prática é um passo do e-CAC que acontece antes.

- ⚠️ **BLOQUEIO DE AUTOMAÇÃO CONFIRMADO:** ao preencher `#txtNIPapel2` via
  Selenium (mesmo em modo *attach* via `debuggerAddress`, sem o navegador
  ter sido lançado pelo WebDriver) e clicar no botão "Alterar" por
  `.click()`, o e-CAC respondeu: *"Prezado usuário, o seu acesso foi
  bloqueado por possuir atributos que o caracteriza como um acesso
  automatizado."* — a Receita Federal detecta e bloqueia esse clique
  especificamente, não só navegação automatizada ponta-a-ponta. Refazer o
  mesmo clique manualmente (usuário real) funcionou sem bloqueio.
  **Implicação para a automação do `prompt.md`:** qualquer clique dentro do
  e-CAC/Regularize pode estar sujeito a essa mesma detecção — antes de
  automatizar cliques em massa (ex.: "Detalhar" em cada inscrição,
  "Gerar relatório detalhado"), validar um a um se o mesmo bloqueio ocorre.
  Se ocorrer de forma consistente, pode ser necessário manter a troca de
  perfil e/ou outros cliques sensíveis como passo manual do operador,
  mesmo com o restante do fluxo automatizado.
- Reconexão via `debuggerAddress` (Chrome aberto fora do Selenium/UC, com
  `--remote-debugging-port`) não fecha o navegador quando o script Python
  termina — diferente de `undetected_chromedriver`, cujo `Chrome.__del__`
  chama `quit()` e mata o processo ao sair de escopo. Útil pra inspeção
  read-only entre passos manuais sem precisar manter um processo Python
  vivo o tempo todo.
- Abas criadas via `driver.switch_to.new_window("tab")` (Selenium) somem
  quando a sessão que as criou desconecta — usar
  `driver.execute_cdp_cmd("Target.createTarget", {"url": ...})` em vez
  disso pra abas que precisam sobreviver além do script que as abriu.

## Regularize — FASE 1 é sempre manual (login + troca de perfil)

Confirmado em execução real de produção (`python -m src.main --regularize
<CNPJ>`) em 2026-08-10: **não automatizar nada do login nem da troca de
perfil.** `regularize.autenticar_e_trocar_perfil` só abre uma aba em
branco (`driver.switch_to.new_window("tab")`, sem navegar) e pausa em
`input()` — o operador faz manualmente: gov.br → Entrar → certificado →
captcha (se aparecer) → abrir e-CAC → "Alterar perfil de acesso" → CNPJ →
Alterar → captcha (se aparecer). Dois motivos, os dois confirmados ao
vivo, não teóricos:
1. **Login automático por certificado tem corrida.** `_logar_via_govbr`
   clica em "Seu certificado digital" e só espera `readyState ==
   'complete'`, que fica satisfeito antes do handshake mTLS terminar de
   verdade — o e-CAC abre na tela de login, não autenticado, se o próximo
   passo (`driver.get` de outra URL) roda rápido demais.
2. **A troca de perfil é bloqueada como acesso automatizado** (ver seção
   acima) — não tem workaround, é sempre manual.

Depois que o operador confirma (`input()`), `entrar_no_regularize_via_ecac`
assume a partir do e-CAC: clica em "Dívida Ativa da União" (menu do
e-CAC) → "PGFN - Todos os serviços do Regularize" — **não** navega direto
pra URL do Regularize. Motivo: `driver.get` direto em
`URL_REGULARIZE_CONSULTA_DIVIDAS` (ou até na raiz) às vezes é redirecionado
de volta pra `/` num carregamento a frio, mesmo autenticado — parece a
guarda de rota da SPA não reconhecer a sessão a tempo. `ir_para_consulta_dividas`
(em `regularize.py`) tenta de novo até 3x quando isso acontece; usada em
toda navegação subsequente pra `/consultaDividas` (enumeração, cada
relatório detalhado, reabertura de aba).

**A partir de 2026-08-11, `entrar_no_regularize_via_ecac` roda num
segundo navegador (headless), não mais no mesmo navegador do login
manual** — ver seção seguinte.

## Regularize — sessão headless via cookies (a partir da FASE 2)

Confirmado ao vivo em 2026-08-11 (`teste_cookies_headless.py`, cookies
exportados de uma aba já autenticada no e-CAC): subir um Chrome headless
via `undetected_chromedriver`, navegar pra `selectors.URL_ECAC`, injetar
os cookies com `driver.add_cookie(...)` um a um e navegar pro e-CAC de
novo é suficiente pra herdar a sessão autenticada — achou "Alterar perfil
de acesso" na página, sem disparar o bloqueio de "acesso automatizado".

**Por que isso não viola a regra de FASE 1 manual:** nenhum login nem
clique de troca de perfil é automatizado — a sessão continua sendo
autenticada por um humano, só que num navegador diferente do que roda o
resto do fluxo.

**Arquitetura atual (`main.executar_regularize`):**
1. Abre navegador #1 (`fluxo.abrir_navegador_com_certificado(..., headless=False)` —
   sempre visível, ignora `config.navegador.headless`) e
   `regularize.autenticar_e_trocar_perfil` pausa em `input()` pro operador
   fazer login + troca de perfil manualmente, exatamente como antes.
2. Ao confirmar, a função captura `driver.get_cookies()` da aba do e-CAC e
   retorna a lista — `main.py` fecha o navegador #1 e remove a policy de
   certificado (não é mais necessária).
3. Abre navegador #2 (`fluxo.abrir_navegador_com_cookies`, sempre
   headless) e injeta os cookies capturados.
4. `regularize.confirmar_sessao_headless_autenticada` confere se "Alterar
   perfil de acesso" aparece antes de seguir — se não aparecer, levanta
   erro (cookies expirados ou presos a outro IP) em vez de continuar e
   gerar relatórios vazios/errados em silêncio.
5. Segue o fluxo normal (`entrar_no_regularize_via_ecac`, FASE 2, FASE 3)
   no navegador #2.

**Riscos conhecidos, sem workaround:**
- Os cookies `TS*` (F5 BIG-IP) costumam embutir o IP de origem — só
  funciona rodando da mesma rede/IP de onde a FASE 1 manual aconteceu.
  Não adianta capturar os cookies numa máquina e rodar o headless noutra.
- São cookies de sessão (sem `expiry`) — expiram, então cada execução
  precisa repetir a FASE 1 manual pra gerar cookies novos. Isso não vira
  uma automação "rode a qualquer hora sem supervisão": o operador ainda
  faz login + troca de perfil toda vez, só não fica esperando o resto do
  fluxo (PDFs) numa janela visível.
- `config.navegador.headless` agora só afeta o fluxo simples de
  `python -m src.main` (sem `--regularize`) — no fluxo Regularize os dois
  navegadores têm headless fixo, independente do que estiver no
  `config.yaml`: visível no #1 (sempre foi) e, **a partir de 2026-08-11,
  também visível no #2** (`fluxo.abrir_navegador_com_cookies`) — mudança
  deliberada pra acompanhar visualmente a FASE 4/5 (SISPAR/CAPAG,
  recém-implementadas, ver seção abaixo) enquanto validamos ao vivo. Se
  quiser headless de volta no #2 pra uso normal depois de validado, reverta
  o comentário `ponytail:` em `abrir_navegador_com_cookies`.

**`--aguardar-sinal`** (`main.py`, não usar em produção): troca o `input()`
da FASE 1 por uma espera pelo arquivo `artifacts/continuar_fase1.flag` —
necessário quando quem inicia o processo não tem stdin interativo de
verdade pra receber o Enter (ex.: `/rodar-regularize`, ver
`.claude/commands/rodar-regularize.md`). **Não é detecção automática pela
página** — alguém cria esse arquivo manualmente (ou pede pro Claude criar)
só depois de confirmar a troca de perfil de verdade. Login e troca de
perfil continuam 100% manuais nos dois casos (`--aguardar-sinal` ou não) —
só muda como o código é avisado que o operador terminou.

⚠️ **Risco real, já aconteceu em produção (2026-08-11)**: quem estiver
acompanhando o chat (ex.: Claude via `/rodar-regularize`) só deve criar o
arquivo de sinal depois de o operador confirmar EXPLICITAMENTE que a
troca de perfil terminou — uma confirmação ambígua ("siga", sem
contexto) levou a criar o sinal cedo demais, com o perfil ainda no
CNPJ/CPF anterior. O processo não trava nem avisa alto: só loga
`perfil_confirmado` com `encontrado_na_pagina: false` e segue adiante,
gerando relatórios pro perfil ERRADO (confirmado ao vivo: SISPAR saiu
com 0 parcelamentos e o CAPAG saiu com a fórmula de pessoa física em vez
da empresa). **Sempre conferir esse campo no trace logo depois de criar o
sinal** — se vier `false`, avisar e não confiar nos PDFs daquela
execução.

**`--limit N`** (`python -m src.main --regularize <CNPJ> --limit N`) trunca
a quantidade de relatórios detalhados gerados na FASE 3, preservando a
ordem das abas — útil pra validar rápido que a sessão headless via
cookies está gerando PDFs corretos antes de rodar tudo (ex.: `--limit 10`
antes de deixar rodar as ~77 inscrições completas).

## Regularize — `_clicavel_no_shadow` derrubava o login com StaleElementReferenceException

`WebDriverWait.until()` só re-tenta sozinho em `NoSuchElementException`
por padrão — um `StaleElementReferenceException` no meio do polling (ex.:
o elemento do Shadow DOM troca entre o `find_element` e o
`is_displayed()`) derruba a espera inteira em vez de só tentar de novo.
Corrigido em `fluxo._clicavel_no_shadow`: a `condicao` interna agora
captura `NoSuchElementException`/`StaleElementReferenceException` e
retorna `False` (ou seja, "ainda não", continua esperando) em vez de
deixar a exceção subir. Mesmo padrão de bug apareceu depois em
`regularize.py` ao clicar em "Detalhar" (a `<tr>` da inscrição ficava
stale entre localizá-la e clicar no link de dentro dela) — corrigido
refazendo a busca da linha do zero a cada tentativa, não só o clique.

## Regularize — nunca clicar em "Imprimir"

No relatório consolidado e no detalhado, o botão "Imprimir" dispara
`window.print()` nativo do Chrome, que abre uma aba `chrome://print/` e
**bloqueia a aba original via JS** até essa aba de preview ser fechada —
qualquer `execute_script`/`.click()` subsequente na aba original trava
até dar timeout. A captura do PDF via CDP (`Page.printToPDF`) não passa
pela thread de JS da página, então não precisa do "Imprimir" nem do
"preparar pra impressão" que ele dispararia — o fluxo clica só em
"Exportar" (consolidado) e espera o "Imprimir" **aparecer** como sinal de
que a página terminou de montar a view exportável, mas nunca clica nele.
Se uma aba `chrome://print/` aparecer sozinha (indício de que algum
código clicou em Imprimir por engano), feche-a (`driver.close()` depois
de trocar pra ela) — a aba original volta a responder.

## Regularize — texto sobreposto no PDF de relatório detalhado (poucos débitos)

Cada painel de débito expandido anima (transição CSS) e sua posição final
na página é calculada no momento do clique. Clicar no próximo "expandir"
antes da transição do anterior terminar faz o cálculo da posição do
próximo usar a altura ainda errada (não expandida) dos anteriores —
resultado: texto de vários débitos sobreposto na mesma posição no PDF.
Só aparecia em relatórios com **poucos** débitos (que terminam de clicar
rápido demais pra a UI acompanhar); com muitos débitos, o tempo entre
cliques já dava folga suficiente por acaso. Corrigido em
`_clicar_todos_expandir`: depois de cada clique confirmado, espera
`document.getAnimations().length == 0` (timeout curto, 5s, com fallback
silencioso) antes de clicar no próximo — não só antes de gerar o PDF no
final.

## Referência — totais reais confirmados (URB TOPO ENGENHARIA, CNPJ 17462219000105)

Pra validar rapidamente se uma nova execução está batendo, sem precisar
reconferir ao vivo: em 2026-08-10, **77 inscrições** ativas em Dívida
Ativa da União + FGTS, R$ 29.068.095,22 no total, quebradas por aba como
Tributária 32 (1 extinta) / Não Tributária 17 / Previdenciária 24 / FGTS
4. Esses números mudam com o tempo (novas inscrições, pagamentos) — não
são um valor fixo esperado pra sempre, só a última referência conhecida.

## `navegador.timeout_ms` baixo demais pro fluxo do Regularize

30000 (padrão original, pensado só pro login no e-CAC) se mostrou
insuficiente pro fluxo de relatórios — subiu pra 60000 em `config.yaml`.
Esse valor vira o `timeout_s` de toda espera em `regularize.py`
(`esperar_spinner_sumir`, `esperar_elemento`, `ir_para_consulta_dividas`,
o timeout total por tentativa de relatório detalhado via `_com_timeout` é
`timeout_s * 2`). Se voltar a dar timeout num relatório com muitos
débitos/inscrições, suba mais antes de investigar outra causa.

## SISPAR (parcelamentos) / CAPAG — implementado e validado ao vivo

Implementado em 2026-08-11 a partir de `docs/imp/capag.md`, seguindo o
padrão de `regularize.py` (Logger, `_clicar`, `esperar_elemento`,
`salvar_pdf`). Levou várias rodadas de execução real (login manual +
`--aguardar-sinal`, ver seção logo abaixo) até fechar de vez — histórico
completo abaixo, útil se algo parecido quebrar de novo no futuro (ex.:
o site mudando). Estado atual, confirmado ao vivo em 2026-08-11 abrindo
os PDFs gerados (não só olhando o log):

- `checkpoint_sispar_ok total=8` — todos os parcelamentos, nome do
  arquivo batendo com o conteúdo.
- `checkpoint_capag_ok` — sem aviso de cookies, sem diálogo de
  "processamento" sobrando, com o texto real (inclusive o caso "omisso").

**Bug de layout achado depois, comparando screenshot do PDF salvo com a
página real (2026-08-11)**: as tabelas do PARCELAMENTO (Pagamentos,
Prestações, Créditos Informados) são mais largas que o papel padrão do
`Page.printToPDF` (Letter, 8.5"x11") — colunas da direita (`Encargos/
Honorários`, `Total`, etc.) ficavam cortadas fora da página. `checkpoint_
sispar_ok`/`checkpoint_capag_ok` e a conferência de texto (cookie/
processamento/nome-bate-com-conteúdo) não pegam isso — é um corte visual
de LARGURA, não de conteúdo ausente no texto. Corrigido: `salvar_pdf`
agora aceita `**opcoes_impressao` repassadas pro CDP `Page.printToPDF`;
os saves de `PARCELAMENTO-*.pdf` e `CAPAG_*.pdf` usam
`paperWidth=17, paperHeight=11` (o dobro da largura padrão) — os saves do
Regularize (Consolidado/Detalhado) continuam sem opção nenhuma,
inalterados, porque nunca teve esse problema relatado.

**RESOLVIDO — confirmado ao vivo (2026-08-11)**: `mediabox` do PDF
confere 17"x11" de verdade (não só o parâmetro passado), e a tabela mais
larga observada (Débitos, mesma classe de largura das que cortavam)
saiu com todas as colunas, incluindo `Encargos/Honorários` e `Valor
Total`. Se ainda cortar algo no futuro (tabela ainda mais larga), subir
`paperWidth` mais antes de investigar outra causa.

Se voltar a falhar (o site pode mudar), comece por aqui, na ordem de risco:

- **`/sispar/sisparnet` embute o simulador SISPAR (outro domínio,
  `pro-frontend-simulador-sispar.estaleiro.serpro.gov.br`) dentro de um
  `<iframe id="sisparFrame">` — confirmado ao vivo em 2026-08-11
  (`docs/pag_exemples/Regularize_consultar.htm` +
  `Regularize_consultar_files/home_qAYj.htm`, esta última é a cópia do
  DOM do iframe salva separadamente pelo Chrome).** `regularize.
  ir_para_sispar` já corrigido: usa `EC.frame_to_be_available_and_switch_to_it`
  antes de procurar o card. `selectors.XPATH_CARD_CONSULTAR` (`.place-info-box-text`
  == "CONSULTAR") e `IMG_CARD_CONSULTAR` estão confirmados contra o
  `home_qAYj.htm` real — se voltar a não achar o elemento, confira
  primeiro se o `driver` está mesmo dentro do iframe (`driver.
  switch_to.default_content()` seguido de nova troca de frame) antes de
  suspeitar do texto/classe.
- ~~`selectors.XPATH_BTN_CONTINUAR_SISPAR`~~ — confirmado ao vivo em
  2026-08-11 (`python -m src.main --regularize 17462219000105 --limit 1`):
  card → Continuar → nova aba em
  `sisparInternet/autenticacao.jsf?token=...&simulador=true` funcionou.
  `coletar_parcelamentos` também confirmado: 8 parcelamentos, mesmos
  números do `parcelamentos.htm` (140463, 355617, 1556844, 1590391,
  1556494, 6756347, 6782840, 6816837).
- **SISPAR/parcelamentos — RESOLVIDO e confirmado ao vivo (2026-08-11,
  5ª execução): `checkpoint_sispar_ok total=8`, 8/8 PDFs, zero
  `DIVERGENCIA`.** Também confirmado abrindo cada um dos 8 PDFs: nome do
  arquivo bate com o número da negociação no conteúdo (o descompasso
  nome/conteúdo relatado abaixo não aconteceu mais nenhuma vez). Histórico
  completo do bug, pra quem for investigar algo parecido no futuro:
  linha/botão "Consulta", **reproduzido de forma IDÊNTICA em 3 execuções
  reais separadas** — sempre falham os mesmos 7 de 8 parcelamentos (todos
  exceto o último da lista, `6816837`), na mesma ordem, mesmo com:
  (1) retry de 3 tentativas re-buscando a linha do zero a cada uma; (2)
  `gerar_relatorios_parcelamentos` em 2 rodadas, dando tempo real (~25s)
  entre a 1ª e a 2ª tentativa dos mesmos itens — **e falhou igual nas
  duas rodadas**, o que descarta de vez a hipótese de "instabilidade
  inicial que passa com tempo" (`countDown()` etc.) — é determinístico
  por item, não uma race que tempo/retry resolve. Aplicada uma 3ª
  correção: `_botao_consulta_habilitado` reconsultava o elemento a cada
  poll do `WebDriverWait`, mas SEM capturar `StaleElementReferenceException`
  gerada dentro do próprio poll (entre `find_elements` e `get_attribute`
  na mesma chamada) — WebDriverWait não re-tenta esse erro por padrão
  (mesma lacuna já documentada e corrigida antes em
  `fluxo._clicavel_no_shadow`, só não tinha sido replicada aqui).
  Adicionado também log granular (`stale na etapa '<nome>'...`) pra, se
  isso ainda não bastar, a próxima falha apontar exatamente qual linha de
  código (localizar linha / clicar linha / esperar botão / clicar botão)
  está estourando.

  **O log granular (4ª execução) finalmente apontou o ponto exato: sempre
  na etapa `clicar_botao_consulta`, nunca na espera.** O elemento fica
  stale bem na janela entre o comando de CLIQUE do Selenium (`find` +
  `click` são 2 comandos WebDriver separados, com round-trip no meio) e o
  navegador executar — por isso nem tempo nem retry por fora dessa janela
  ajudavam, a mesma janela reabre a cada tentativa. Corrigido com
  `_clicar_via_js_xpath`: localiza E clica numa ÚNICA chamada
  `execute_script` (via `document.evaluate` + `.click()`), sem round-trip
  nenhum entre os dois — usado só nesse ponto específico, não em todo
  clique do módulo. **Confirmado que resolveu (5ª execução, ver acima).**

  Achado extra que veio de bônus: numa execução em que só o último item
  "funcionava" (antes do fix), o PDF `PARCELAMENTO-6816837.pdf` continha
  o conteúdo do parcelamento **6782840** (o item anterior) — nome do
  arquivo não batia com o conteúdo (suspeita: a seleção de linha do item
  anterior, que falhava do nosso lado, registrava no servidor mesmo
  assim). **Esse descompasso não voltou a acontecer** depois do fix do
  clique atômico — confirmado abrindo os 8 PDFs da execução de sucesso.
- **CAPAG — bug real encontrado e corrigido (2026-08-11), confirmado ao
  vivo depois do fix (checkpoint_capag_ok)**, causa confirmada contra
  `docs/pag_exemples/capagPesquisa.htm`: o fieldset "Valores para
  cálculo da capacidade de pagamento individual" fica ANINHADO dentro de
  outro fieldset não-toggleable ("Capacidade de Pagamento"). O XPath
  antigo (`//fieldset[.//legend[contains(...)]]`) casava os DOIS (o
  ancestral também "contém" a legend como descendente) e, em ordem de
  documento, `find_element` retornava o fieldset EXTERNO — sem toggler,
  clique sem efeito nenhum, daí o `TimeoutException` esperando o ícone
  mudar. Corrigido selecionando direto por `.ui-fieldset-toggleable`
  (confirmado: só existe UM elemento com essa classe na página inteira —
  não precisa de XPath ancestral pra achar a legend certa). Esse fixture
  também é o exemplo real do caso "omisso" do `capag.md`: "A consulta a
  esses dados não está disponível em razão do enquadramento na situação
  de omisso." — captura normalmente, sem quebrar o fluxo.
- **CAPAG — 2 bugs de conteúdo confirmados abrindo o PDF gerado, não só
  conferindo se `checkpoint_capag_ok` apareceu (2026-08-11)**:
  1. Aviso de cookies do PGFN ("Para melhorar a sua experiência...
     Permitir Rejeitar") sobrava no texto extraído do PDF — a página é
     JSF com recarga completa a cada navegação (sem SPA), então o aviso
     pode reaparecer em qualquer página nova. Corrigido com
     `regularize._dispensar_aviso_cookies` (clica em "Permitir" se
     visível, melhor esforço, nunca quebra o fluxo se não achar) —
     chamado antes de cada `salvar_pdf` do SISPAR/CAPAG.
  2. A frase "A consulta a esses dados não está disponível..." (conteúdo
     real do fieldset, confirmado presente via `fieldset.text` no log)
     **não aparecia no texto do PDF** — o ícone do fieldset virava
     "expandido" um instante antes do navegador terminar de pintar o
     conteúdo, e como esse caso não tem placeholder AJAX pra esperar
     sumir, a espera existente não esperava nada de verdade. Corrigido em
     `_expandir_um_fieldset`: espera extra até o texto do fieldset ficar
     maior que só a legend, antes de considerar expandido.

  **Revalidado ao vivo (2026-08-11, execução seguinte)**: o item 1 (aviso
  de cookies) sumiu de vez, confirmado. O item 2 **continuou faltando**
  mesmo com a espera por "texto maior que a legend" — esse fieldset em
  particular é pequeno/rápido demais, o wait resolve antes do repaint
  real acontecer. Ponytail: adicionado um reflow forçado
  (`document.body.offsetHeight`) + `time.sleep(0.3)` fixo no final de
  `_expandir_um_fieldset`, sem condição JS confiável encontrada pra
  esperar "terminou de pintar" de verdade.

  **Causa raiz de verdade, achada quando o usuário reportou "Solicitação
  em processamento..." aparecendo na tela de alguns relatórios**: as
  páginas JSF do SISPAR/CAPAG têm o MESMO padrão do `app-spinner` do
  Angular — `#statusAguarde` ("Aguarde / Solicitação em processamento...",
  confirmado em `parcelamentos.htm` E `parcelamento_consolidado.htm`)
  fica no DOM sempre (`display:block`), só a visibilidade muda durante um
  AJAX. Nenhum dos waits anteriores (ícone, regex, texto-maior-que-legend,
  animações, reflow+sleep) checava isso — o código podia perfeitamente
  imprimir com esse diálogo ainda visível. Adicionado
  `regularize.esperar_aguarde_jsf_sumir` (mesmo padrão de
  `esperar_spinner_sumir`) chamado: (1) dentro de
  `_expandir_um_fieldset`, logo após o clique na legend; (2) depois do
  clique em "Consulta" (antes de expandir os fieldsets do parcelamento);
  (3) depois do clique em "Pesquisar" do CAPAG; (4) bem antes de cada
  `salvar_pdf` do SISPAR/CAPAG, como rede de segurança final.

  **RESOLVIDO — confirmado ao vivo (2026-08-11, execução seguinte), abrindo
  os PDFs de verdade, não só o log**: os 8 `PARCELAMENTO-*.pdf` e o
  `CAPAG_*.pdf` saíram sem "processamento" (aguarde), sem aviso de
  cookies, com a frase do "omisso" presente, e nome batendo com conteúdo
  em todos. `checkpoint_sispar_ok total=8` + `checkpoint_capag_ok`. SISPAR
  e CAPAG estão funcionando de ponta a ponta.
- `selectors.TOGGLER_COLAPSADO` (`.ui-fieldset-toggler.ui-icon-plusthick`)
  assume o padrão clássico do PrimeFaces (ícone alterna plusthick/
  minusthick) — confirmado contra `parcelamento_consolidado.htm` E
  `capagPesquisa.htm`, os dois batem.
- `regularize._REGEX_CARREGANDO` (`r"Consultando\b.*\.\.\."`) casa com os
  4 placeholders vistos na fixture ("Consultando créditos informados...",
  "pagamentos...", "Prestações...", "ocorrências...") — se a página real
  tiver um placeholder com texto diferente, a espera ainda funciona (só
  não vai encontrar o padrão e resolve na hora), mas pode não estar
  esperando o AJAX real terminar.
- `selectors.TR_LINHA_PARCELAMENTO` (`tr.conteudoGrid`) e a extração das 7
  colunas em `coletar_parcelamentos` assumem a ordem exata de
  `parcelamentos.htm` (Vinculação, Negociações, Modalidade, Número da
  Conta, Situação, Data Adesão, Valor Consolidado) — se a ordem mudar
  entre CPF/CNPJ com múltiplos grupos (`grupoCpfCnpj:0`, `:1`, ...), pode
  ser necessário também iterar sobre múltiplos `tbody` em vez de um só.

**Como validar**: `python -m src.main --regularize <CNPJ> --limit 1`, num
terminal interativo de verdade (não via automação/CI) — `--limit 1` já
reduz a FASE 3 ao mínimo (mas a FASE 2, consolidado, sempre roda);
acompanhe `artifacts/traces/regularize_*.jsonl` em outro shell. Checagem
de sucesso: nº de parcelamentos coletados == nº de `PARCELAMENTO-*.pdf`
gerados (evento `checkpoint_sispar_ok`), e `checkpoint_capag_ok` presente.

## `zoneinfo`/`America/Sao_Paulo` falha no Windows sem `tzdata`

`from zoneinfo import ZoneInfo; ZoneInfo("America/Sao_Paulo")` dá
`ZoneInfoNotFoundError` em Python no Windows — o Windows não vem com o
banco de fusos IANA que o `zoneinfo` da stdlib espera achar. `tzdata`
(pacote pip da própria equipe do Python, só dados, sem código) resolve;
já está em `requirements.txt`.
