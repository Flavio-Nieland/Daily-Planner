/* Caderno do Peso: a curva interativa e o registro.

   Pedido dele (2026-11-03): passar o mouse num ponto mostra quanto e quando foi gravado.
   A série sai de ESTADO.peso — a do build mais a viva do Worker —, então o peso gravado
   agora entra na curva agora. Registro novo guarda {kg, em}: a hora só existe daqui em
   diante; os antigos são só número e a dica diz "hora não registrada". */

const PESO = { faixa: 'tudo', msg: '' };

function seriePeso() {
  return Object.entries(ESTADO.peso || {})
    .map(([data, v]) => {
      const kg = v && typeof v === 'object' ? +v.kg : +v;
      return { data, kg, em: v && typeof v === 'object' ? v.em || null : null };
    })
    .filter(p => /^\d{4}-\d{2}-\d{2}$/.test(p.data) && isFinite(p.kg) && p.kg > 0)
    .sort((a, b) => (a.data < b.data ? -1 : 1));
}

function metaPeso(dados) {
  const v = +valorDo('medida', 'meta:peso');
  return isFinite(v) && v > 0 ? v : dados.meta;
}

function diasSemPesar(hoje) {
  const s = seriePeso(), u = s[s.length - 1];
  return u ? Math.round((dt(hoje) - dt(u.data)) / 864e5) : null;
}

function pgCurva(dados) {
  const sem = diasSemPesar(dados.hoje);
  return '<div class="linha-ctl"><div class="seg" role="group">'
    + [['30', '30 dias'], ['90', '90 dias'], ['tudo', 'tudo']].map(([v, r]) =>
      '<button data-faixa="' + v + '" aria-pressed="' + (PESO.faixa === v) + '">' + r + '</button>').join('')
    + '</div>' + (sem !== null && sem > 3 ? '<span class="miudo">último registro há ' + sem
      + ' dias — <button class="link" data-pag="1">registrar agora</button></span>' : '') + '</div>'
    + '<div class="grafico" id="grafico"></div>'
    + '<div class="legenda"><span><i></i>peso registrado</span><span><i class="mm"></i>média dos últimos 7 dias</span>'
    + '<span><i class="alvo"></i>alvo de ' + nf(metaPeso(dados)) + ' kg</span></div>'
    + '<div class="stats" id="stats"></div>';
}

