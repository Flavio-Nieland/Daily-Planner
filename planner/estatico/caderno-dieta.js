/* Caderno da Dieta: "O dia" e uma página por refeição.

   Pedido dele (2026-11-03): a folha com as cinco refeições juntas ficava poluída; cada
   refeição ganha a própria página, com a mesma refeição de ontem e de amanhã ao lado — é
   ali que se vê o aproveitamento entre os dias do ciclo de compras. O seletor ontem/hoje/
   amanhã vale para todas as páginas. Dia gerado antes de 04/11/2026 não tem prato,
   macros nem preparo: a página mostra o que houver. */

const DIETA = { foco: null };
const SIMBOLO = { segui: '✓', troquei: '~', pulei: '×' };

function dietaDados() { return dadosDe('dieta'); }
function focoDieta(d) { return DIETA.foco && d.dias[DIETA.foco] ? DIETA.foco : d.hoje; }
function pratoDe(r) { return r.prato || (r.itens && r.itens[0] ? r.itens[0].alimento : r.nome); }
function chaveRef(iso, i) { return 'refeicao:' + iso + ':' + i; }

/* A refeição da vez: a última cujo horário já chegou, com 30 min de antecedência. */
function refeicaoDaHora(d) {
  const t = new Date(Date.now() + 30 * 6e4).toTimeString().slice(0, 5);
  let vez = 0;
  d.dias[d.hoje].refeicoes.forEach((r, i) => { if ((r.hora || '99') <= t) vez = i; });
  return vez;
}

/* Sem endereço na URL, a edição do dia abre na refeição da hora (decisão de 2026-11-03). */
function paginaInicial() {
  const d = dietaDados(), t = indiceDo('dieta');
  if (!d || t < 0 || EDICAO.iso !== hojeReal() || !d.dias[d.hoje]) return null;
  return { t, p: refeicaoDaHora(d) + 1 };
}

function cicloDe(d, iso) { return d.ciclos.find(c => c.dias.includes(iso)); }

function pgDia(d) {
  const foco = focoDieta(d), refs = d.dias[foco].refeicoes, maxk = Math.max(...refs.map(r => +r.kcal || 0), 1);
  const soma = c => refs.reduce((n, r) => n + (+r[c] || 0), 0);
  const kcal = soma('kcal'), P = soma('proteina_g'), C = soma('carbo_g'), G = soma('gordura_g');
  const pct = (g, k) => kcal ? Math.round(g * k / kcal * 100) : 0;
  const vez = foco === d.hoje && EDICAO.iso === hojeReal() ? refeicaoDaHora(d) : -1;
  const linhas = refs.map((r, i) => {
    const v = valorDo('feito', chaveRef(foco, i));
    const passou = foco < d.hoje || (foco === d.hoje && (r.hora || '99') <= agoraHM());
    const marca = v ? '<span class="marca" title="' + esc(v) + '">' + (SIMBOLO[v] || '✓') + '</span>'
      : passou ? '<span class="marca pend">marcar</span>' : '';
    return '<li data-ir="dieta:' + (i + 1) + '"' + (i === vez ? ' class="agora"' : '') + '><span class="h">' + esc(r.hora) + '</span>'
      + '<span><span class="r">' + esc(r.nome) + (i === vez ? '<span class="tag">agora</span>' : '') + marca + '</span>'
      + '<span class="p">' + esc(pratoDe(r)) + '</span></span>'
      + '<span class="k">' + (+r.kcal || 0) + ' kcal<span class="kbar"><i style="width:' + Math.round((+r.kcal || 0) / maxk * 100) + '%"></i></span></span></li>';
  }).join('');
  const ciclo = cicloDe(d, foco);
  let caixa = '';
  if (ciclo) {
    const n = ciclo.dias.indexOf(foco);
    const amanhaCompra = d.ciclos.some(c => c.inicio === mais(foco, 1));
    caixa = '<div class="ciclo"><div class="rotulo sem-fio">Ciclo de compras<span class="dir">dia ' + (n + 1) + ' de ' + ciclo.dias.length + '</span></div>'
      + '<div class="ticks">' + ciclo.dias.map((x, i) => '<i class="' + (i < n ? 'on' : i === n ? 'hoje' : '') + '" title="' + curto(x) + '"></i>').join('') + '</div>'
      + '<p class="miudo">Compra de ' + curto(ciclo.inicio) + ' cobre ' + ciclo.dias.map(curto).join(', ') + '.</p>'
      + (n === 0 ? '<p class="compra-dia">Hoje é dia de compra. <button class="link" data-ir="compras:0">ver a lista</button></p>' : '')
      + (amanhaCompra ? '<p class="compra-dia">Amanhã é dia de compra. <button class="link" data-ir="compras:0">ver a lista</button></p>' : '')
      + '</div>';
  }
  const titulo = foco === d.hoje ? 'O dia de hoje' : foco < d.hoje ? 'Como foi ontem' : 'O que vem amanhã';
  return '<div class="materia"><div>'
    + '<div class="rotulo">' + titulo + '<span class="dir">' + curto(foco) + '</span></div>'
    + '<ul class="linha-tempo">' + linhas + '</ul>'
    + '<p class="miudo" style="margin-top:8px">Toque numa refeição para abrir a página dela.</p>'
    + '</div><div class="lado">'
    + '<div class="rotulo">O dia fecha em</div>'
    + '<p class="grande num">' + kcal.toLocaleString('pt-BR') + ' kcal</p>'
    + '<p class="miudo">meta de ' + d.meta.toLocaleString('pt-BR') + ' kcal</p>'
    + (P ? '<div class="macros"><div><b>' + P + ' g</b><span>prot · ' + pct(P, 4) + '%</span></div>'
      + '<div><b>' + C + ' g</b><span>carbo · ' + pct(C, 4) + '%</span></div>'
      + '<div><b>' + G + ' g</b><span>gord · ' + pct(G, 9) + '%</span></div></div>' : '')
    + caixa + '</div></div>';
}

