"""O registro do peso indo do navegador até o Worker, sem recarregar a folha.

Aqui um servidor local finge ser o Worker com o mesmo contrato do worker/index.js —
o que se prova é o lado do navegador: token guardado, corpo enviado, confirmação na folha
e o que acontece quando o token é recusado.
"""

import json
import threading
from datetime import date
from http.server import BaseHTTPRequestHandler, HTTPServer

import pytest

from planner import render
from planner.topicos import peso

TOKEN = "token-de-teste"


class _Worker(BaseHTTPRequestHandler):
    recebidos: list = []
    recusar = False

    def _cors(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Headers", "Content-Type,Authorization")
        self.send_header("Access-Control-Allow-Methods", "GET,POST,OPTIONS")

    def do_OPTIONS(self):
        self.send_response(204)
        self._cors()
        self.end_headers()

    def do_POST(self):
        autorizacao = self.headers.get("Authorization", "")
        if type(self).recusar or autorizacao != f"Bearer {TOKEN}":
            self.send_response(401)
            self._cors()
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(b'{"erro":"token invalido"}')
            return
        corpo = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        type(self).recebidos.append(corpo)
        self.send_response(200)
        self._cors()
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(b'{"ok":true}')

    def log_message(self, *_):
        pass


@pytest.fixture
def worker():
    _Worker.recebidos, _Worker.recusar = [], False
    servidor = HTTPServer(("127.0.0.1", 0), _Worker)
    threading.Thread(target=servidor.serve_forever, daemon=True).start()
    yield servidor, f"http://127.0.0.1:{servidor.server_port}"
    servidor.shutdown()


@pytest.fixture
def folha(tmp_path, worker, monkeypatch):
    """A edição publicada, servida por http, apontando para o Worker de teste."""
    _, url = worker
    monkeypatch.setenv("WORKER_URL", url)
    dia = date(2026, 8, 19)
    topicos = [{"id": "peso", "nome": "Peso", "chapeu": "Sua curva",
                "blocos": peso.blocos(dia, [("2026-08-18", 78.9)]), "falhou": False}]
    destino = tmp_path / "index.html"
    destino.write_text(render.montar(dia, topicos), encoding="utf-8")

    from http.server import SimpleHTTPRequestHandler
    from functools import partial
    sítio = HTTPServer(("127.0.0.1", 0),
                       partial(SimpleHTTPRequestHandler, directory=str(tmp_path)))
    sítio.RequestHandlerClass.log_message = lambda *_: None
    threading.Thread(target=sítio.serve_forever, daemon=True).start()
    yield f"http://127.0.0.1:{sítio.server_port}/index.html"
    sítio.shutdown()


def _abrir(pagina, endereco, token=TOKEN):
    pagina.goto(endereco)
    if token:
        pagina.evaluate("t => localStorage.setItem('diario.token', t)", token)
    pagina.wait_for_selector("#peso-gravar")


@pytest.fixture
def pagina():
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        navegador = p.chromium.launch()
        pg = navegador.new_page(viewport={"width": 1440, "height": 900})
        yield pg
        navegador.close()


def test_o_peso_chega_ao_worker_e_a_folha_confirma(folha, pagina, worker):
    _abrir(pagina, folha)
    pagina.fill("#peso-valor", "78,1")
    pagina.click("#peso-gravar")
    pagina.wait_for_function("() => document.getElementById('peso-aviso').textContent.includes('gravado')")

    assert _Worker.recebidos == [{"secao": "peso", "chave": "2026-08-19", "valor": 78.1}]
    aviso = pagina.text_content("#peso-aviso")
    assert "78.1 kg gravado" in aviso
    assert "amanhã" in aviso, "a folha precisa dizer que a curva só muda amanhã"
    assert pagina.input_value("#peso-valor") == ""


def test_virgula_e_ponto_valem_a_mesma_coisa(folha, pagina):
    _abrir(pagina, folha)
    pagina.fill("#peso-valor", "77.9")
    pagina.click("#peso-gravar")
    pagina.wait_for_function("() => document.getElementById('peso-aviso').textContent.includes('gravado')")
    assert _Worker.recebidos[0]["valor"] == 77.9


def test_peso_absurdo_nem_sai_do_navegador(folha, pagina):
    _abrir(pagina, folha)
    for valor in ("0", "-3", "900", "abc"):
        pagina.fill("#peso-valor", valor)
        pagina.click("#peso-gravar")
        pagina.wait_for_function("() => document.getElementById('peso-aviso').textContent.includes('inválido')")
    assert _Worker.recebidos == []


def test_token_recusado_e_esquecido_para_ele_digitar_outro(folha, pagina):
    _Worker.recusar = True
    _abrir(pagina, folha, token="token-errado")
    pagina.fill("#peso-valor", "78,1")
    pagina.click("#peso-gravar")
    pagina.wait_for_function("() => document.getElementById('peso-aviso').textContent.includes('recusado')")
    assert pagina.evaluate("() => localStorage.getItem('diario.token')") is None


def test_o_html_publicado_nao_carrega_o_token(folha, pagina):
    _abrir(pagina, folha, token=None)
    conteudo = pagina.content()
    assert TOKEN not in conteudo
