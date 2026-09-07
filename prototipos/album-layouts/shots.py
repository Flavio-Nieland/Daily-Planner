from playwright.sync_api import sync_playwright
import pathlib

ARQ = pathlib.Path("/mnt/c/Users/flavi/Downloads/album-layouts-prototipo.html").as_uri()
VAR = ["atual", "A", "B", "C", "D"]
SAIDA = pathlib.Path("/mnt/c/Users/flavi/Downloads")

with sync_playwright() as p:
    nav = p.chromium.launch()
    pag = nav.new_page(viewport={"width": 1500, "height": 1000})
    print(f'{"variante":8} {"tela":10} {"capa%":>6} {"fonte":>7} {"corte corpo":>12} {"corte disco":>12}')
    print("-" * 62)
    for v in VAR:
        for it, tela in enumerate(["notebook", "dele"]):
            pag.goto(f"{ARQ}?variant={v}", wait_until="load")
            pag.wait_for_timeout(250)
            pag.select_option("#tela", str(it))
            pag.wait_for_timeout(1200)
            d = pag.evaluate("""() => {
                const c = document.querySelector('.corpo');
                const cap = c.querySelector('img.capa');
                return {pct: Math.round(100*(cap?cap.clientHeight:0)/c.clientHeight),
                        fs: getComputedStyle(c).getPropertyValue('--fs').trim(),
                        corpo: Math.max(c.scrollWidth-c.clientWidth, c.scrollHeight-c.clientHeight),
                        disco: [...c.querySelectorAll('.disco')].reduce(
                            (t,el)=>t+Math.max(0, el.scrollHeight-el.clientHeight), 0)};
            }""")
            pag.locator(".folha").screenshot(path=str(SAIDA / f"album-{v}-{tela}.png"))
            print(f'{v:8} {tela:10} {d["pct"]:5}% {d["fs"]:>7} {d["corpo"]:11}px {d["disco"]:11}px')
    nav.close()
