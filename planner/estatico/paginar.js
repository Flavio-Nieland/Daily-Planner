/* Paginação da edição — o MESMO código roda nos dois lados:
   no build, o Chromium headless chama window.__paginar() e o resultado é gravado no HTML;
   no cliente, a folha re-pagina ao abrir e ao redimensionar, porque a tela dele não é a do build.

   Armadilha do ADR 0001: multi-coluna transborda na HORIZONTAL. O teste é scrollWidth,
   não scrollHeight — medir altura não detecta nada e a paginação silenciosamente não acontece. */

const SETA_ESQ = '<svg viewBox="0 0 36 30"><path d="M14 6 L5 15 L14 24 M5 15 H31" fill="none" stroke="currentColor" stroke-width="1.6"/></svg>';
const SETA_DIR = '<svg viewBox="0 0 36 30"><path d="M22 6 L31 15 L22 24 M31 15 H5" fill="none" stroke="currentColor" stroke-width="1.6"/></svg>';

function transborda(el) { return el.scrollWidth > el.clientWidth + 2; }

function masthead() {
  return '<div class="mast"><div class="titulo">' + EDICAO.jornal + '</div>'
    + '<div class="linha"><span>' + EDICAO.dia + '</span><span>' + EDICAO.data + '</span>'
    + '<span>Edição ' + EDICAO.numero + '</span></div></div>';
}

function cabeca(topico, cont, indice, total) {
  return '<div class="cabeca"><div class="chapeu">' + topico.chapeu + '</div>'
    + '<h2>' + topico.nome + '</h2>'
    + (cont > 0 ? '<span class="cont">continuação · folha ' + (cont + 1) + '</span>' : '')
    + '</div>';
}

/* Distribui os blocos de cada tópico em folhas, medindo numa folha invisível.
   Um bloco nunca é partido no meio: quando não cabe, vai inteiro para a folha seguinte. */
function __paginar() {
  const medidor = document.getElementById('medidor');
  medidor.innerHTML = '';
  const folha = document.createElement('div');
  folha.className = 'folha';
  const dentro = document.createElement('div');
  dentro.className = 'dentro';
  const mast = document.createElement('div');
  mast.innerHTML = masthead();
  const cab = document.createElement('div');
  const corpo = document.createElement('div');
  corpo.className = 'corpo';
  const pe = document.createElement('div');
  pe.className = 'rodape';
  pe.style.height = '50px';
  dentro.append(mast, cab, corpo, pe);
  folha.appendChild(dentro);
  medidor.appendChild(folha);

  const folhas = [];
  EDICAO.topicos.forEach((topico, ti) => {
    let cont = 0, postos = 0;
    while (postos < topico.blocos.length) {
      cab.innerHTML = cabeca(topico, cont);
      corpo.innerHTML = '';
      const cabem = [];
      for (let i = postos; i < topico.blocos.length; i++) {
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

let FOLHAS = null, atual = 0;

function desenhar() {
  const f = FOLHAS[atual], topico = EDICAO.topicos[f.topico];
  const palco = document.getElementById('palco');

  const folha = document.createElement('div');
  folha.className = 'folha';
  const grao = document.createElement('div');
  grao.className = 'grao';
  const moldura = document.createElement('div');
  moldura.className = 'moldura';
  const dentro = document.createElement('div');
  dentro.className = 'dentro';
  dentro.innerHTML = masthead() + cabeca(topico, f.cont);

  const corpo = document.createElement('div');
  corpo.className = 'corpo';
  corpo.innerHTML = f.blocos.map(i => topico.blocos[i]).join('');
  dentro.appendChild(corpo);

  const pe = document.createElement('div');
  pe.className = 'rodape';
  pe.innerHTML = '<button class="seta" data-passo="-1"' + (atual === 0 ? ' disabled' : '') + '>' + SETA_ESQ + '</button>'
    + '<div class="bolinhas">' + EDICAO.topicos.map((t, i) =>
        '<button class="bolinha" data-topico="' + i + '" title="' + t.nome + '" aria-label="' + t.nome + '"'
        + ' aria-current="' + (i === f.topico) + '"></button>').join('') + '</div>'
    + '<button class="seta" data-passo="1"' + (atual === FOLHAS.length - 1 ? ' disabled' : '') + '>' + SETA_DIR + '</button>'
    + '<span class="numero">' + (atual + 1) + ' / ' + FOLHAS.length + '</span>';
  dentro.appendChild(pe);

  folha.append(grao, moldura, dentro);
  palco.innerHTML = '';
  palco.appendChild(folha);

  // colunas adaptativas: folha com pouco conteúdo não merece 3 colunas.
  // A paginação foi medida em 3 colunas, então 2 colunas pode não caber — daí a volta atrás.
  let colunas = 2;
  corpo.style.columnCount = 2;
  if (transborda(corpo)) { corpo.style.columnCount = 3; colunas = 3; }
  // auto-fit tipográfico: o corpo cresce até quase estourar, como jornal fecha a página
  const MAX = colunas === 2 ? 18.6 : 16.6;
  let fs = 13.5;
  corpo.style.setProperty('--fs', fs + 'px');
  while (fs < MAX) {
    const passo = +(fs + 0.4).toFixed(2);
    corpo.style.setProperty('--fs', passo + 'px');
    if (transborda(corpo)) { corpo.style.setProperty('--fs', fs + 'px'); break; }
    fs = passo;
  }

  pe.addEventListener('click', ev => {
    const b = ev.target.closest('button');
    if (!b) return;
    if (b.dataset.passo) ir(atual + (+b.dataset.passo));
    if (b.dataset.topico !== undefined) ir(FOLHAS.findIndex(x => x.topico === +b.dataset.topico));
  });
}

function ir(i) {
  if (i < 0 || i >= FOLHAS.length || i === atual) return;
  atual = i;
  desenhar();
}

function abrir() {
  // as folhas do build servem de primeira leitura; a medição local manda, porque a tela muda
  FOLHAS = __paginar();
  if (atual >= FOLHAS.length) atual = FOLHAS.length - 1;
  desenhar();
}

if (typeof window !== 'undefined') {
  window.__paginar = __paginar;
  window.addEventListener('DOMContentLoaded', () => {
    FOLHAS = EDICAO.folhas && EDICAO.folhas.length ? EDICAO.folhas : __paginar();
    desenhar();
    requestAnimationFrame(abrir);          // confere a medição na tela real
  });
  let t;
  window.addEventListener('resize', () => { clearTimeout(t); t = setTimeout(abrir, 180); });
  window.addEventListener('keydown', ev => {
    if (ev.key === 'ArrowLeft') ir(atual - 1);
    if (ev.key === 'ArrowRight') ir(atual + 1);
  });
}
