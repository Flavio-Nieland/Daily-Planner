/* Paginação e navegação da edição — o MESMO código roda nos dois lados:
   no build, o Chromium headless chama window.__paginar() e o resultado é gravado no HTML;
   no cliente, a folha re-pagina ao abrir e ao redimensionar, porque a tela dele não é a do build.

   Armadilha do ADR 0001: multi-coluna transborda na HORIZONTAL. O teste é scrollWidth,
   não scrollHeight — medir altura não detecta nada e a paginação silenciosamente não acontece.

   Desde 2026-11-03 há dois tipos de tópico:
   - o tópico de BLOCOS, que a paginação distribui em folhas por transbordo (o de sempre);
   - o CADERNO, com páginas nomeadas e diagramação própria (Dieta, Compras, Álbum, Peso,
     Resumo). Quem desenha cada página é cadernos.js; aqui só se navega. A queixa que deu
     origem: a folha da Dieta com as cinco refeições juntas ficava poluída.

   Navegação: ←/→ passam as páginas (atravessando tópicos), ↑/↓ trocam de tópico, as
   bolinhas pulam de tópico e cada tópico lembra a página em que ele parou. */

const SETA_ESQ = '<svg viewBox="0 0 36 30"><path d="M14 6 L5 15 L14 24 M5 15 H31" fill="none" stroke="currentColor" stroke-width="1.6"/></svg>';
const SETA_DIR = '<svg viewBox="0 0 36 30"><path d="M22 6 L31 15 L22 24 M31 15 H5" fill="none" stroke="currentColor" stroke-width="1.6"/></svg>';

const TETO_FS = 15;                    // px; o corpo de blocos cresce até aqui, não mais

function transborda(el) { return el.scrollWidth > el.clientWidth + 2; }
function ehCaderno(topico) { return !!(topico.caderno && typeof CADERNOS !== 'undefined' && CADERNOS[topico.caderno]); }

function bolinhas(ativo) {
  return '<div class="bolinhas">' + EDICAO.topicos.map((t, i) => {
    const feita = typeof emDia === 'function' && emDia(i);
    return '<button class="bolinha' + (feita ? ' feita' : '') + '" data-cad="' + i + '" title="' + t.nome
      + (feita ? ' — em dia' : '') + '" aria-label="' + t.nome + '" aria-current="' + (i === ativo) + '"></button>';
  }).join('') + '</div>';
}

function cinta(indice, total, ti) {
  return '<div class="cinta"><span>' + EDICAO.dia + '</span><span>' + EDICAO.data + '</span>'
    + '<span class="so-largo">Edição ' + EDICAO.numero + '</span>'
    + '<span>Folha ' + (indice + 1) + ' de ' + total + '</span>'
    + (typeof faltaCinta === 'function' ? faltaCinta() : '')
    + bolinhas(ti) + '</div>';
}

function cabeca(topico, cont, chapeu) {
  return '<div class="cabeca"><div class="chapeu">' + (chapeu || topico.chapeu) + '</div>'
    + '<h2>' + topico.nome + '</h2>'
    + (cont > 0 ? '<span class="cont">continuação · folha ' + (cont + 1) + '</span>' : '')
    + '</div>';
}

/* Quebra obrigatória: bloco marcado com data-quebra abre folha nova e troca o chapéu. */
function quebras(topico) {
  const caixa = document.createElement('div');
  return topico.blocos.map(html => {
    caixa.innerHTML = html;
    const no = caixa.firstElementChild;
    return (no && no.dataset.quebra) || null;
  });
}

function chapeuDa(topico, primeiro) {
  const marcas = quebras(topico);
  let chapeu = topico.chapeu;
  for (let i = 0; i <= primeiro; i++) if (marcas[i]) chapeu = marcas[i];
  return chapeu;
}

/* Distribui os blocos de cada tópico de BLOCOS em folhas, medindo numa folha invisível.
   Um bloco nunca é partido no meio: quando não cabe, vai inteiro para a folha seguinte.
   Caderno não entra aqui — as páginas dele são fixas. */
function __paginar() {
  const medidor = document.getElementById('medidor');
  medidor.innerHTML = '';
  const folha = document.createElement('div');
  folha.className = 'folha';
  const dentro = document.createElement('div');
  dentro.className = 'dentro';
  const topo = document.createElement('div');
  const cab = document.createElement('div');
  const corpo = document.createElement('div');
  corpo.className = 'corpo';
  const pe = document.createElement('div');
  pe.className = 'rodape';
  pe.style.height = '46px';
  dentro.append(topo, cab, corpo, pe);
  folha.appendChild(dentro);
  medidor.appendChild(folha);

  const folhas = [];
  EDICAO.topicos.forEach((topico, ti) => {
    if (ehCaderno(topico)) return;
    const marcas = quebras(topico);
    let cont = 0, postos = 0;
    while (postos < topico.blocos.length) {
      if (marcas[postos]) cont = 0;              // grupo novo recomeça a contagem
      topo.innerHTML = '<div class="cinta"><span>medida</span></div>';
      cab.innerHTML = cabeca(topico, cont, chapeuDa(topico, postos));
      corpo.innerHTML = '';
      const cabem = [];
      for (let i = postos; i < topico.blocos.length; i++) {
        if (marcas[i] && cabem.length) break;    // quebra obrigatória fecha a folha aqui
        const caixa = document.createElement('div');
        caixa.innerHTML = topico.blocos[i];
        const no = caixa.firstElementChild;
        corpo.appendChild(no);
        if (transborda(corpo)) {
          // bloco sozinho que não cabe fica assim mesmo — não dá para partir
          if (cabem.length === 0) cabem.push(i); else corpo.removeChild(no);
          break;
        }
        cabem.push(i);
      }
      folhas.push({ topico: ti, blocos: cabem.slice(), cont: cont });
      postos = cabem[cabem.length - 1] + 1;
      cont++;
    }
  });
  medidor.innerHTML = '';
  return folhas;
}

