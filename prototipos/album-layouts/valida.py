from playwright.sync_api import sync_playwright
import pathlib

ARQ = pathlib.Path("/mnt/c/Users/flavi/Downloads/album-layouts-prototipo.html").as_uri()
VAR = ["atual", "A", "B", "C", "D"]

with sync_playwright() as p:
    nav = p.chromium.launch()
    pag = nav.new_page(viewport={"width": 1500, "height": 1000})
    print(f'{"variante":22} {"tela":24} {"capa %":>7} {"texto":>6} {"escondido":>10}')
    print("-" * 74)
    for v in VAR:
        for it, tela in enumerate(["notebook", "desktop", "grande", "dele"]):
            pag.goto(f"{ARQ}?variant={v}", wait_until="load")
            pag.wait_for_timeout(300)
            pag.select_option("#tela", str(it))
            pag.wait_for_timeout(700)
            d = pag.evaluate("""() => {
                const c = document.querySelector('.corpo');
                const cap = c.querySelector('img.capa');
                return {pct: Math.round(100*(cap?cap.clientHeight:0)/c.clientHeight),
                        texto: c.innerText.trim().length,
                        esc: c.scrollWidth - c.clientWidth,
                        nome: document.getElementById('nome').textContent};
            }""")
            marca = "  " if d["esc"] <= 2 and d["pct"] <= 45 else "❌"
            print(f'{marca}{d["nome"][:20]:20} {tela:24} {d["pct"]:6}% {d["texto"]:6} {d["esc"]:9}px')
        print()
    nav.close()