function montarGrafico(dados) {
  const caixa = document.getElementById('grafico'), st = document.getElementById('stats');
  if (!caixa) return;
  const serie = seriePeso(), meta = metaPeso(dados);
  const pts = PESO.faixa === 'tudo' ? serie : serie.filter(p => p.data >= mais(dados.hoje, -+PESO.faixa));
  if (!pts.length) {
    const ult = serie[serie.length - 1];
    caixa.innerHTML = '<p class="vazio" style="padding:60px 0;text-align:center">'
      + (ult ? 'Nenhum registro nos últimos ' + PESO.faixa + ' dias — o último foi em ' + ddmm(ult.data) + '.'
        : 'Sem medidas ainda. O primeiro registro começa a curva.') + '</p>';
    st.innerHTML = '';
    return;
  }
  const W = 860, H = 300, ml = 46, mr = 16, mt = 16, mb = 30;
  const t0 = dt(pts[0].data).getTime(), t1 = Math.max(dt(pts[pts.length - 1].data).getTime(), t0 + 864e5 * 6);
  const vals = pts.map(p => p.kg);
  let lo = Math.min(...vals, meta), hi = Math.max(...vals, meta);
  lo = Math.floor((lo - 0.4) * 2) / 2; hi = Math.ceil((hi + 0.4) * 2) / 2;
  const X = t => ml + (t - t0) / (t1 - t0) * (W - ml - mr);
  const Y = v => mt + (hi - v) / (hi - lo) * (H - mt - mb);
  const xy = pts.map(p => [X(dt(p.data).getTime()), Y(p.kg)]);
  // média móvel por tempo: tudo o que caiu nos 7 dias até o ponto
  const mm = pts.map(p => {
    const lim = mais(p.data, -6), w = serie.filter(q => q.data >= lim && q.data <= p.data);
    return w.reduce((n, q) => n + q.kg, 0) / w.length;
  });
  let g = '';
  for (let v = lo; v <= hi + 1e-9; v += 0.5) {
    const y = Y(v), inteiro = Math.abs(v - Math.round(v)) < 1e-9;
    g += '<line x1="' + ml + '" x2="' + (W - mr) + '" y1="' + y + '" y2="' + y + '" stroke="' + (inteiro ? '#c6bb9d' : '#e4dcc6') + '"/>';
    if (inteiro) g += '<text class="eixo" x="' + (ml - 8) + '" y="' + (y + 4) + '" text-anchor="end">' + v + ' kg</text>';
  }
  const passoDias = Math.max(1, Math.ceil((t1 - t0) / 864e5 / 8));
  for (let t = t0; t <= t1; t += passoDias * 864e5) {
    g += '<text class="eixo" x="' + X(t) + '" y="' + (H - 8) + '" text-anchor="middle">' + ddmm(new Date(t).toISOString().slice(0, 10)) + '</text>';
  }
  g += '<line x1="' + ml + '" x2="' + (W - mr) + '" y1="' + Y(meta) + '" y2="' + Y(meta) + '" stroke="#8a2417" stroke-width="1" stroke-dasharray="1 4"/>'
    + '<text class="eixo" x="' + (W - mr) + '" y="' + (Y(meta) - 5) + '" text-anchor="end" fill="#8a2417">alvo ' + nf(meta) + ' kg</text>';
  // mais de 7 dias sem pesar não é "peso estável": o trecho vira pontilhado e a média recomeça
  const trechos = [[0]];
  for (let i = 1; i < pts.length; i++) {
    const dias = Math.round((dt(pts[i].data) - dt(pts[i - 1].data)) / 864e5);
    if (dias > 7) {
      g += '<line x1="' + xy[i - 1][0] + '" y1="' + xy[i - 1][1] + '" x2="' + xy[i][0] + '" y2="' + xy[i][1]
        + '" stroke="#141209" stroke-dasharray="1 5" opacity=".6"/>'
        + '<text class="eixo" font-style="italic" x="' + ((xy[i - 1][0] + xy[i][0]) / 2) + '" y="'
        + (Math.min(xy[i - 1][1], xy[i][1]) - 10) + '" text-anchor="middle">' + dias + ' dias sem registro</text>';
      trechos.push([i]);
    } else trechos[trechos.length - 1].push(i);
  }
  trechos.forEach(t => {
    if (t.length < 2) return;
    g += '<polyline points="' + t.map(i => xy[i][0].toFixed(1) + ',' + Y(mm[i]).toFixed(1)).join(' ')
      + '" fill="none" stroke="#8a2417" stroke-width="1.6" stroke-dasharray="5 4"/>'
      + '<polyline points="' + t.map(i => xy[i][0].toFixed(1) + ',' + xy[i][1].toFixed(1)).join(' ')
      + '" fill="none" stroke="#141209" stroke-width="1.8"/>';
  });
  g += xy.map(([x, y], i) => '<circle cx="' + x + '" cy="' + y + '" r="' + (i === xy.length - 1 ? 4.5 : 3.4)
    + '" fill="' + (i === xy.length - 1 ? '#141209' : '#fcf9f1') + '" stroke="#141209" stroke-width="1.6"/>').join('');
  g += '<line class="mira" x1="0" x2="0" y1="' + mt + '" y2="' + (H - mb) + '" stroke="#141209" stroke-width=".8" stroke-dasharray="2 3" visibility="hidden"/>'
    + '<circle class="foco" r="7" fill="none" stroke="#8a2417" stroke-width="2" visibility="hidden"/>'
    + '<rect class="sensor" x="' + ml + '" y="0" width="' + (W - ml - mr) + '" height="' + H + '" fill="transparent"/>';
  caixa.innerHTML = '<svg viewBox="0 0 ' + W + ' ' + H + '" role="img" aria-label="curva do peso, ' + pts.length
    + ' registros">' + g + '</svg><div class="dica" id="dica"></div>';

  const svg = caixa.querySelector('svg'), dica = caixa.querySelector('.dica');
  const mira = svg.querySelector('.mira'), foco = svg.querySelector('.foco');
  function mostrar(i) {
    const p = pts[i], [x, y] = xy[i], escala = svg.getBoundingClientRect().width / W;
    mira.setAttribute('x1', x); mira.setAttribute('x2', x); mira.setAttribute('visibility', 'visible');
    foco.setAttribute('cx', x); foco.setAttribute('cy', y); foco.setAttribute('visibility', 'visible');
    const ant = serie[serie.findIndex(q => q.data === p.data) - 1];
    const delta = ant ? (p.kg - ant.kg >= 0 ? '+' : '−') + nf(Math.abs(p.kg - ant.kg)) + ' kg desde ' + ddmm(ant.data) : 'primeiro registro';
    const quando = p.em ? 'gravado às ' + new Date(p.em).toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit' }) : 'hora não registrada';
    dica.innerHTML = '<b>' + nf(p.kg) + ' kg</b><span>' + SEMANA[dt(p.data).getDay()] + ', ' + ddmm(p.data) + '/' + p.data.slice(0, 4)
      + ' · ' + quando + '</span><span>' + delta + '</span>';
    dica.style.display = 'block';
    dica.style.left = Math.min(Math.max(x * escala, 120), svg.getBoundingClientRect().width - 120) + 'px';
    dica.style.top = (y * escala) + 'px';
  }
  const sensor = svg.querySelector('.sensor');
  const perto = clientX => {
    const r = svg.getBoundingClientRect(), x = (clientX - r.left) / r.width * W;
    let melhor = 0;
    xy.forEach(([px], i) => { if (Math.abs(px - x) < Math.abs(xy[melhor][0] - x)) melhor = i; });
    return melhor;
  };
  sensor.addEventListener('mousemove', ev => mostrar(perto(ev.clientX)));
  sensor.addEventListener('touchstart', ev => mostrar(perto(ev.touches[0].clientX)), { passive: true });
  sensor.addEventListener('mouseleave', () => {
    dica.style.display = 'none'; mira.setAttribute('visibility', 'hidden'); foco.setAttribute('visibility', 'hidden');
  });

  const ult = pts[pts.length - 1], pri = pts[0];
  st.innerHTML = '<div><b>' + nf(ult.kg) + ' kg</b><span>último · ' + ddmm(ult.data) + '</span></div>'
    + '<div><b>' + (ult.kg - pri.kg >= 0 ? '+' : '−') + nf(Math.abs(ult.kg - pri.kg)) + ' kg</b><span>no período</span></div>'
    + '<div><b>' + nf(Math.min(...vals)) + ' kg</b><span>mínimo</span></div>'
    + '<div><b>' + nf(Math.max(...vals)) + ' kg</b><span>máximo</span></div>';
}

