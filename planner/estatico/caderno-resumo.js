/* Caderno do Resumo: a edição de hoje, o que falta hoje e o balanço da semana.

   Pedido dele (2026-11-03): o diário só prescrevia — dizia o que comer, ouvir e pesar,
   mas nunca sabia o que ele fez. Agora:
   - "O que falta hoje" junta as marcações de todos os cadernos e das folhas com "fiz hoje";
     a cinta conta o que falta e as bolinhas dos tópicos em dia ficam hachuradas;
   - "Balanço da semana" cruza a média semanal do peso com o quanto ele seguiu a dieta e
     o alvo (70 kg, editável). A sugestão de kcal só aparece com a dieta sendo seguida
     (≥ 70% das refeições marcadas): abaixo disso, o problema não é a meta. */

function edicaoDeHoje() { return EDICAO.iso === hojeReal(); }

/* Os itens do dia, de todos os tópicos. info = só aviso, não conta como pendência. */
function pendencias() {
  const hoje = EDICAO.iso, lista = [];
  EDICAO.topicos.forEach(t => {
    if (t.caderno === 'dieta' && t.dados.dias[hoje]) {
      t.dados.dias[hoje].refeicoes.forEach((r, i) => {
        if (edicaoDeHoje() && (r.hora || '99') > agoraHM()) return;
        const v = valorDo('feito', 'refeicao:' + hoje + ':' + i);
        lista.push({ id: 'dieta', ir: 'dieta:' + (i + 1), ok: !!v,
          texto: v ? r.nome + ': ' + v : 'Marcar como foi o ' + r.nome.toLowerCase() });
      });
    } else if (t.caderno === 'compras') {
      const n = t.dados.ciclos.findIndex(c => c.inicio === hoje && c.itens.length);
      if (n >= 0) {
        const c = t.dados.ciclos[n], ok = c.itens.filter(x => noCarrinho(c, x)).length;
        lista.push({ id: 'compras', ir: 'compras:0', ok: ok === c.itens.length,
          texto: 'Compra de hoje: ' + ok + ' de ' + c.itens.length + ' no carrinho' });
      } else if (t.dados.ciclos.some(c => c.inicio === mais(hoje, 1) && c.itens.length)) {
        lista.push({ id: 'compras', ir: 'compras:0', ok: true, info: true, texto: 'Amanhã é dia de compra — a lista já está pronta' });
      }
    } else if (t.caderno === 'album') {
      ['gosto', 'estilo'].forEach((q, i) => {
        if (!t.dados[q]) return;
        const v = valorDo('feito', 'disco:' + hoje + ':' + q);
        lista.push({ id: 'album', ir: 'album:' + i, ok: !!v, texto: v ? t.dados[q].album + ': ' + v : 'Ouvir ' + t.dados[q].album });
      });
    } else if (t.caderno === 'peso') {
      const v = valorDo('peso', hoje);
      lista.push({ id: 'peso', ir: 'peso:1', ok: !!v, texto: v ? 'Peso de hoje gravado' : 'Registrar o peso de hoje' });
    } else if (!t.caderno && !t.falhou) {
      // folha de blocos com "fiz hoje": o botão no HTML diz que falta; o "✓ feito" diz que já foi
      const html = t.blocos.join('');
      if (!/class="marcar"|class="feito"/.test(html)) return;
      const ok = !!valorDo('feito', t.id + ':' + hoje) || !/class="marcar"/.test(html);
      lista.push({ id: t.id, ir: t.id + ':', ok, texto: ok ? t.nome + ' feito' : 'Marcar ' + t.nome + ' como feito' });
    }
  });
  return lista;
}

function emDia(ti) {
  const id = EDICAO.topicos[ti].id, itens = pendencias().filter(x => x.id === id && !x.info);
  return itens.length > 0 && itens.every(x => x.ok);
}

function faltaCinta() {
  const n = pendencias().filter(x => !x.ok).length;
  const peso = dadosDe('peso'), sem = peso ? diasSemPesar(peso.hoje) : null;
  if (indiceDo('resumo') < 0) return '';
  const partes = [];
  if (sem !== null && sem > 3) partes.push(sem + ' dias sem pesar');
  if (n) partes.push('falta' + (n > 1 ? 'm ' : ' ') + n);
  return partes.length ? '<button class="falta" data-ir="resumo:1">' + partes.join(' · ') + '</button>'
    : '<span class="falta ok">tudo em dia ✓</span>';
}

