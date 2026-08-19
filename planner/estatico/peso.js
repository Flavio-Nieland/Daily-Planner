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

/* Elo: mesma mecânica do peso, seção diferente. */
document.addEventListener("click", async (ev) => {
  const botao = ev.target.closest("#elo-gravar");
  if (!botao) return;
  const campo = document.getElementById("elo-valor");
  const aviso = document.getElementById("elo-aviso");
  const elo = parseInt((campo.value || "").replace(/\D/g, ""), 10);
  if (!isFinite(elo) || elo < 100 || elo > 3500) {
    aviso.textContent = "Elo inválido.";
    return;
  }
  botao.disabled = true;
  aviso.textContent = "gravando…";
  try {
    await gravarNoWorker("elo", campo.dataset.dia, elo);
    aviso.textContent = elo + " anotado. Entra na curva amanhã.";
    campo.value = "";
  } catch (erro) {
    aviso.textContent = "Não gravou: " + erro.message;
  } finally {
    botao.disabled = false;
  }
});

/* Comida: o veredito guarda o prato e o dia numa gravação só. */
document.addEventListener("click", async (ev) => {
  const botao = ev.target.closest(".veredito");
  if (!botao) return;
  const aviso = document.getElementById("comida-aviso")
             || document.getElementById("programacao-aviso");
  document.querySelectorAll(".veredito").forEach(b => (b.disabled = true));
  aviso.textContent = "gravando…";
  try {
    const chave = botao.dataset.chave || "prato:" + botao.dataset.prato;
    await gravarNoWorker("dominio", chave,
      { dia: botao.dataset.dia, veredito: botao.dataset.veredito });
    aviso.textContent = { dominado: "Marcado como dominado. Amanhã vem o próximo prato.",
                          revisar: "Anotado. O prato volta para revisão em alguns dias.",
                          concluido: "Concluído. Amanhã entra o próximo tópico liberado." }[botao.dataset.veredito]
                        || "Anotado.";
  } catch (erro) {
    document.querySelectorAll(".veredito").forEach(b => (b.disabled = false));
    aviso.textContent = "Não gravou: " + erro.message;
  }
});

/* Álbum: o estilo pedido vale a partir da edição de amanhã. */
document.addEventListener("click", async (ev) => {
  const botao = ev.target.closest("#estilo-gravar");
  if (!botao) return;
  const campo = document.getElementById("estilo-valor");
  const aviso = document.getElementById("estilo-aviso");
  const estilo = (campo.value || "").trim();
  if (estilo.length < 2) {
    aviso.textContent = "Escreva um estilo.";
    return;
  }
  botao.disabled = true;
  aviso.textContent = "gravando…";
  try {
    await gravarNoWorker("estilo", "pedido", { dia: campo.dataset.dia, estilo });
    aviso.textContent = `"${estilo}" anotado. A sugestão muda na edição de amanhã.`;
    campo.value = "";
  } catch (erro) {
    aviso.textContent = "Não gravou: " + erro.message;
  } finally {
    botao.disabled = false;
  }
});

/* Alongamento: mão–chão em cm e dor de 0 a 10, na mesma seção "medida". */
document.addEventListener("click", async (ev) => {
  const botao = ev.target.closest(".medir");
  if (!botao) return;
  const qual = botao.dataset.medida;
  const campo = document.getElementById(qual + "-valor");
  const aviso = document.getElementById("medida-aviso");
  const valor = parseFloat((campo.value || "").replace(",", "."));
  const limite = qual === "dor" ? 10 : 100;
  if (!isFinite(valor) || valor < -50 || valor > limite) {
    aviso.textContent = "Valor inválido.";
    return;
  }
  botao.disabled = true;
  aviso.textContent = "gravando…";
  try {
    await gravarNoWorker("medida", qual + ":" + campo.dataset.dia, valor);
    aviso.textContent = "Anotado. Entra na comparação amanhã.";
    campo.value = "";
  } catch (erro) {
    aviso.textContent = "Não gravou: " + erro.message;
  } finally {
    botao.disabled = false;
  }
});

/* Treino: carga e reps por exercício, numa gravação só. */
document.addEventListener("click", async (ev) => {
  const botao = ev.target.closest(".anotar-carga");
  if (!botao) return;
  const bloco = botao.closest(".exercicio");
  const aviso = bloco.querySelector(".aviso-carga");
  const kg = parseFloat((bloco.querySelector(".carga-kg").value || "").replace(",", "."));
  const reps = parseInt(bloco.querySelector(".carga-reps").value, 10);
  if (!isFinite(kg) || kg <= 0 || kg > 700 || !isFinite(reps) || reps <= 0 || reps > 100) {
    aviso.textContent = "Carga ou reps inválidos.";
    return;
  }
  botao.disabled = true;
  aviso.textContent = "gravando…";
  try {
    await gravarNoWorker("carga", botao.dataset.exercicio + ":" + botao.dataset.dia, { kg, reps });
    aviso.textContent = `${kg} kg × ${reps} anotado.`;
  } catch (erro) {
    botao.disabled = false;
    aviso.textContent = "Não gravou: " + erro.message;
  }
});
