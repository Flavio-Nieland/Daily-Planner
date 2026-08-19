/* O registro do peso: manda para o Worker e confirma na própria folha, sem recarregar.

   O token é dele e fica no localStorage do navegador — o HTML publicado é público e nunca
   carrega credencial. A curva do jornal só muda amanhã, porque a edição de hoje já está
   publicada; a folha diz isso em vez de fingir que atualizou. */

const GUARDA_TOKEN = "diario.token";

async function gravarNoWorker(secao, chave, valor) {
  if (!EDICAO.worker) throw new Error("o Worker ainda não foi configurado nesta edição");
  let token = localStorage.getItem(GUARDA_TOKEN);
  if (!token) {
    token = (prompt("Cole o token do seu Worker (fica salvo neste navegador):") || "").trim();
    if (!token) throw new Error("sem token, nada é gravado");
    localStorage.setItem(GUARDA_TOKEN, token);
  }
  const resposta = await fetch(EDICAO.worker + "/estado", {
    method: "POST",
    headers: { "Content-Type": "application/json", Authorization: "Bearer " + token },
    body: JSON.stringify({ secao, chave, valor }),
  });
  if (resposta.status === 401) {
    localStorage.removeItem(GUARDA_TOKEN);
    throw new Error("token recusado — tente de novo para digitar outro");
  }
  if (!resposta.ok) throw new Error("o Worker respondeu " + resposta.status);
  return resposta.json();
}

document.addEventListener("click", async (ev) => {
  const botao = ev.target.closest("#peso-gravar");
  if (!botao) return;
  const campo = document.getElementById("peso-valor");
  const aviso = document.getElementById("peso-aviso");
  const kg = parseFloat((campo.value || "").replace(",", "."));
  if (!isFinite(kg) || kg <= 0 || kg > 400) {
    aviso.textContent = "Peso inválido.";
    return;
  }
  botao.disabled = true;
  aviso.textContent = "gravando…";
  try {
    await gravarNoWorker("peso", campo.dataset.dia, kg);
    aviso.textContent = `${kg.toFixed(1)} kg gravado. Entra na curva na edição de amanhã.`;
    campo.value = "";
  } catch (erro) {
    aviso.textContent = "Não gravou: " + erro.message;
  } finally {
    botao.disabled = false;
  }
});

/* Marcar um tópico como feito. É isto que avança o plano — nunca o calendário.
   O navegador só registra o dia; quem decide a sessão da vez é o build. */
document.addEventListener("click", async (ev) => {
  const botao = ev.target.closest(".marcar");
  if (!botao) return;
  const topico = botao.dataset.topico;
  const aviso = document.getElementById(topico + "-aviso");
  botao.disabled = true;
  if (aviso) aviso.textContent = "marcando…";
  try {
    await gravarNoWorker("feito", topico + ":" + botao.dataset.dia, true);
    botao.outerHTML = '<span class="feito">✓ feito hoje</span>';
    if (aviso) aviso.textContent = "Avança na edição de amanhã.";
  } catch (erro) {
    botao.disabled = false;
    if (aviso) aviso.textContent = "Não marcou: " + erro.message;
  }
});
