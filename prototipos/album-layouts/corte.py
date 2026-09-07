from playwright.sync_api import sync_playwright
import pathlib

ARQ = pathlib.Path("/mnt/c/Users/flavi/Downloads/album-layouts-prototipo.html").as_uri()

with sync_playwright() as p:
    nav = p.chromium.launch()
    pag = nav.new_page(viewport={"width": 1500, "height": 1000})
    print(f'{"variante":10} {"tela":10} {"corte no corpo":>15} {"corte dentro dos discos":>25}')
    print("-" * 66)
    for v in ["atual", "A", "B", "C", "D"]:
        for it, tela in enumerate(["notebook", "dele"]):
            pag.goto(f"{ARQ}?variant={v}", wait_until="load")
            pag.wait_for_timeout(250)
            pag.select_option("#tela", str(it))
            pag.wait_for_timeout(700)
            d = pag.evaluate("""() => {
                const c = document.querySelector('.corpo');
                const cortes = [...c.querySelectorAll('.disco')].map(
                    el => Math.max(0, el.scrollHeight - el.clientHeight));
                return {corpo: c.scrollWidth - c.clientWidth, cortes};
            }""")
            perdido = sum(d["cortes"])
            print(f'{v:10} {tela:10} {d["corpo"]:14}px  {str(d["cortes"]):>25}'
                  + ("   <-- TEXTO PERDIDO" if perdido else ""))
    nav.close()
