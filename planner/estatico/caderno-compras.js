/* Caderno das Compras: o resumo do ciclo e uma página por seção do mercado.

   Compra a cada três dias (decisão dele em 2026-11-03). A lista é a soma exata do cardápio
   do ciclo, feita no build — sai igual nos dois builds do dia. Cada item diz o que pegar na
   prateleira e em que refeições será usado. A caixinha marcada vai para `feito` no Worker
   (chave compra:<início>:<item>), para marcar no celular e ver no computador. */

const COMPRAS = { ciclo: null };

function cicloCompras(d) { return d.ciclos[COMPRAS.ciclo === null ? d.padrao : COMPRAS.ciclo] || d.ciclos[0]; }
function secoesDe(c) { return [...new Set(c.itens.map(i => i.secao))]; }
function chaveCompra(c, item) { return ('compra:' + c.inicio + ':' + item.chave.replace(/[^a-z0-9]+/g, '-')).slice(0, 64); }
function noCarrinho(c, item) { return !!valorDo('feito', chaveCompra(c, item)); }

function rotuloCiclo(d, c) {
  if (c.inicio === d.hoje) return 'hoje';
  if (c.inicio === mais(d.hoje, 1)) return 'amanhã';
  if (c.dias.includes(d.hoje)) return 'em curso';
  return c.inicio > d.hoje ? 'próxima' : 'feita';
}

function escolhaCiclo(d) {
  const atual = cicloCompras(d);
  return '<div class="seg escolha" role="group" aria-label="qual compra">' + d.ciclos.map((c, i) =>
    '<button data-ciclo="' + i + '" aria-pressed="' + (c === atual) + '">Compra de ' + curto(c.inicio) + ' · ' + rotuloCiclo(d, c) + '</button>').join('') + '</div>';
}

function zapLink(c) {
  const txt = '*Compra de ' + curto(c.inicio) + '* (' + c.dias.map(curto).join(', ') + ')\n'
    + secoesDe(c).map(s => '\n*' + s + '*\n' + c.itens.filter(i => i.secao === s)
      .map(i => '- ' + (i.compra || i.nome + ' ' + gramas(i.g))).join('\n')).join('\n');
  return 'https://wa.me/?text=' + encodeURIComponent(txt);
}

function pgCompra(d) {
  const c = cicloCompras(d);
  if (!c.itens.length) {
    return escolhaCiclo(d) + '<p class="vazio">Sem lista para esta compra: o cardápio desses dias é de antes do regime de ciclos.</p>';
  }
  const cards = secoesDe(c).map((s, i) => {
    const da = c.itens.filter(x => x.secao === s), ok = da.filter(x => noCarrinho(c, x)).length;
    return '<button data-pag="' + (i + 1) + '"><span class="n">' + esc(s) + '</span><span class="miudo">' + da.length + ' itens · ' + ok + ' no carrinho</span>'
      + '<span class="prog"><i style="width:' + (ok / da.length * 100) + '%"></i></span></button>';
  }).join('');
  const rendem = c.itens.filter(x => new Set(x.usos.map(u => u.dia)).size >= 2)
    .sort((a, b) => b.usos.length - a.usos.length).slice(0, 7);
  return escolhaCiclo(d) + '<div class="materia"><div>'
    + '<div class="rotulo">Cobre ' + c.dias.map(curto).join(' · ') + '<span class="dir">' + c.itens.length + ' itens</span></div>'
    + '<div class="secoes">' + cards + '</div>'
    + '<a class="botao zap" href="' + zapLink(c) + '" target="_blank" rel="noopener">mandar a lista pro WhatsApp ↗</a>'
    + '<p class="miudo" style="margin-top:10px">A lista é a soma exata do cardápio dos três dias — muda só se o cardápio mudar.</p>'
    + '</div><div class="lado"><div class="rotulo">Os que mais rendem</div>'
    + '<ul class="rende">' + (rendem.map(x => '<li><span>' + esc(x.nome) + '</span><span>' + x.usos.length + ' refeições, '
      + new Set(x.usos.map(u => u.dia)).size + ' dias</span></li>').join('') || '<li class="vazio">nenhum ingrediente atravessa os dias</li>') + '</ul>'
    + '<p class="miudo" style="margin-top:10px">É aqui que se vê se o cardápio conversa entre os dias: compra uma vez, usa no ciclo inteiro.</p>'
    + '</div></div>';
}

function pgSecao(d, s) {
  const c = cicloCompras(d);
  const linhas = c.itens.filter(x => x.secao === s).map(x => {
    const ok = noCarrinho(c, x);
    const usos = x.usos.map(u => '<span class="uso" title="' + esc(u.qtd) + '">' + SEM[dt(u.dia).getDay()] + ' · '
      + esc(u.ref.replace(' da manhã', ' manhã').replace(' da tarde', ' tarde')) + '</span>').join('');
    return '<tr class="' + (ok ? 'ok' : '') + '"><td class="caixa"><input type="checkbox" class="chk" data-compra="' + esc(chaveCompra(c, x)) + '"'
      + (ok ? ' checked' : '') + ' aria-label="' + esc(x.nome) + '"></td>'
      + '<td class="nome">' + esc(x.nome) + '</td><td class="compra-un" title="o cardápio usa ' + gramas(x.g) + '">' + esc(x.compra || gramas(x.g)) + '</td>'
      + '<td class="u">' + usos + '</td></tr>';
  }).join('');
  return escolhaCiclo(d) + '<table class="lista"><thead><tr><th></th><th>Item</th><th>Comprar</th><th>Usado em</th></tr></thead><tbody>' + linhas + '</tbody></table>';
}

CADERNOS.compras = {
  paginas: (topico) => {
    const d = topico.dados, c = cicloCompras(d);
    return [{ nome: 'A compra', f: () => pgCompra(d) }].concat(secoesDe(c).map(s => ({ nome: s, f: () => pgSecao(d, s) })));
  },
};

document.addEventListener('click', ev => {
  const b = ev.target.closest('[data-ciclo]');
  if (!b) return;
  COMPRAS.ciclo = +b.dataset.ciclo;
  redesenhar();
});
document.addEventListener('change', ev => {
  if (!ev.target.matches || !ev.target.matches('.chk[data-compra]')) return;
  gravarEstado('feito', ev.target.dataset.compra, ev.target.checked);
});
