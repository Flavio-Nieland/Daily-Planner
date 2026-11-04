/* Caderno do Álbum: um disco por página, e a discoteca com o link da planilha.

   Pedido dele (2026-11-03): uma página para o disco do gosto, outra para o do estilo
   pedido, e a planilha do histórico à mão. Com a página inteira para um disco, a capa
   volta a ser grande — o problema da capa espremida na coluna (PR #27) deixa de existir.
   A nota "gostei / não curti / não ouvi" vai para `feito` (disco:<data>:<origem>) e
   ensina o gosto sem depender do Spotify. */

function pgDisco(d, qual) {
  const x = d[qual];
  if (!x) {
    return '<div class="falhou-caixa"><div class="rotulo">Sem o disco do seu gosto hoje</div>'
      + '<p>O perfil do Spotify não veio' + (d.sem_spotify ? ': ' + esc(d.sem_spotify) : '') + ', e ainda não há perfil salvo.</p>'
      + '<p class="miudo">O disco do estilo pedido, na página seguinte, não depende disso.</p></div>';
  }
  const capa = x.capa ? '<img class="capa" src="' + esc(x.capa) + '" alt="capa de ' + esc(x.album) + '" loading="eager">'
    : '<div class="capa sem"><span>' + esc(x.album) + '</span></div>';
  const ouvir = x.id ? '<a class="botao ouvir" href="https://open.spotify.com/album/' + esc(x.id) + '" target="_blank" rel="noopener">▶ ouvir no Spotify</a>' : '';
  const hist = esc(x.historia);
  const aviso = qual === 'gosto' && d.sem_spotify && d.perfil_de
    ? '<div class="aviso-cache">Spotify fora do ar — escolhido pelo seu último perfil salvo (' + ddmm(d.perfil_de) + ').</div>' : '';
  const caixa = qual === 'estilo' ? '<div class="caixa-estilo"><div class="rotulo">Quer ouvir outro estilo?</div>'
    + '<p class="campo-linha"><input type="text" id="estilo-valor" placeholder="jazz modal" aria-label="estilo que você quer ouvir" data-dia="' + d.hoje + '">'
    + '<button type="button" class="botao" id="estilo-gravar">pedir</button></p>'
    + (d.pendente ? '<p class="miudo">Você pediu "' + esc(d.pendente) + '" hoje — entra na edição de amanhã.</p>'
      : '<p class="miudo">Em vigor: ' + esc(d.vigente) + '.</p>')
    + '<p class="miudo" id="estilo-aviso">O pedido vale a partir de amanhã e fica até você trocar.</p></div>' : '';
  return '<div class="disco-pg"><div>' + capa + ouvir + '</div><div>' + aviso
    + '<div class="chapeu">' + (qual === 'gosto' ? 'Pelo seu gosto' : 'Pelo estilo pedido') + (x.ano ? ' · ' + esc(x.ano) : '') + '</div>'
    + '<h3 class="grande">' + esc(x.album) + '</h3><p class="art">' + esc(x.artista) + '</p>'
    + '<p class="hist"><span class="capitular">' + hist.charAt(0) + '</span>' + hist.slice(1) + '</p>'
    + (x.faixa ? '<div class="faixa"><b>Faixa-chave</b>' + esc(x.faixa) + '</div>' : '')
    + '<div class="nota">' + comoFoi('disco:' + d.hoje + ':' + qual, ['gostei', 'não curti', 'não ouvi'], false, 'Ouviu?') + '</div>'
    + caixa + '</div></div>';
}

function pgDiscoteca(d) {
  const linhas = d.discoteca.map(r => {
    const nota = valorDo('feito', 'disco:' + r.data + ':' + r.origem);
    return '<li><span class="d">' + ddmm(r.data) + '</span>' + esc(r.album) + ' — <i>' + esc(r.artista) + '</i>'
      + ' <span class="miudo">· ' + (r.origem === 'gosto' ? 'gosto' : 'pedido') + (nota ? ' · <b>' + esc(nota) + '</b>' : '') + '</span></li>';
  }).join('');
  return '<div class="planilha"><div><div class="chapeu">A planilha</div><p class="grande">Albuns claude</p>'
    + '<p class="miudo">Cada edição grava uma linha com os dois discos do dia e a nota que você deu. Recomeçou do zero em 03/11/2026.</p></div>'
    + '<a class="botao" href="' + esc(d.planilha) + '" target="_blank" rel="noopener">abrir ↗</a></div>'
    + '<div class="rotulo">Desde o recomeço<span class="dir">' + d.discoteca.length + ' discos</span></div>'
    + (linhas ? '<ul class="discos">' + linhas + '</ul>' : '<p class="vazio">Os discos entram aqui a partir de hoje.</p>')
    + '<p class="miudo" style="margin-top:10px">A nota de cada disco ensina o gosto sem depender do Spotify.</p>';
}

CADERNOS.album = {
  paginas: (topico) => [
    { nome: 'Pelo seu gosto', f: () => pgDisco(topico.dados, 'gosto') },
    { nome: 'Pelo estilo pedido', f: () => pgDisco(topico.dados, 'estilo') },
    { nome: 'Discoteca', f: () => pgDiscoteca(topico.dados) },
  ],
};
