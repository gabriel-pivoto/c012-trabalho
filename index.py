import threading
import time
import random
import json
from http.server import BaseHTTPRequestHandler, HTTPServer

ESTOQUE_INICIAL_PADRAO = 1
QUANTIDADE_CLIENTES_PADRAO = 2


def tempo_de_checkout():
    r = random.uniform(0.01, 0.02)
    if random.random() > 0.5:
        r += 0.3
    return r


def tempo_de_api():
    r = random.uniform(0.03, 0.08)
    if random.random() > 0.5:
        r += 0.3
    return r

class Produto:
    def __init__(self, nome, estoque_inicial):
        self.nome = nome
        self.quantidade_estoque = estoque_inicial


def normalizar_quantidade_clientes(valor):
    try:
        quantidade = int(valor)
    except (TypeError, ValueError):
        raise ValueError("quantidade_clientes deve ser um numero inteiro")

    if quantidade < 1:
        raise ValueError("quantidade_clientes deve ser maior que zero")

    return quantidade


def normalizar_estoque_inicial(valor):
    try:
        estoque = int(valor)
    except (TypeError, ValueError):
        raise ValueError("estoque_inicial deve ser um numero inteiro")

    if estoque < 0:
        raise ValueError("estoque_inicial nao pode ser negativo")

    return estoque


def criar_estado_cliente(cliente_id):
    return {
        "nome": f"Cliente {cliente_id}",
        "tempo_processamento_s": None,
        "saldo_apos_cliente": None,
        "etapas": [],
        "visual": {
            "fez_pedido_s": None,
            "processando_s": None,
            "final_s": None,
            "estado_final": None,
        },
    }
def processar_checkout(cliente_id, produto, inicio_simulacao=None, logs=None, clientes=None):
    cliente_key = str(cliente_id)
    visual_ativo = inicio_simulacao is not None and logs is not None and clientes is not None

    def tempo_atual():
        return time.perf_counter() - inicio_simulacao

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
        espera_ate_processamento = r * random.uniform(0.25, 0.75)
        tempo_processando = r - espera_ate_processamento
        if visual_ativo:
            clientes[cliente_key]["tempo_processamento_s"] = r

        time.sleep(espera_ate_processamento)

        if visual_ativo:
            clientes[cliente_key]["visual"]["processando_s"] = tempo_atual()

        registrar("processando pagamento", "processando pagamento")
        time.sleep(tempo_processando)

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

def simular_sistema(
    quantidade_clientes=QUANTIDADE_CLIENTES_PADRAO,
    estoque_inicial=ESTOQUE_INICIAL_PADRAO,
):
    quantidade_clientes = normalizar_quantidade_clientes(quantidade_clientes)
    estoque_inicial = normalizar_estoque_inicial(estoque_inicial)
    notebook = Produto(nome="Notebook Gamer", estoque_inicial=estoque_inicial)
    threads = [
        threading.Thread(target=processar_checkout, args=(cliente_id, notebook))
        for cliente_id in range(1, quantidade_clientes + 1)
    ]

    print(f"Estoque inicial: {notebook.quantidade_estoque}\n")

    for thread in threads:
        thread.start()

    for thread in threads:
        thread.join()

    print(f"\nEstoque final: {notebook.quantidade_estoque}")
    if notebook.quantidade_estoque < 0:
        print("ERRO: O estoque está negativo! A race condition foi bem-sucedida.")


def simular_sistema_com_resultado(
    quantidade_clientes=QUANTIDADE_CLIENTES_PADRAO,
    estoque_inicial=ESTOQUE_INICIAL_PADRAO,
):
    quantidade_clientes = normalizar_quantidade_clientes(quantidade_clientes)
    estoque_inicial = normalizar_estoque_inicial(estoque_inicial)
    notebook = Produto(nome="Notebook Gamer", estoque_inicial=estoque_inicial)
    logs = []
    inicio_simulacao = time.perf_counter()
    clientes = {
        str(cliente_id): criar_estado_cliente(cliente_id)
        for cliente_id in range(1, quantidade_clientes + 1)
    }
    threads = [
        threading.Thread(
            target=processar_checkout,
            args=(cliente_id, notebook, inicio_simulacao, logs, clientes),
        )
        for cliente_id in range(1, quantidade_clientes + 1)
    ]

    logs.append(f"[0.000s] Estoque inicial: {notebook.quantidade_estoque}")

    for thread in threads:
        thread.start()

    for thread in threads:
        thread.join()

    tempo_total = time.perf_counter() - inicio_simulacao
    logs.append(f"[{tempo_total:.3f}s] Estoque final: {notebook.quantidade_estoque}")
    erro_race_condition = notebook.quantidade_estoque < 0
    if erro_race_condition:
        logs.append("ERRO: O estoque esta negativo! A race condition foi bem-sucedida.")

    return {
        "quantidade_clientes": quantidade_clientes,
        "estoque_inicial": estoque_inicial,
        "estoque_final": notebook.quantidade_estoque,
        "race_condition": erro_race_condition,
        "tempo_total_s": tempo_total,
        "clientes": clientes,
        "logs": logs,
    }


class SimulacaoAPIHandler(BaseHTTPRequestHandler):
    def _ler_payload_json(self):
        content_length = int(self.headers.get("Content-Length", "0") or 0)
        if content_length <= 0:
            return {}

        raw_body = self.rfile.read(content_length)
        if not raw_body:
            return {}

        try:
            return json.loads(raw_body.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            raise ValueError("JSON invalido")

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

        try:
            payload = self._ler_payload_json()
            quantidade_clientes = normalizar_quantidade_clientes(
                payload.get("quantidade_clientes", QUANTIDADE_CLIENTES_PADRAO)
            )
            estoque_inicial = normalizar_estoque_inicial(
                payload.get("estoque_inicial", ESTOQUE_INICIAL_PADRAO)
            )
        except ValueError as exc:
            self._enviar_json(400, {"erro": str(exc)})
            return

        resultado = simular_sistema_com_resultado(
            quantidade_clientes=quantidade_clientes,
            estoque_inicial=estoque_inicial,
        )
        self._enviar_json(200, resultado)


def iniciar_api(host="127.0.0.1", porta=8000):
    servidor = HTTPServer((host, porta), SimulacaoAPIHandler)
    print(f"API iniciada em http://{host}:{porta}")
    print("Endpoint: POST /api/simular")
    print(
        "Payload opcional: "
        f"{{\"quantidade_clientes\": {QUANTIDADE_CLIENTES_PADRAO}, "
        f"\"estoque_inicial\": {ESTOQUE_INICIAL_PADRAO}}}"
    )
    servidor.serve_forever()

if __name__ == "__main__":
    iniciar_api()
