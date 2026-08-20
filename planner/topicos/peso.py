"""Folha do Peso — só entrada dele mais visualização, sem LLM e sem API externa.

É o caso de teste do caminho de escrita (Worker → KV → estado.json): se o peso não
persistir, nada persiste. A curva é diária, não semanal: ele registra quando quiser e
cada valor entra no gráfico.
"""

from datetime import date

LARGURA, ALTURA, MARGEM = 260, 96, 8


def _grafico(pontos: list[tuple[str, float]]) -> str:
    """Curva da série completa, desenhada no build — sem JS, sem biblioteca."""
    if len(pontos) < 2:
        return ""
    valores = [kg for _, kg in pontos]
    menor, maior = min(valores), max(valores)
    faixa = (maior - menor) or 1
    passo = (LARGURA - 2 * MARGEM) / (len(pontos) - 1)

    coords = [
        (MARGEM + i * passo,
         ALTURA - MARGEM - (kg - menor) / faixa * (ALTURA - 2 * MARGEM))
        for i, (_, kg) in enumerate(pontos)
    ]
    linha = " ".join(f"{x:.1f},{y:.1f}" for x, y in coords)
    ultimo_x, ultimo_y = coords[-1]
    return (
        f'<svg viewBox="0 0 {LARGURA} {ALTURA}" class="curva" role="img" '
        f'aria-label="curva do peso, {len(pontos)} registros">'
        f'<polyline points="{linha}" fill="none" stroke="currentColor" stroke-width="1.4"/>'
        f'<circle cx="{ultimo_x:.1f}" cy="{ultimo_y:.1f}" r="2.6" fill="currentColor"/>'
        f'</svg>'
        f'<p class="miudo">{menor:.1f} kg a {maior:.1f} kg · {len(pontos)} registros</p>'
    )


def blocos(dia: date, serie: list[tuple[str, float]]) -> list[str]:
    registro = (
        '<div class="bloco" id="peso-registro">'
        '<h4>Registrar o peso de hoje</h4>'
        '<p class="campo"><input type="text" inputmode="decimal" id="peso-valor" '
        f'placeholder="78,4" aria-label="peso de hoje em quilos" data-dia="{dia.isoformat()}">'
        '<button type="button" id="peso-gravar">gravar</button></p>'
        '<p class="miudo" id="peso-aviso">Vai para o seu Worker; a curva do jornal atualiza amanhã.</p>'
        '</div>'
    )

    if not serie:
        return [registro,
                '<div class="bloco"><h4>Sem medidas ainda</h4>'
                '<p>O primeiro registro começa a curva.</p></div>']

    data_ultima, ultima = serie[-1]
    quando = f"{data_ultima[8:]}/{data_ultima[5:7]}"
    if len(serie) > 1:
        anterior = serie[-2][1]
        delta = ultima - anterior
        sinal = "+" if delta > 0 else ""
        variacao = (f'<p class="miudo">{sinal}{delta:.1f} kg desde '
                    f'{serie[-2][0][8:]}/{serie[-2][0][5:7]}</p>')
    else:
        variacao = '<p class="miudo">primeira medida</p>'

    ultima_medida = (
        f'<div class="bloco"><h4>Última medida</h4>'
        f'<p class="destaque">{ultima:.1f} kg</p>'
        f'<p class="miudo">em {quando}</p>{variacao}</div>'
    )

    curva = _grafico(serie)
    if curva:
        return [registro, ultima_medida, f'<div class="bloco"><h4>A curva</h4>{curva}</div>']
    return [registro, ultima_medida]
