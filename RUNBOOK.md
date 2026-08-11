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
  navegadores têm headless fixo (visível no #1, headless no #2),
  independente do que estiver no `config.yaml`.

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

## `zoneinfo`/`America/Sao_Paulo` falha no Windows sem `tzdata`

`from zoneinfo import ZoneInfo; ZoneInfo("America/Sao_Paulo")` dá
`ZoneInfoNotFoundError` em Python no Windows — o Windows não vem com o
banco de fusos IANA que o `zoneinfo` da stdlib espera achar. `tzdata`
(pacote pip da própria equipe do Python, só dados, sem código) resolve;
já está em `requirements.txt`.