function pgRegistrar(dados) {
  const serie = seriePeso(), ult = serie[serie.length - 1];
  const hoje = serie.find(p => p.data === dados.hoje);
  const sem = diasSemPesar(dados.hoje);
  return '<div class="registro">'
    + (sem !== null && sem > 3 ? '<div class="parado">' + sem + ' dias sem registro — o último foi ' + nf(ult.kg) + ' kg em ' + ddmm(ult.data) + '</div>' : '')
    + '<div class="rotulo centro">Peso de hoje · ' + curto(dados.hoje) + '</div>'
    + '<div class="kg"><button class="passo" data-delta="-0.1" aria-label="menos 100 gramas">−</button>'
    + '<input id="peso-valor" inputmode="decimal" value="' + (hoje ? nf(hoje.kg) : ult ? nf(ult.kg) : '') + '" placeholder="70,0"'
    + ' aria-label="peso de hoje em quilos" data-dia="' + dados.hoje + '"><span class="un">kg</span>'
    + '<button class="passo" data-delta="0.1" aria-label="mais 100 gramas">+</button></div>'
    + '<button class="botao" id="peso-gravar">' + (hoje ? 'corrigir o de hoje' : 'gravar') + '</button>'
    + '<p class="resp" id="peso-aviso">' + (PESO.msg || (hoje ? 'Hoje já tem ' + nf(hoje.kg) + ' kg; gravar de novo substitui.'
      : 'Em jejum, depois do banheiro: é o que dá a curva mais limpa.')) + '</p>'
    + '<div class="spark" id="spark"></div></div>';
}

