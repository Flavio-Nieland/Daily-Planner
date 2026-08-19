# Worker do estado

Recebe o que o Flávio escreve na edição e guarda no KV. O build do dia seguinte lê tudo e
consolida no `estado.json` versionado no git — o KV é buffer, não fonte da verdade.

## Deploy (uma vez)

```bash
npm install -g wrangler
wrangler login

cd worker
wrangler kv namespace create ESTADO      # cole o id devolvido no wrangler.toml
wrangler secret put TOKEN                # invente uma senha longa; é a que você digita no navegador
wrangler deploy
```

O `wrangler deploy` imprime a URL (algo como `https://diario-estado.SEU-SUBDOMINIO.workers.dev`).

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
