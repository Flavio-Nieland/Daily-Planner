"""Curva pequena desenhada no build, em SVG puro — sem JS e sem biblioteca.

Nasceu na folha do Peso; desde que o Peso virou caderno com curva interativa
(2026-11-03), quem usa é o Xadrez, para o Elo.
"""

LARGURA, ALTURA, MARGEM = 260, 96, 8


def grafico(pontos: list[tuple[str, float]]) -> str:
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
