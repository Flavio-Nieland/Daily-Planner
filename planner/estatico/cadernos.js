/* Os cadernos: tópicos com páginas nomeadas e diagramação própria.

   Cada caderno se registra em CADERNOS com:
     paginas(topico, ti) -> [{ nome, f: () => html, depois?: corpo => void }]
     cabeca?(topico, ti) -> html extra sob o sumário (ex.: o seletor ontem/hoje/amanhã)
   Os dados vêm do build em topico.dados; o que ele marca vem de ESTADO (estado.js).

   Protótipo aprovado em 2026-11-03: C:\Users\flavi\Downloads\diario-subpaginas-prototipo.html */

const CADERNOS = {};

const SEM = ['dom', 'seg', 'ter', 'qua', 'qui', 'sex', 'sáb'];
const SEMANA = ['domingo', 'segunda-feira', 'terça-feira', 'quarta-feira', 'quinta-feira', 'sexta-feira', 'sábado'];
const esc = s => String(s === undefined || s === null ? '' : s).replace(/[&<>"]/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));
const dt = iso => new Date(iso + 'T12:00:00');
const mais = (iso, n) => { const d = dt(iso); d.setDate(d.getDate() + n); return d.toISOString().slice(0, 10); };
const ddmm = iso => iso.slice(8, 10) + '/' + iso.slice(5, 7);
const curto = iso => SEM[dt(iso).getDay()] + ' ' + ddmm(iso);
const nf = (n, c = 1) => Number(n).toLocaleString('pt-BR', { minimumFractionDigits: c, maximumFractionDigits: c });
const gramas = g => g >= 1000 ? nf(g / 1000, 1) + ' kg' : Math.round(g) + ' g';
const agoraHM = () => new Date().toTimeString().slice(0, 5);
function hojeReal() { const d = new Date(); return new Date(d.getTime() - d.getTimezoneOffset() * 6e4).toISOString().slice(0, 10); }
function dadosDe(id) { const t = EDICAO.topicos.find(x => x.id === id && x.caderno); return t ? t.dados : null; }

/* "Como foi?": botões que gravam uma marcação em `feito`. Clicar de novo desmarca.
   As chaves (refeicao:…, disco:…, compra:…) não têm forma de "tópico:data", então o
   progressao.py do build as ignora — não avançam plano nenhum. */
function comoFoi(chave, opcoes, futuro, rotulo) {
  const v = valorDo('feito', chave);
  return '<div class="comofoi"><span>' + (rotulo || 'Como foi?') + '</span><div class="seg" role="group">'
    + opcoes.map(o => '<button data-marca="' + esc(chave) + '|' + esc(o) + '" aria-pressed="' + (v === o) + '"'
      + (futuro ? ' disabled' : '') + '>' + esc(o) + '</button>').join('')
    + '</div>' + (futuro ? '<span>marca quando chegar o dia</span>' : '') + '</div>';
}

document.addEventListener('click', ev => {
  const b = ev.target.closest('[data-marca]');
  if (!b) return;
  const i = b.dataset.marca.lastIndexOf('|');
  const chave = b.dataset.marca.slice(0, i), valor = b.dataset.marca.slice(i + 1);
  gravarEstado('feito', chave, valorDo('feito', chave) === valor ? false : valor);
});