function pgHoje() {
  const l = pendencias(), d = dadosDe('dieta');
  const feitos = l.filter(x => x.ok && !x.info).length, tot = l.filter(x => !x.info).length;
  let agora = '';
  if (d && d.dias[d.hoje]) {
    const i = refeicaoDaHora(d), r = d.dias[d.hoje].refeicoes[i];
    agora = '<div class="rotulo">Agora</div><p class="miudo">' + esc(r.nome) + ' · ' + esc(r.hora) + '</p>'
      + '<p class="grande agora-prato">' + esc(pratoDe(r)) + '</p>'
      + '<button class="link" data-ir="dieta:' + (i + 1) + '">ver a refeição</button>';
  }
  const peso = dadosDe('peso'), sem = peso ? diasSemPesar(peso.hoje) : null;
  return '<div class="materia"><div>'
    + '<div class="rotulo">O que falta hoje<span class="dir">' + feitos + ' de ' + tot + ' feitos</span></div>'
    + (l.length ? '<ul class="pend-lista">' + l.map(x => '<li class="' + (x.ok ? 'ok' : '') + '"><span class="st">'
      + (x.info ? '·' : x.ok ? '✓' : '○') + '</span><span>' + esc(x.texto) + '</span>'
      + '<button class="link ir" data-ir="' + x.ir + '">abrir</button></li>').join('') + '</ul>'
      : '<p class="vazio">Nada para marcar ainda hoje.</p>')
    + '</div><div class="lado">' + agora
    + (sem !== null && sem > 3 ? '<div class="sugestao"><b>' + sem + ' dias sem pesar.</b> Três pesagens por semana já dão uma tendência confiável.</div>' : '')
    + '</div></div>';
}

const segunda = iso => mais(iso, -((dt(iso).getDay() + 6) % 7));

/* Regressão linear dos últimos 90 dias, em kg por semana; precisa de 3 registros. */
function tendencia(hoje) {
  const desde = mais(hoje, -90), pts = seriePeso().filter(p => p.data >= desde);
  if (pts.length < 3) return null;
  const xs = pts.map(p => (dt(p.data) - dt(desde)) / 864e5), ys = pts.map(p => p.kg);
  const mx = xs.reduce((a, b) => a + b) / xs.length, my = ys.reduce((a, b) => a + b) / ys.length;
  const den = xs.reduce((n, x) => n + (x - mx) ** 2, 0);
  if (!den) return null;
  return { porSemana: xs.reduce((n, x, i) => n + (x - mx) * (ys[i] - my), 0) / den * 7, n: pts.length };
}

function marcasDeRefeicao(desde, ate) {
  return Object.entries(ESTADO.feito || {})
    .filter(([k, v]) => v && k.startsWith('refeicao:') && k.slice(9, 19) >= desde && k.slice(9, 19) <= ate)
    .map(([, v]) => v);
}