function vizinho(d, iso, i, titulo) {
  const dia = d.dias[iso];
  const cab = '<div class="rotulo">' + titulo + '<span class="dir">' + curto(iso) + '</span></div>';
  if (!dia || !dia.refeicoes[i]) return '<div class="vizinho">' + cab + '<p class="vazio miudo">sem cardápio</p></div>';
  const r = dia.refeicoes[i];
  return '<div class="vizinho">' + cab + '<p class="pr">' + esc(pratoDe(r)) + '</p>'
    + '<p class="miudo">' + r.itens.map(x => esc(x.alimento)).join(' · ') + '</p>'
    + '<p class="miudo num">' + (+r.kcal || 0) + ' kcal · ' + esc(r.hora) + '</p>'
    + (r.aproveita ? '<p class="ap">↺ ' + esc(r.aproveita) + '</p>' : '') + '</div>';
}

function pgRefeicao(d, i) {
  const foco = focoDieta(d), r = d.dias[foco].refeicoes[i];
  if (!r) return '<p class="vazio">Sem esta refeição no cardápio de ' + curto(foco) + '.</p>';
  const macros = r.proteina_g !== undefined ? ' · ' + r.proteina_g + ' g prot · ' + r.carbo_g + ' g carbo · ' + r.gordura_g + ' g gord' : '';
  const itens = '<ul class="itens">' + r.itens.map(x => '<li><span>' + esc(x.alimento) + '</span><span class="q">' + esc(x.qtd)
    + '</span><span class="g">' + (x.gramas ? Math.round(x.gramas) + ' g' : '') + '</span></li>').join('') + '</ul>';
  return '<div class="materia"><div>'
    + '<div class="ref-topo"><span>' + esc(r.hora) + '</span><span>' + curto(foco) + '</span><span class="k">' + (+r.kcal || 0) + ' kcal' + macros + '</span></div>'
    + '<h3 class="grande ref-prato">' + esc(pratoDe(r)) + '</h3>'
    + comoFoi(chaveRef(foco, i), ['segui', 'troquei', 'pulei'], foco > d.hoje)
    + itens
    + (r.preparo ? '<div class="preparo"><div class="rotulo">Preparo</div><p>' + esc(r.preparo) + '</p></div>' : '')
    + (r.aproveita ? '<div class="aproveita"><div class="rotulo">↺ Aproveitamento</div><p>' + esc(r.aproveita) + '</p></div>' : '')
    + '</div><div class="lado">' + vizinho(d, mais(foco, -1), i, 'Ontem') + vizinho(d, mais(foco, 1), i, 'Amanhã') + '</div></div>';
}

CADERNOS.dieta = {
  paginas: (topico) => {
    const d = topico.dados, refs = d.dias[focoDieta(d)].refeicoes;
    return [{ nome: 'O dia', f: () => pgDia(d) }].concat(refs.map((r, i) => ({ nome: r.nome, f: () => pgRefeicao(d, i) })));
  },
  cabeca: (topico) => {
    const d = topico.dados;
    const dias = [[-1, 'ontem'], [0, 'hoje'], [1, 'amanhã']].map(([n, rotulo]) => [mais(d.hoje, n), rotulo]).filter(([iso]) => d.dias[iso]);
    return '<div class="seg" role="group" aria-label="dia do cardápio">' + dias.map(([iso, rotulo]) =>
      '<button data-foco="' + iso + '" aria-pressed="' + (iso === focoDieta(d)) + '">' + rotulo + '<b>' + curto(iso) + '</b></button>').join('') + '</div>';
  },
};

document.addEventListener('click', ev => {
  const b = ev.target.closest('[data-foco]');
  if (!b) return;
  DIETA.foco = b.dataset.foco;
  redesenhar();
});
