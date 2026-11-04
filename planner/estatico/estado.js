/* O estado que a edição enxerga: o que o build congelou no HTML mais o que está vivo no Worker.

   O build embute só as fatias que as páginas usam (peso, as marcações recentes de `feito`,
   a meta em `medida`) — nunca as notas dos livros, que são texto dele num site público.
   Ao abrir, se o navegador já tem o token, busca o estado vivo e redesenha: é isso que faz
   o peso gravado agora aparecer na curva agora, e não na edição de amanhã.

   Gravar é otimista: a página muda na hora e, se o Worker recusar, volta atrás e diz por quê. */

const ESTADO = (typeof EDICAO !== 'undefined' && EDICAO.estado) || {};
const GUARDA_TOKEN = "diario.token";

function tokenGuardado() {
  try { return localStorage.getItem(GUARDA_TOKEN); } catch (e) { return null; }
}

async function gravarNoWorker(secao, chave, valor) {
  if (!EDICAO.worker) throw new Error("o Worker ainda não foi configurado nesta edição");
  let token = tokenGuardado();
  if (!token) {
    token = (prompt("Cole o token do seu Worker (fica salvo neste navegador):") || "").trim();
    if (!token) throw new Error("sem token, nada é gravado");
    try { localStorage.setItem(GUARDA_TOKEN, token); } catch (e) { /* segue só nesta visita */ }
  }
  const resposta = await fetch(EDICAO.worker + "/estado", {
    method: "POST",
    headers: { "Content-Type": "application/json", Authorization: "Bearer " + token },
    body: JSON.stringify({ secao, chave, valor }),
  });
  if (resposta.status === 401) {
    try { localStorage.removeItem(GUARDA_TOKEN); } catch (e) { /* nada */ }
    throw new Error("token recusado — tente de novo para digitar outro");
  }
  if (!resposta.ok) throw new Error("o Worker respondeu " + resposta.status);
  return resposta.json();
}

function valorDo(secao, chave) { return (ESTADO[secao] || {})[chave]; }

function aplicarLocal(secao, chave, valor) {
  ESTADO[secao] = Object.assign({}, ESTADO[secao] || {}, { [chave]: valor });
}

function avisar(texto) {
  let caixa = document.getElementById("aviso-global");
  if (!caixa) {
    caixa = document.createElement("div");
    caixa.id = "aviso-global";
    caixa.setAttribute("role", "status");
    document.body.appendChild(caixa);
  }
  caixa.textContent = texto;
  caixa.classList.add("visivel");
  clearTimeout(avisar.t);
  avisar.t = setTimeout(() => caixa.classList.remove("visivel"), 4200);
}

/* Muda na página e manda para o Worker. Falhou: desfaz e conta. */
async function gravarEstado(secao, chave, valor) {
  const antes = valorDo(secao, chave);
  aplicarLocal(secao, chave, valor);
  if (typeof redesenhar === "function") redesenhar();
  try {
    await gravarNoWorker(secao, chave, valor);
    return true;
  } catch (erro) {
    aplicarLocal(secao, chave, antes === undefined ? false : antes);
    if (typeof redesenhar === "function") redesenhar();
    avisar("Não gravou: " + erro.message);
    return false;
  }
}

/* O estado vivo do KV. Sem token não pergunta nada: abrir a edição é só ler. */
async function carregarEstadoVivo() {
  if (!EDICAO.worker || !tokenGuardado()) return;
  try {
    const resposta = await fetch(EDICAO.worker + "/estado", {
      headers: { Authorization: "Bearer " + tokenGuardado() },
    });
    if (!resposta.ok) return;
    const vivo = await resposta.json();
    ["peso", "feito", "medida"].forEach(secao => {
      if (vivo && vivo[secao] && typeof vivo[secao] === "object") {
        ESTADO[secao] = Object.assign({}, ESTADO[secao] || {}, vivo[secao]);
      }
    });
    if (typeof redesenhar === "function") redesenhar();
  } catch (e) {
    /* sem rede: fica o que o build congelou */
  }
}
