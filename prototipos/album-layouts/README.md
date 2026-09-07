# PROTÓTIPO — layouts da folha do Álbum (07/09/2026)

**Branch descartável. Não mergear na `main`.** Só a decisão validada volta para lá.

## A pergunta

Como a folha do Álbum deve ocupar o espaço, no notebook e no desktop, sem a capa comer a
folha e sem deixar coluna vazia? Ele mandou o print de uma folha em que a primeira das três
colunas tinha só o título `PELO SEU GOSTO` e nada mais.

## O diagnóstico

A folha tem largura **fixa**: `.folha{width:min(1000px,97vw)}`. Tela grande não a alarga —
mas a **altura** acompanha a viewport (`height:calc(100vh - 28px)`, teto de 920px). A capa é
`width:100%` da coluna, então sua **altura** é a largura da coluna, um número que não sabe
nada sobre a altura disponível:

| tela | colunas | coluna | capa | capa / altura do corpo |
|---|---|---|---|---|
| notebook 1366×768 | 2 | 455px | 455px | **79%** |
| desktop 1920×1080 | 3 | 293px | 293px | 39% |
| desktop 2560×1440 | 3 | 293px | 293px | 39% |
| a tela dele (zoom alto) | 3 | 293px | 294px | **68%** |

Com a capa ocupando 68–79% da altura, não sobra espaço para o texto na mesma coluna. O
`break-inside:avoid` do bloco é ignorado (o bloco não cabe em coluna nenhuma), o browser
parte onde dá, e o `<h4>` fica órfão numa coluna inteira.

## As variantes

Abrir `album-layouts-prototipo.html` (gerado em `~/Downloads`), trocar com as setas do
rodapé, as teclas ← →, ou `?variant=A`. O seletor do rodapé simula notebook, dois desktops
e a tela dele.

| id | nome | ideia |
|---|---|---|
| `atual` | Como está hoje | baseline, para comparar |
| `A` | Ficha horizontal | capa vira selo de 120px, texto corre em volta; 2 colunas |
| `B` | Cartaz duplo | sem multi-coluna: grid de 2, capa média no topo de cada disco |
| `C` | Manchete de jornal | um disco em destaque com texto em volta, o outro em nota estreita |
| `D` | Teto na capa | mudança mínima: mantém as 3 colunas, capa limitada a 34% do corpo |

## O que a medição mostrou (notebook, o pior caso)

| variante | capa | fonte do auto-fit | conteúdo cortado |
|---|---|---|---|
| atual | 49% | 13,5px (travada no mínimo) | **325px** |
| **A** | **20%** | **15,1px (no teto)** | **0** |
| B | 33% | 13,5px | 35px |
| C | 38% | 14,7px | 0 |
| D | 34% | 13,5px | **325px** |

Duas conclusões que só apareceram por medir:

1. **`D` não resolve.** Limitar a altura da capa não basta: o problema não é só a capa, são
   três colunas estreitas com um texto de 600+ caracteres por disco. Isso mata a hipótese
   "muda uma linha de CSS e pronto".
2. **A folga vira tamanho de letra.** O auto-fit de `paginar.js` cresce a fonte até quase
   estourar, com teto de 15px. Nas variantes que sobram espaço a fonte vai a 15,1px; no
   layout atual ela fica travada em 13,5px. Ou seja: o desperdício de espaço estava sendo
   pago em **texto menor**, não só em coluna vazia.

## Pegadinhas do próprio protótipo (valem para os próximos)

- A primeira versão punha `overflow:hidden` nos discos das variantes B e C. As métricas
  ficaram bonitas e **falsas**: o texto era cortado por dentro (35px em B, no notebook), o
  mesmo defeito que o fix da capa acabou de matar. Medir `scrollHeight - clientHeight` de
  cada bloco, não só o transbordo do `.corpo`.
- Sem replicar o auto-fit da fonte, o protótipo julga o layout com texto menor que o real.
- O jornal usa fontes **locais do Windows** (`Bodoni MT`, `Century Schoolbook`) — não há
  `@font-face` nem `<link>`. Em Chromium Linux cai para sans-serif, o que muda as alturas:
  os prints tirados aqui não representam o que ele vê. O veredito visual é na máquina dele.
- A medição só estabiliza depois de ~1,2s: as capas vêm de `i.scdn.co`.

## Veredito

_(a preencher quando ele escolher)_
