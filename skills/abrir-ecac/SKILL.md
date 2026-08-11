---
description: Abre o navegador já autenticado por certificado digital A1 no e-CAC (gov.br), sem gerar relatório nenhum. Use quando o usuário só quiser logar/abrir o e-CAC pra continuar manualmente, sem pedir relatório do Regularize/PGFN.
---

# Abrir e-CAC autenticado

Roda o modo simples do CLI: lista os certificados válidos do Windows
Certificate Store, deixa o usuário escolher um (ou usa `certificado.
cn_padrao` de `config.yaml` se só houver um casando), loga via gov.br e
abre o e-CAC numa aba nova. Deixa o navegador aberto pro usuário continuar
manualmente — não faz mais nada sozinho.

## Comando

```
cd "${CLAUDE_PLUGIN_ROOT}"
python -m src.main
```

Isso é interativo (menu de setas pra escolher certificado, se houver mais
de um casando com `config.yaml`, e um `input()` no final antes de fechar o
navegador) — rode num terminal de verdade do usuário, não numa ferramenta
de shell não-interativa.

Se o usuário quiser os relatórios de dívida ativa (Regularize/PGFN) de um
CNPJ, não é este skill — use `gerar-relatorio-regularize`.
