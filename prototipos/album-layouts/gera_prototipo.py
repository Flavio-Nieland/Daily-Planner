"""PROTÓTIPO — descartável. Gera o HTML com as variantes de layout da folha do Álbum."""
import json

css = open("estilo.css", encoding="utf-8").read()
alb = json.load(open("album.json", encoding="utf-8"))
blocos = alb["blocos"]

VARIANTES = [
    ("atual", "Como está hoje", "3 colunas, capa = largura da coluna. O baseline."),
    ("A", "Ficha horizontal", "Capa pequena à esquerda, texto correndo em volta. 2 colunas."),
    ("B", "Cartaz duplo", "Sem multi-coluna: um disco por metade, capa média no topo."),
    ("C", "Manchete de jornal", "Um disco em destaque com texto em volta, o outro em nota curta."),
    ("D", "Teto na capa", "Mantém as 3 colunas de hoje, mas a capa nunca passa de 34% do corpo."),
]

TELAS = [
    ("notebook", "Notebook 1366×768", 1366, 768),
    ("desktop", "Desktop 1920×1080", 1920, 1080),
    ("grande", "Desktop 2560×1440", 2560, 1440),
    ("dele", "A sua tela (zoom alto)", 1100, 620),
]

overrides = """
/* ===================== PROTÓTIPO: overrides por variante ===================== */
/* A folha do protótipo tem tamanho simulado, não 100vh */
#palco .folha{width:var(--fw)!important;height:var(--fh)!important;max-height:none!important}

/* --- A: ficha horizontal. A capa deixa de ditar a altura: vira um selo de 120px e o
       texto corre em volta dela. Duas colunas, porque a linha fica curta demais em três. */
[data-v="A"] .corpo{column-count:2!important}
[data-v="A"] .disco .capa{float:left;width:120px;aspect-ratio:1;margin:2px 10px 4px 0}
[data-v="A"] .disco .destaque-texto{margin-top:0}
[data-v="A"] .disco::after{content:"";display:block;clear:both}

/* --- B: cartaz duplo. Abandona multi-coluna e usa grid: um disco por metade, capa média
       no topo de cada um, e a caixa de estilo numa faixa que atravessa as duas. */
[data-v="B"] .corpo{column-count:auto!important;display:grid;
  grid-template-columns:1fr 1fr;grid-template-rows:1fr auto;gap:0 26px;
  column-rule:none!important}
[data-v="B"] .corpo>.disco{border-right:1px solid var(--rule);padding-right:24px;min-width:0}
[data-v="B"] .corpo>.disco:nth-of-type(2){border-right:none;padding-right:0}
[data-v="B"] .disco .capa{width:min(62%,200px);aspect-ratio:1;margin:0 auto 8px}
[data-v="B"] .corpo>.bloco:last-child{grid-column:1/-1;border-top:1px solid var(--ink);
  margin-top:8px;padding-top:8px;display:flex;gap:18px;align-items:baseline}
[data-v="B"] .corpo>.bloco:last-child h4{margin:0;white-space:nowrap}

/* --- C: manchete de jornal. O disco do gosto é a matéria de capa: ocupa a largura toda,
       com a capa grande em float e o texto correndo em volta. O pedido vira nota curta. */
[data-v="C"] .corpo{column-count:auto!important;display:grid;
  grid-template-columns:1fr 260px;gap:0 26px;column-rule:none!important}
[data-v="C"] .corpo>.disco:nth-of-type(1){grid-column:1;min-width:0}
[data-v="C"] .corpo>.disco:nth-of-type(1) .capa{float:left;width:min(46%,230px);aspect-ratio:1;
  margin:2px 14px 6px 0}
[data-v="C"] .corpo>.disco:nth-of-type(1) .destaque-texto{font-size:1.5em}
[data-v="C"] .corpo>.disco:nth-of-type(2){grid-column:2;grid-row:1/span 2;
  border-left:1px solid var(--rule);padding-left:22px;font-size:.94em;min-width:0}
[data-v="C"] .corpo>.disco:nth-of-type(2) .capa{width:84px;aspect-ratio:1;float:left;
  margin:2px 10px 4px 0}
[data-v="C"] .corpo>.bloco:last-child{grid-column:1;align-self:end;
  border-top:1px solid var(--ink);padding-top:8px}

/* --- D: mudança mínima. Mantém as 3 colunas de hoje; só impede a capa de crescer além de
       34% da altura do corpo (--capamax vem do JS, que é quem conhece essa altura). */
[data-v="D"] .disco .capa{width:auto;max-width:100%;height:var(--capamax);aspect-ratio:1;
  object-fit:cover;margin:0 auto 6px}

/* ===================== PROTÓTIPO: chrome (não faz parte do design) ===================== */
body{background:#1e1c19;margin:0;font-family:system-ui,sans-serif}
#palco{display:flex;align-items:center;justify-content:center;padding:26px 0 92px}
#barra{position:fixed;bottom:14px;left:50%;transform:translateX(-50%);z-index:99;
  display:flex;gap:10px;align-items:center;background:#111;color:#fff;
  border:1px solid #555;border-radius:999px;padding:8px 14px;font:13px/1.2 system-ui,sans-serif;
  box-shadow:0 6px 24px #0009}
#barra button{background:#2b2b2b;color:#fff;border:1px solid #666;border-radius:8px;
  padding:5px 11px;cursor:pointer;font-size:14px}
#barra button:hover{background:#3d3d3d}
#barra select{background:#2b2b2b;color:#fff;border:1px solid #666;border-radius:8px;padding:5px 8px}
#nome{min-width:210px;text-align:center;font-weight:600}
#metricas{position:fixed;top:12px;left:12px;z-index:99;background:#111e;color:#eee;
  border:1px solid #555;border-radius:10px;padding:10px 13px;
  font:12px/1.6 ui-monospace,monospace;white-space:pre}
#metricas b{color:#ffd479}
.ruim{color:#ff7b6b;font-weight:700}
.bom{color:#8ddf8d;font-weight:700}
#nota{position:fixed;top:12px;right:12px;z-index:99;max-width:290px;background:#111e;color:#ddd;
  border:1px solid #555;border-radius:10px;padding:10px 13px;font:12px/1.5 system-ui,sans-serif}
"""

