from playwright.sync_api import sync_playwright

TELAS = [("notebook 1366x768", 1366, 768), ("desktop 1920x1080", 1920, 1080),
         ("desktop 2560x1440", 2560, 1440), ("como o dele (zoom alto)", 1100, 620)]

with sync_playwright() as p:
    nav = p.chromium.launch()
    for nome, w, h in TELAS:
        pag = nav.new_page(viewport={"width": w, "height": h})
        pag.goto("https://flavio-nieland.github.io/Daily-Planner/", wait_until="load")
        pag.wait_for_timeout(2000)
        alvo = pag.evaluate("FOLHAS.findIndex(f => EDICAO.topicos[f.topico].id === 'album')")
        pag.evaluate(f"ir({alvo})")
        pag.wait_for_timeout(500)
        d = pag.evaluate("""() => {
            const c = document.querySelector('.corpo');
            const cap = c.querySelector('img.capa');
            const f = document.querySelector('.folha');
            return {folhas: FOLHAS.length, folha_w: Math.round(f.clientWidth),
                    corpo_h: Math.round(c.clientHeight), colunas: +getComputedStyle(c).columnCount,
                    capa: cap ? Math.round(cap.clientWidth) : 0,
                    blocos_na_folha: c.children.length};
        }""")
        col = round((d["folha_w"] - 60 - 30 * (d["colunas"] - 1)) / d["colunas"])
        pct = round(100 * d["capa"] / d["corpo_h"]) if d["corpo_h"] else 0
        print(f'{nome:26} folhas={d["folhas"]:3}  folha={d["folha_w"]}px  '
              f'corpo_h={d["corpo_h"]}px  cols={d["colunas"]}  coluna≈{col}px  '
              f'capa={d["capa"]}px = {pct}% da altura do corpo')
        pag.close()
    nav.close()