function pgBalanco() {
  const hoje = EDICAO.iso, peso = dadosDe('peso'), serie = seriePeso();
  const semanas = [];
  for (let s = segunda(hoje), k = 0; k < 8; k++, s = mais(s, -7)) {
    const fim = mais(s, 6), pesos = serie.filter(p => p.data >= s && p.data <= fim), m = marcasDeRefeicao(s, fim);
    semanas.push({ s, media: pesos.length ? pesos.reduce((n, p) => n + p.kg, 0) / pesos.length : null, n: pesos.length,
      ader: m.length ? m.filter(v => v === 'segui').length / m.length : null, marcadas: m.length });
  }
  semanas.forEach((w, i) => {
    const ant = semanas.slice(i + 1).find(x => x.media !== null);
    w.delta = w.media !== null && ant ? w.media - ant.media : null;
  });
  const linhas = semanas.map(w => '<tr class="' + (w.media === null && !w.marcadas ? 'vazia' : '') + '"><td>'
    + (w.s === segunda(hoje) ? 'esta semana' : 'sem. de ' + ddmm(w.s)) + '</td>'
    + '<td>' + (w.media === null ? '—' : nf(w.media) + ' kg') + '</td>'
    + '<td>' + (w.delta === null ? '' : (w.delta >= 0 ? '+' : '−') + nf(Math.abs(w.delta))) + '</td>'
    + '<td>' + (w.n || '—') + '</td>'
    + '<td>' + (w.ader === null ? '—' : Math.round(w.ader * 100) + '% de ' + w.marcadas) + '</td></tr>').join('');

  let lado = '<div class="rotulo">O alvo</div>';
  if (!peso) return '<p class="vazio">Sem o caderno do Peso nesta edição.</p>';
  const meta = metaPeso(peso), ult = serie[serie.length - 1];
  lado += '<div class="alvo"><input id="alvo" inputmode="decimal" value="' + nf(meta) + '" aria-label="peso alvo em quilos"> <span class="miudo">kg</span></div>';
  if (!ult) {
    lado += '<p class="miudo">Sem pesagens ainda.</p>';
  } else {
    const falta = meta - ult.kg, t = tendencia(hoje);
    lado += '<p class="mt">' + (Math.abs(falta) < 0.05 ? '<b>No alvo.</b>' : 'Faltam <b class="num">' + nf(Math.abs(falta)) + ' kg</b>')
      + ' <span class="miudo">a partir de ' + nf(ult.kg) + ' kg (' + ddmm(ult.data) + ')</span></p>';
    if (!t) {
      lado += '<p class="miudo mt">Poucos registros nos últimos 90 dias para medir o ritmo — três pesagens por semana bastam.</p>';
    } else {
      const ritmo = t.porSemana;
      lado += '<p class="mt">Ritmo: <b class="num">' + (ritmo >= 0 ? '+' : '−') + nf(Math.abs(ritmo), 2) + ' kg/semana</b> <span class="miudo">(' + t.n + ' registros em 90 dias)</span></p>';
      if (Math.sign(ritmo) === Math.sign(falta) && Math.abs(ritmo) > 0.02) {
        const quando = mais(hoje, Math.round(falta / ritmo * 7));
        lado += '<p>Nesse ritmo, chega aos ' + nf(meta) + ' kg por volta de <b>' + ddmm(quando) + '/' + quando.slice(0, 4) + '</b>.</p>';
      } else if (Math.abs(falta) >= 0.05) {
        lado += '<p>Nesse ritmo, não chega: a curva está parada ou indo para o outro lado.</p>';
      }
      const quer = falta > 0 ? [0.15, 0.35] : [-0.5, -0.25];
      const m = marcasDeRefeicao(mais(hoje, -28), hoje);
      const ader = m.length >= 5 ? m.filter(v => v === 'segui').length / m.length : null;
      let sug;
      if (Math.abs(falta) < 0.5) sug = '<b>Manter.</b> Você está perto do alvo.';
      else if (ader !== null && ader < 0.7) sug = '<b>Antes de mexer nas kcal:</b> você seguiu ' + Math.round(ader * 100) + '% das refeições marcadas. Com a dieta seguida, o ritmo atual pode bastar.';
      else if (ritmo < quer[0]) sug = '<b>Subir para ' + (falta > 0 ? '3.000' : '2.600') + ' kcal?</b> O ritmo está abaixo da faixa boa para o alvo (' + nf(quer[0], 2) + ' a ' + nf(quer[1], 2) + ' kg/semana).';
      else if (ritmo > quer[1]) sug = '<b>Baixar 150 kcal?</b> O ritmo está acima da faixa boa — parte do ganho vira gordura.';
      else sug = '<b>Manter as 2.800 kcal.</b> O ritmo está dentro da faixa boa para o alvo.';
      lado += '<div class="sugestao">' + sug + (ader === null ? '<p class="miudo">Marque as refeições por uma semana para a sugestão levar em conta se a dieta está sendo seguida.</p>' : '')
        + '<p class="miudo">Sugestão. A meta de kcal só muda se você pedir.</p></div>';
    }
  }
  return '<div class="materia"><div>'
    + '<div class="rotulo">As últimas 8 semanas</div>'
    + '<table class="semanas"><thead><tr><th>Semana</th><th>Média</th><th>Δ</th><th>Pesagens</th><th>Seguiu a dieta</th></tr></thead><tbody>' + linhas + '</tbody></table>'
    + '<p class="miudo mt">Média semanal, não o dia: o peso diário oscila até 1 kg com água e sal.</p>'
    + '</div><div class="lado">' + lado + '</div></div>';
}

CADERNOS.resumo = {
  paginas: (topico) => [
    { nome: 'Edição de hoje', f: () => '<div class="abertura">' + topico.blocos.join('') + '</div>' },
    { nome: 'O que falta hoje', f: pgHoje },
    { nome: 'Balanço da semana', f: pgBalanco },
  ],
};

document.addEventListener('change', ev => {
  if (ev.target.id !== 'alvo') return;
  const v = parseFloat(ev.target.value.replace(',', '.'));
  if (isFinite(v) && v > 30 && v < 250) gravarEstado('medida', 'meta:peso', Math.round(v * 10) / 10);
  else { avisar('Alvo inválido.'); redesenhar(); }
});
