# Instalar este projeto como skill do Claude Code

Instrução padrão pra você (Claude Code) instalar o plugin `ecac-regularize`
(este repositório) em qualquer máquina/projeto e continuar se comportando
exatamente como quando roda aqui dentro. Leia isto quando o usuário pedir
algo como "instala esse projeto como skill", "quero o robô do e-CAC nessa
máquina também" ou similar.

## Instalar (primeira vez)

```
git clone https://github.com/ittsjoao/reguraliza-scrapper.git ~/.claude/skills/ecac-regularize
```

Sem passo de marketplace nenhum. Na próxima sessão o Claude Code carrega
automaticamente como `ecac-regularize@skills-dir`, com dois comandos:

- `/ecac-regularize:rodar-regularize <CNPJ> [--limit N]`
- `/ecac-regularize:atualizar-repo`

## Comportamento — sempre igual ao repositório original

Este plugin não tem regra própria separada: `commands/rodar-regularize.md` e
`commands/atualizar-repo.md` já carregam toda a instrução de comportamento
(o que pode automatizar, o que é sempre manual, onde ficam os outputs) e
começam com `cd "${CLAUDE_PLUGIN_ROOT}"` — rodam de forma idêntica estando
aqui, em `~/.claude/skills/ecac-regularize`, ou em qualquer outra máquina.
Não invente comportamento diferente por estar "fora" do repositório
original; se uma instrução parecer incompleta ou desatualizada, é bug no
próprio `commands/*.md` — corrija lá, não no comportamento ad-hoc.

## Atualizar — origin/main é a única fonte da verdade

Nunca atualize essa cópia manualmente com `git pull`/merge/stash. Use
sempre `/ecac-regularize:atualizar-repo`, que roda:

```
git fetch origin
git reset --hard origin/main
git clean -fd
```

Deliberadamente destrutivo: sobrescreve qualquer commit, edição ou arquivo
local não rastreado (fora do `.gitignore`) sem perguntar. Uma cópia
instalada como skill nunca deve acumular edição própria — pra mudar
comportamento, mude no repositório
(`https://github.com/ittsjoao/reguraliza-scrapper`) e rode
`/ecac-regularize:atualizar-repo` de novo em cada máquina.

**Excção:** se `${CLAUDE_PLUGIN_ROOT}` for o repositório de desenvolvimento
(onde alguém edita e commita — ex.: este mesmo diretório ao trabalhar no
projeto), avise antes de rodar `/atualizar-repo`: qualquer coisa não
enviada a `origin/main` será perdida sem aviso.
