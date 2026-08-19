/* Como uma escrita entra no estado. Separado do Worker para poder ser testado sozinho.

   O estado é raso de propósito: seções no primeiro nível, uma chave por registro no
   segundo. Peso usa a data como chave, então registrar duas vezes no mesmo dia deixa o
   último valor — sem duplicar ponto no gráfico. */

export const SECOES = ["peso"];          // cresce a cada tópico com estado

export function valido(corpo) {
  return !!corpo && SECOES.includes(corpo.secao)
    && typeof corpo.chave === "string" && corpo.chave.length > 0 && corpo.chave.length <= 64
    && corpo.valor !== undefined && corpo.valor !== null;
}

export function aplicar(estado, corpo, agora) {
  const novo = { ...estado };
  novo[corpo.secao] = { ...(novo[corpo.secao] || {}), [corpo.chave]: corpo.valor };
  novo.atualizado_em = agora;
  return novo;
}