function montarSpark() {
  const el = document.getElementById('spark'), pts = seriePeso().slice(-14);
  if (!el || pts.length < 2) return;
  const W = 360, H = 60, vals = pts.map(p => p.kg), lo = Math.min(...vals) - 0.2, hi = Math.max(...vals) + 0.2;
  const t0 = dt(pts[0].data).getTime(), t1 = dt(pts[pts.length - 1].data).getTime();
  const xy = pts.map(p => [6 + (dt(p.data).getTime() - t0) / ((t1 - t0) || 1) * (W - 12), 6 + (hi - p.kg) / (hi - lo) * (H - 12)]);
  el.innerHTML = '<svg viewBox="0 0 ' + W + ' ' + H + '"><polyline points="' + xy.map(a => a.join(',')).join(' ')
    + '" fill="none" stroke="#141209" stroke-width="1.5"/><circle cx="' + xy[xy.length - 1][0] + '" cy="' + xy[xy.length - 1][1]
    + '" r="3.5" fill="#141209"/></svg><p class="miudo">últimos ' + pts.length
    + ' registros · <button class="link" data-pag="0">ver a curva inteira</button></p>';
}

CADERNOS.peso = {
  paginas: (topico) => [
    { nome: 'A curva', f: () => pgCurva(topico.dados), depois: () => montarGrafico(topico.dados) },
    { nome: 'Registrar', f: () => pgRegistrar(topico.dados), depois: () => { montarSpark(); PESO.msg = ''; } },
  ],
};

document.addEventListener('click', async ev => {
  const b = ev.target.closest('[data-faixa],[data-delta],#peso-gravar');
  if (!b) return;
  if (b.dataset.faixa) { PESO.faixa = b.dataset.faixa; return redesenhar(); }
  const campo = document.getElementById('peso-valor');
  if (b.dataset.delta) {
    const v = parseFloat((campo.value || '0').replace(',', '.')) || 0;
    campo.value = nf(Math.round((v + +b.dataset.delta) * 10) / 10);
    return;
  }
  const aviso = document.getElementById('peso-aviso');
  const kg = parseFloat((campo.value || '').replace(',', '.'));
  if (!isFinite(kg) || kg <= 20 || kg > 300) { aviso.textContent = 'Peso inválido.'; return; }
  b.disabled = true;
  aviso.textContent = 'gravando…';
  const valor = { kg: Math.round(kg * 10) / 10, em: new Date().toISOString() };
  try {
    await gravarNoWorker('peso', campo.dataset.dia, valor);
    aplicarLocal('peso', campo.dataset.dia, valor);
    PESO.msg = nf(valor.kg) + ' kg gravado. Já está na curva — <button class="link" data-pag="0">ver</button>';
    redesenhar();
  } catch (erro) {
    aviso.textContent = 'Não gravou: ' + erro.message;
    b.disabled = false;
  }
});