/* ---------- navegação por (tópico, página) ---------- */

let LEGADO = null;                     // folhas medidas dos tópicos de blocos
const NAV = { t: 0, p: 0, ultima: {} };

/* As páginas de um tópico. Caderno pode mudar de páginas conforme o estado (a Compras
   troca de seções quando ele escolhe outro ciclo), por isso é calculado a cada desenho. */
function paginasDe(ti) {
  const topico = EDICAO.topicos[ti];
  if (ehCaderno(topico)) return CADERNOS[topico.caderno].paginas(topico, ti);
  const folhas = LEGADO.filter(f => f.topico === ti);
  return folhas.length ? folhas.map(f => ({ legado: f })) : [{ legado: { topico: ti, blocos: [], cont: 0 } }];
}

function posicao() {
  let antes = 0, total = 0;
  EDICAO.topicos.forEach((_, i) => {
    const n = paginasDe(i).length;
    if (i < NAV.t) antes += n;
    total += n;
  });
  return { indice: antes + NAV.p, total };
}

function redesenhar() { desenhar(); }

function desenhar() {
  const topico = EDICAO.topicos[NAV.t];
  const paginas = paginasDe(NAV.t);
  if (NAV.p >= paginas.length) NAV.p = paginas.length - 1;
  if (NAV.p < 0) NAV.p = 0;
  const pg = paginas[NAV.p];
  const { indice, total } = posicao();
  const palco = document.getElementById('palco');
  const rolagem = palco.querySelector('.corpo.pagina');
  const manterRolagem = rolagem && palco.dataset.onde === NAV.t + ':' + NAV.p ? rolagem.scrollTop : 0;

  const folha = document.createElement('div');
  folha.className = 'folha';
  const grao = document.createElement('div');
  grao.className = 'grao';
  const moldura = document.createElement('div');
  moldura.className = 'moldura';
  const dentro = document.createElement('div');
  dentro.className = 'dentro';

  const corpo = document.createElement('div');
  if (pg.legado) {
    const f = pg.legado;
    dentro.innerHTML = cinta(indice, total, NAV.t) + cabeca(topico, f.cont, chapeuDa(topico, f.blocos[0] || 0));
    corpo.className = 'corpo';
    corpo.innerHTML = f.blocos.map(i => topico.blocos[i]).join('');
  } else {
    const extra = CADERNOS[topico.caderno].cabeca ? CADERNOS[topico.caderno].cabeca(topico, NAV.t) : '';
    dentro.innerHTML = cinta(indice, total, NAV.t)
      + '<div class="cabeca"><div class="chapeu">' + topico.chapeu + '</div><h2>' + topico.nome + '</h2>'
      + '<nav class="sumario-cad" aria-label="páginas do caderno">' + paginas.map((p, i) =>
        '<button data-pag="' + i + '" aria-current="' + (i === NAV.p) + '">' + p.nome + '</button>').join('') + '</nav>'
      + extra + '</div>';
    corpo.className = 'corpo pagina';
    corpo.innerHTML = pg.f();
  }
  dentro.appendChild(corpo);

  const pe = document.createElement('div');
  pe.className = 'rodape';
  const ultimo = NAV.t === EDICAO.topicos.length - 1 && NAV.p === paginas.length - 1;
  const onde = pg.legado
    ? '<span class="numero">' + (indice + 1) + ' / ' + total + '</span>'
    : '<span class="onde">' + topico.nome + ' · ' + pg.nome + '<small>página ' + (NAV.p + 1) + ' de '
      + paginas.length + ' · folha ' + (indice + 1) + ' / ' + total + '</small></span>';
  pe.innerHTML = '<button class="seta" data-passo="-1"' + (indice === 0 ? ' disabled' : '') + ' aria-label="página anterior">' + SETA_ESQ + '</button>'
    + onde
    + '<button class="seta" data-passo="1"' + (ultimo ? ' disabled' : '') + ' aria-label="próxima página">' + SETA_DIR + '</button>';
  dentro.appendChild(pe);

  folha.append(grao, moldura, dentro);
  palco.innerHTML = '';
  palco.appendChild(folha);
  palco.dataset.onde = NAV.t + ':' + NAV.p;

  if (pg.legado) {
    // colunas adaptativas: folha com pouco conteúdo não merece 3 colunas.
    // A paginação foi medida em 3 colunas, então 2 colunas pode não caber — daí a volta atrás.
    corpo.style.columnCount = 2;
    if (transborda(corpo)) corpo.style.columnCount = 3;
    // auto-fit tipográfico: o corpo cresce até quase estourar, com teto.
    let fs = 13.5;
    corpo.style.setProperty('--fs', fs + 'px');
    while (fs < TETO_FS) {
      const passo = +(fs + 0.4).toFixed(2);
      corpo.style.setProperty('--fs', passo + 'px');
      if (transborda(corpo)) { corpo.style.setProperty('--fs', fs + 'px'); break; }
      fs = passo;
    }
  } else {
    if (pg.depois) pg.depois(corpo);
    corpo.scrollTop = manterRolagem;
  }

  NAV.ultima[topico.id] = NAV.p;
  try { localStorage.setItem('diario.ultima.' + EDICAO.iso, JSON.stringify(NAV.ultima)); } catch (e) { /* sem storage */ }
  if (history.replaceState) history.replaceState(null, '', '#' + topico.id + '/' + (NAV.p + 1));
}

