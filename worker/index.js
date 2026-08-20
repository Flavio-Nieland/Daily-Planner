/* Worker que recebe o que o Flávio escreve na edição e guarda no KV.

   O KV é buffer, não fonte da verdade: o build do dia seguinte consolida tudo no
   estado.json versionado no git. Se o KV sumir, perde-se no máximo um dia de marcações
   (ADR 0003). O site é público, então nenhum token vive no HTML — ele digita uma vez no
   navegador e o valor fica no localStorage dele. */

import { aplicar, valido } from "./merge.js";

const CHAVE = "estado";

const cors = (origem) => ({
  "Access-Control-Allow-Origin": origem,
  "Access-Control-Allow-Methods": "GET,POST,OPTIONS",
  "Access-Control-Allow-Headers": "Content-Type,Authorization",
  "Access-Control-Max-Age": "86400",
});

const json = (dados, status, origem) =>
  new Response(JSON.stringify(dados), {
    status,
    headers: { "Content-Type": "application/json; charset=utf-8", ...cors(origem) },
  });

function autorizado(req, env) {
  const cabecalho = req.headers.get("Authorization") || "";
  const token = cabecalho.startsWith("Bearer ") ? cabecalho.slice(7) : "";
  // comparação de tamanho fixo evita distinguir tokens pelo tempo de resposta
  if (!env.TOKEN || token.length !== env.TOKEN.length) return false;
  let diferenca = 0;
  for (let i = 0; i < token.length; i++) diferenca |= token.charCodeAt(i) ^ env.TOKEN.charCodeAt(i);
  return diferenca === 0;
}

export default {
  async fetch(req, env) {
    const origem = env.ORIGEM || "*";
    if (req.method === "OPTIONS") return new Response(null, { status: 204, headers: cors(origem) });

    const url = new URL(req.url);
    if (url.pathname !== "/estado") return json({ erro: "rota desconhecida" }, 404, origem);
    if (!autorizado(req, env)) return json({ erro: "token inválido" }, 401, origem);

    const guardado = (await env.ESTADO.get(CHAVE, { type: "json" })) || {};

    if (req.method === "GET") return json(guardado, 200, origem);

    if (req.method === "POST") {
      let corpo;
      try {
        corpo = await req.json();
      } catch {
        return json({ erro: "corpo não é JSON" }, 400, origem);
      }
      if (!valido(corpo)) return json({ erro: "seção, chave ou valor inválidos" }, 400, origem);

      const novo = aplicar(guardado, corpo, new Date().toISOString());
      await env.ESTADO.put(CHAVE, JSON.stringify(novo));
      return json({ ok: true, secao: corpo.secao, chave: corpo.chave }, 200, origem);
    }

    return json({ erro: "método não suportado" }, 405, origem);
  },
};