vjs = json.dumps([{"id": v[0], "nome": v[1], "nota": v[2]} for v in VARIANTES], ensure_ascii=False)
tjs = json.dumps([{"id": t[0], "nome": t[1], "w": t[2], "h": t[3]} for t in TELAS], ensure_ascii=False)
bjs = json.dumps(blocos, ensure_ascii=False)

html = f"""<!doctype html>
<meta charset="utf-8">
<title>PROTÓTIPO — layouts da folha do Álbum</title>
<!--
  PROTÓTIPO DESCARTÁVEL — gerado em 07/09/2026.
  Pergunta que ele responde: como a folha do Álbum deve ocupar o espaço, no notebook e no
  desktop, sem a capa comer a folha e deixar coluna vazia?
  Trocar variante: setas do rodapé, teclas ← →, ou ?variant=A na URL.
  Trocar o tamanho de tela simulado: o seletor no rodapé.
-->
<style>{css}</style>
<style>{overrides}</style>
<body>
<div id="metricas"></div>
<div id="nota"></div>
<div id="palco"></div>
<div id="barra">
  <button id="ant">←</button>
  <span id="nome"></span>
  <button id="prox">→</button>
  <select id="tela"></select>
</div>
<script>
const VARIANTES = {vjs};
const TELAS = {tjs};
const BLOCOS = {bjs};

let iv = Math.max(0, VARIANTES.findIndex(v =>
  v.id === (new URLSearchParams(location.search).get('variant') || 'atual')));
let it = 0;

function desenhar() {{
  const v = VARIANTES[iv], t = TELAS[it];
  const fw = Math.min(1000, Math.round(t.w * 0.97));
  const fh = Math.min(920, t.h - 28);

  document.getElementById('palco').innerHTML = `
    <div class="folha" data-v="${{v.id}}" style="--fw:${{fw}}px;--fh:${{fh}}px">
      <div class="grao"></div><div class="moldura"></div>
      <div class="dentro">
        <div class="cinta"><span>segunda-feira</span><span>07/09/2026</span>
          <span>Edição 20260907</span><span>Folha 6 de 11</span></div>
        <div class="cabeca"><div class="chapeu">Dois discos por dia</div><h2>Álbum</h2></div>
        <div class="corpo">${{BLOCOS.join('')}}</div>
        <div class="rodape"><span class="numero">6 / 11</span></div>
      </div>
    </div>`;

  const corpo = document.querySelector('.corpo');
  // a capa da variante D precisa saber a altura do corpo — só o JS conhece
  corpo.style.setProperty('--capamax', Math.round(corpo.clientHeight * 0.34) + 'px');

  autofit(corpo);
  requestAnimationFrame(() => medir(v, t, fw, fh));
  document.getElementById('nome').textContent = v.id + ' — ' + v.nome;
  document.getElementById('nota').innerHTML = '<b>' + v.nome + '</b><br>' + v.nota;
  const u = new URL(location); u.searchParams.set('variant', v.id);
  history.replaceState(null, '', u);
}}

/* mesmo laço do paginar.js: cresce a fonte até quase estourar, com teto de 15px */
function autofit(corpo) {{
  const transborda = () => corpo.scrollWidth > corpo.clientWidth + 2
                        || corpo.scrollHeight > corpo.clientHeight + 2;
  let fs = 13.5;
  corpo.style.setProperty('--fs', fs + 'px');
  while (fs < 15) {{
    const passo = +(fs + 0.4).toFixed(2);
    corpo.style.setProperty('--fs', passo + 'px');
    if (transborda()) {{ corpo.style.setProperty('--fs', fs + 'px'); break; }}
    fs = passo;
  }}
}}

function medir(v, t, fw, fh) {{
  const corpo = document.querySelector('.corpo');
  const capas = [...corpo.querySelectorAll('img.capa')];
  const escondido = corpo.scrollWidth - corpo.clientWidth;
  const alturaCapa = capas.length ? Math.round(capas[0].clientHeight) : 0;
  const pct = corpo.clientHeight ? Math.round(100 * alturaCapa / corpo.clientHeight) : 0;
  // quanto do corpo tem texto de verdade, por coluna: aproximação pelo texto visível
  const texto = corpo.innerText.trim().length;
  const veredito = escondido > 2
    ? '<span class="ruim">ESCONDE ' + escondido + 'px</span>'
    : '<span class="bom">nada escondido</span>';
  const capaOk = pct <= 45 ? '<span class="bom">' + pct + '%</span>'
                           : '<span class="ruim">' + pct + '%</span>';
  document.getElementById('metricas').innerHTML =
    'tela      ' + t.nome + '\\n' +
    'folha     ' + fw + ' × ' + fh + 'px\\n' +
    'corpo     ' + Math.round(corpo.clientHeight) + 'px de altura\\n' +
    'colunas   ' + (getComputedStyle(corpo).columnCount === 'auto' ? 'grid' : getComputedStyle(corpo).columnCount) + '\\n' +
    'capa      ' + alturaCapa + 'px = ' + capaOk + ' do corpo\\n' +
    'texto     ' + texto + ' caracteres visíveis\\n' +
    'transbordo ' + veredito;
}}

document.getElementById('ant').onclick = () => {{ iv = (iv - 1 + VARIANTES.length) % VARIANTES.length; desenhar(); }};
document.getElementById('prox').onclick = () => {{ iv = (iv + 1) % VARIANTES.length; desenhar(); }};
addEventListener('keydown', e => {{
  if (['INPUT','TEXTAREA'].includes(e.target.tagName) || e.target.isContentEditable) return;
  if (e.key === 'ArrowLeft') document.getElementById('ant').click();
  if (e.key === 'ArrowRight') document.getElementById('prox').click();
}});
const sel = document.getElementById('tela');
sel.innerHTML = TELAS.map((t, i) => `<option value="${{i}}">${{t.nome}}</option>`).join('');
sel.onchange = () => {{ it = +sel.value; desenhar(); }};
addEventListener('resize', () => desenhar());
desenhar();
</script>
"""
destino = "/mnt/c/Users/flavi/Downloads/album-layouts-prototipo.html"
open(destino, "w", encoding="utf-8").write(html)
print("gerado:", destino, len(html), "bytes")
