import threading
import time
import random
import json
from http.server import BaseHTTPRequestHandler, HTTPServer

def tempo_de_checkout():
    r = random.uniform(0.1, 0.2)
    if random.random() > 0.7:
        r += 0.3
    return r


def tempo_de_api():
    r = random.uniform(0.03, 0.08)
    if random.random() > 0.7:
        r += 0.01
    return r

class Produto:
    def __init__(self, nome, estoque_inicial):
        self.nome = nome
        self.quantidade_estoque = estoque_inicial

def processar_checkout(cliente_id, produto, inicio_simulacao=None, logs=None, clientes=None):
    cliente_key = str(cliente_id)
    visual_ativo = inicio_simulacao is not None and logs is not None and clientes is not None

    def tempo_atual():
        return round(time.perf_counter() - inicio_simulacao, 3)

    def registrar(msg, etapa=None):
        if visual_ativo:
            tempo = tempo_atual()
            texto = f"[{tempo:.3f}s] Cliente {cliente_id}: {msg}"
            logs.append(texto)
            if etapa is not None:
                clientes[cliente_key]["etapas"].append({"etapa": etapa, "tempo_s": tempo})
        else:
            texto = f"Cliente {cliente_id}: {msg}"

        print(texto)

    registrar("pagou", "pagou")
    if visual_ativo:
        clientes[cliente_key]["visual"]["fez_pedido_s"] = tempo_atual()

    atraso_api = tempo_de_api()
    registrar(f"aguardando API ({atraso_api:.3f}s)", f"aguardando API ({atraso_api:.3f}s)")
    time.sleep(atraso_api)

    registrar(f"verificando estoque para {produto.nome}", f"verificando estoque para {produto.nome}")

    if produto.quantidade_estoque > 0:
        r = tempo_de_checkout()
        if visual_ativo:
            clientes[cliente_key]["tempo_processamento_s"] = round(r, 3)
            clientes[cliente_key]["visual"]["processando_s"] = tempo_atual()

        registrar("processando pagamento", "processando pagamento")
        time.sleep(r)

        registrar("processado", "processado")
        produto.quantidade_estoque -= 1
        registrar("compra concluida", "compra concluida")

        if visual_ativo:
            clientes[cliente_key]["visual"]["final_s"] = tempo_atual()
            clientes[cliente_key]["visual"]["estado_final"] = "Completo"
            clientes[cliente_key]["saldo_apos_cliente"] = produto.quantidade_estoque
    else:
        if visual_ativo:
            clientes[cliente_key]["tempo_processamento_s"] = 0.0
            clientes[cliente_key]["visual"]["processando_s"] = tempo_atual()

        registrar("falha na compra (produto esgotado)", "falha na compra (produto esgotado)")

        if visual_ativo:
            clientes[cliente_key]["visual"]["final_s"] = tempo_atual()
            clientes[cliente_key]["visual"]["estado_final"] = "Falhou"
            clientes[cliente_key]["saldo_apos_cliente"] = produto.quantidade_estoque

def simular_sistema():
    notebook = Produto(nome="Notebook Gamer", estoque_inicial=1)

    thread_cliente_1 = threading.Thread(target=processar_checkout, args=(1, notebook))
    thread_cliente_2 = threading.Thread(target=processar_checkout, args=(2, notebook))
    
    print(f"Estoque inicial: {notebook.quantidade_estoque}\n")

    thread_cliente_1.start()
    thread_cliente_2.start()

    thread_cliente_1.join()
    thread_cliente_2.join()

    print(f"\nEstoque final: {notebook.quantidade_estoque}")
    if notebook.quantidade_estoque < 0:
        print("ERRO: O estoque está negativo! A race condition foi bem-sucedida.")


def simular_sistema_com_resultado():
    notebook = Produto(nome="Notebook Gamer", estoque_inicial=1)
    logs = []

    inicio_simulacao = time.perf_counter()

    clientes = {
        "1": {
            "nome": "Cliente 1",
            "tempo_processamento_s": None,
            "saldo_apos_cliente": None,
            "etapas": [],
            "visual": {
                "fez_pedido_s": None,
                "processando_s": None,
                "final_s": None,
                "estado_final": None,
            },
        },
        "2": {
            "nome": "Cliente 2",
            "tempo_processamento_s": None,
            "saldo_apos_cliente": None,
            "etapas": [],
            "visual": {
                "fez_pedido_s": None,
                "processando_s": None,
                "final_s": None,
                "estado_final": None,
            },
        },
    }

    logs.append(f"[0.000s] Estoque inicial: {notebook.quantidade_estoque}")

    thread_cliente_1 = threading.Thread(
        target=processar_checkout,
        args=(1, notebook, inicio_simulacao, logs, clientes),
    )
    thread_cliente_2 = threading.Thread(
        target=processar_checkout,
        args=(2, notebook, inicio_simulacao, logs, clientes),
    )

    thread_cliente_1.start()
    thread_cliente_2.start()

    thread_cliente_1.join()
    thread_cliente_2.join()

    tempo_total = round(time.perf_counter() - inicio_simulacao, 3)
    logs.append(f"[{tempo_total:.3f}s] Estoque final: {notebook.quantidade_estoque}")
    erro_race_condition = notebook.quantidade_estoque < 0
    if erro_race_condition:
        logs.append("ERRO: O estoque esta negativo! A race condition foi bem-sucedida.")

    return {
        "estoque_inicial": 1,
        "estoque_final": notebook.quantidade_estoque,
        "race_condition": erro_race_condition,
        "tempo_total_s": tempo_total,
        "clientes": clientes,
        "logs": logs,
    }


class SimulacaoAPIHandler(BaseHTTPRequestHandler):
    def _enviar_json(self, status_code, payload):
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status_code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_POST(self):
        if self.path != "/api/simular":
            self._enviar_json(404, {"erro": "Rota nao encontrada"})
            return

        resultado = simular_sistema_com_resultado()
        self._enviar_json(200, resultado)


def iniciar_api(host="127.0.0.1", porta=8000):
    servidor = HTTPServer((host, porta), SimulacaoAPIHandler)
    print(f"API iniciada em http://{host}:{porta}")
    print("Endpoint: POST /api/simular")
    servidor.serve_forever()

if __name__ == "__main__":
    iniciar_api()