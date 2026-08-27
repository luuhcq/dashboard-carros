# CLAUDE.md

## Commit messages

All commit messages follow [Conventional Commits](https://www.conventionalcommits.org/), written in English, always with a type prefix (`feat:`, `fix:`, `test:`, `docs:`, `chore:`, etc.) — no exceptions, including intermediate/summary commits.

## Language

Summaries and free-text communication with the user: always in Portuguese. Commit messages: always in English, Conventional Commits (see rule above, unchanged).

## Divergências conhecidas no histórico de commits

- **`c928ca8`** — a mensagem do commit ("fix: prevent asking_price/sale_price edits via Admin bypassing audit log") não corresponde ao diff real: o conteúdo de `c928ca8` é o rename `aging` → `days_in_stock` em `vehicles/serializers.py`. A correção de Admin que a mensagem descreve existe de fato no código, mas está em **`37158cf`** — as duas mensagens foram trocadas por um erro de staging numa sessão anterior (ex.: `git add -p`/staging seletivo aplicado ao commit errado). Não é um bug funcional, só um rótulo errado num commit já publicado.
  - Histórico publicado não foi reescrito de propósito (reescrever/force-push sobre commits já no remoto é destrutivo). Quem for investigar a correção de asking_price/sale_price via Admin deve olhar `37158cf`, não `c928ca8`, apesar da mensagem deste último sugerir o contrário.