function passo(n) {
  let t = NAV.t, p = NAV.p + n;
  if (p < 0) {
    if (t === 0) return;
    t--; p = paginasDe(t).length - 1;
  } else if (p >= paginasDe(t).length) {
    if (t === EDICAO.topicos.length - 1) return;
    t++; p = 0;
  }
  NAV.t = t; NAV.p = p;
  desenhar();
}

/* Trocar de tópico volta para a página em que ele parou naquele tópico. */
function irTopico(t, p) {
  if (t < 0 || t >= EDICAO.topicos.length) return;
  NAV.t = t;
  NAV.p = p !== undefined ? p : (NAV.ultima[EDICAO.topicos[t].id] || 0);
  desenhar();
}

function indiceDo(id) { return EDICAO.topicos.findIndex(t => t.id === id); }

function pelaUrl() {
  const [id, pg] = decodeURIComponent(location.hash.slice(1)).split('/');
  const t = indiceDo(id);
  if (t < 0) return false;
  NAV.t = t; NAV.p = Math.max(0, (+pg || 1) - 1);
  return true;
}

function abrir() {
  // as folhas do build servem de primeira leitura; a medição local manda, porque a tela muda
  LEGADO = __paginar();
  desenhar();
}

if (typeof window !== 'undefined') {
  window.__paginar = __paginar;
  window.addEventListener('DOMContentLoaded', () => {
    LEGADO = EDICAO.folhas && EDICAO.folhas.length ? EDICAO.folhas : __paginar();
    try { NAV.ultima = JSON.parse(localStorage.getItem('diario.ultima.' + EDICAO.iso) || '{}') || {}; } catch (e) { NAV.ultima = {}; }
    if (!pelaUrl() && typeof paginaInicial === 'function') {
      const ini = paginaInicial();
      if (ini) { NAV.t = ini.t; NAV.p = ini.p; }
    }
    desenhar();
    requestAnimationFrame(abrir);          // confere a medição na tela real
    if (typeof carregarEstadoVivo === 'function') carregarEstadoVivo();
  });
  window.addEventListener('hashchange', () => { if (pelaUrl()) desenhar(); });
  let t;
  window.addEventListener('resize', () => { clearTimeout(t); t = setTimeout(abrir, 180); });
  window.addEventListener('keydown', ev => {
    if (ev.target.closest && ev.target.closest('input,textarea,select')) return;
    if (ev.key === 'ArrowLeft') passo(-1);
    if (ev.key === 'ArrowRight') passo(1);
    if (ev.key === 'ArrowDown') { ev.preventDefault(); irTopico(NAV.t + 1); }
    if (ev.key === 'ArrowUp') { ev.preventDefault(); irTopico(NAV.t - 1); }
  });
  let toque = null;
  document.addEventListener('touchstart', ev => { toque = ev.touches[0].clientX; }, { passive: true });
  document.addEventListener('touchend', ev => {
    if (toque === null || (ev.target.closest && ev.target.closest('.grafico,input,table'))) { toque = null; return; }
    const dx = ev.changedTouches[0].clientX - toque;
    toque = null;
    if (Math.abs(dx) > 70) passo(dx < 0 ? 1 : -1);
  });
  // a navegação escuta o documento inteiro: as bolinhas moram na cinta e os links nas páginas
  document.addEventListener('click', ev => {
    const b = ev.target.closest('button,[data-ir]');
    if (!b || !b.closest('#palco')) return;
    if (b.dataset.passo) return passo(+b.dataset.passo);
    if (b.dataset.cad !== undefined) return irTopico(+b.dataset.cad);
    if (b.dataset.pag !== undefined) { NAV.p = +b.dataset.pag; return desenhar(); }
    if (b.dataset.ir) {
      const [id, p] = b.dataset.ir.split(':');
      const t = indiceDo(id);
      if (t >= 0) irTopico(t, p === undefined || p === '' ? undefined : +p);
    }
  });
}
