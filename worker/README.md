# Worker do estado

Recebe o que o Flávio escreve na edição e guarda no KV. O build do dia seguinte lê tudo e
consolida no `estado.json` versionado no git — o KV é buffer, não fonte da verdade.

## No ar

- Worker: **https://estado.diario-flavio-nieland.workers.dev**
- Conta: `flavionieland1@gmail.com` · KV `ESTADO` = `e2b625570e5c49258ae77b5637e30b15`
- Secrets `WORKER_URL` e `WORKER_TOKEN` já criados no repositório.
- O token está em `~/.config/diario-token.txt` (fora do repositório, 600) — é o que se cola
  no navegador na primeira gravação. Para trocar: `wrangler secret put TOKEN --name estado`
  e `gh secret set WORKER_TOKEN`.

## Deploy (como foi feito)

```bash
npm install -g wrangler
wrangler login

cd worker
wrangler kv namespace create ESTADO      # cole o id devolvido no wrangler.toml
wrangler secret put TOKEN                # a senha que você digita no navegador
wrangler deploy
```

O `wrangler deploy` imprime a URL. Uma conta nova precisa registrar antes o subdomínio
`workers.dev` — o certificado dele leva alguns minutos para começar a responder.

## Depois do deploy

1. No repositório, crie os secrets `WORKER_URL` e `WORKER_TOKEN` com a URL e o token:
   ```bash
   gh secret set WORKER_URL --body "https://diario-estado.SEU-SUBDOMINIO.workers.dev"
   gh secret set WORKER_TOKEN --body "o-token-que-você-inventou"
   ```
2. Abra a edição, clique em registrar o peso e cole o token quando ele for pedido. Ele fica
   no `localStorage` do seu navegador — nunca no HTML publicado, que é público.

## API

| | |
|---|---|
| `GET /estado` | devolve o estado inteiro (usado pelo build) |
| `POST /estado` | `{"secao":"peso","chave":"2026-08-19","valor":78.4}` |

As duas exigem `Authorization: Bearer <token>`. Registrar duas vezes na mesma chave deixa
o último valor.
