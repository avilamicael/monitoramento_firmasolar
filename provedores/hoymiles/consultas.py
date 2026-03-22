"""
Consultas à API Hoymiles S-Cloud.

Todas as funções recebem a sessão já autenticada (com token no header).
"""
import json
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed

import requests

from provedores.excecoes import ProvedorErro, ProvedorErroAuth, ProvedorErroRateLimit

logger = logging.getLogger(__name__)

BASE_URL = 'https://neapi.hoymiles.com'


def _post(path: str, body: dict, sessao: requests.Session, token: str) -> dict:
    """Executa uma requisição POST autenticada."""
    try:
        resp = sessao.post(
            f'{BASE_URL}/{path.lstrip("/")}',
            data=json.dumps(body, ensure_ascii=False),
            headers={'authorization': token},
            timeout=20,
        )
    except requests.RequestException as exc:
        raise ProvedorErro(f'Hoymiles: erro de rede em {path}: {exc}') from exc

    if resp.status_code == 429:
        raise ProvedorErroRateLimit('Hoymiles: rate limit atingido (429)')
    if resp.status_code == 401:
        raise ProvedorErroAuth('Hoymiles: token inválido (401)')

    try:
        dados = resp.json()
    except Exception as exc:
        raise ProvedorErro(f'Hoymiles: resposta inválida de {path}: {resp.text[:200]}') from exc

    status = str(dados.get('status', ''))
    if status not in ('0', '200', ''):
        msg = dados.get('message') or str(dados)
        if 'auth' in msg.lower() or 'token' in msg.lower() or status in ('401', '403'):
            raise ProvedorErroAuth(f'Hoymiles: erro de autenticação — {msg}')
        raise ProvedorErro(f'Hoymiles: erro da API em {path} — {msg}')

    return dados


def _buscar_realtime_usina(id_usina: str, sessao: requests.Session, token: str) -> dict:
    """Busca dados em tempo real de uma usina. Projetado para execução paralela."""
    try:
        dados = _post('/pvm-data/api/0/station/data/count_station_real_data',
                      {'sid': id_usina}, sessao, token)
        return dados.get('data') or {}
    except ProvedorErro:
        return {}


def listar_usinas(sessao: requests.Session, token: str) -> list[dict]:
    """
    Retorna todas as usinas com dados em tempo real.

    Fluxo:
        1. Busca lista paginada de usinas
        2. Para cada usina, busca dados realtime em paralelo (ThreadPoolExecutor)
        3. Combina os dados e retorna
    """
    # Etapa 1: lista paginada
    todas_usinas = []
    pagina = 1
    while True:
        dados = _post('/pvm/api/0/station/select_by_page',
                      {'page': pagina, 'page_size': 100}, sessao, token)
        usinas = (dados.get('data') or {}).get('list') or []
        todas_usinas.extend(usinas)
        if len(usinas) < 100:
            break
        pagina += 1

    if not todas_usinas:
        return []

    # Etapa 2: realtime em paralelo (max 5 threads = rate limit Hoymiles)
    ids = [str(u.get('id', '')) for u in todas_usinas]
    realtime_por_id: dict[str, dict] = {}

    with ThreadPoolExecutor(max_workers=5) as executor:
        futuras = {executor.submit(_buscar_realtime_usina, sid, sessao, token): sid for sid in ids}
        for futura in as_completed(futuras):
            sid = futuras[futura]
            try:
                realtime_por_id[sid] = futura.result()
            except Exception:
                realtime_por_id[sid] = {}

    # Etapa 3: combina dados
    return [
        {**u, '_realtime': realtime_por_id.get(str(u.get('id', '')), {})}
        for u in todas_usinas
    ]


def listar_inversores(id_usina: str, sessao: requests.Session, token: str) -> list[dict]:
    """
    Retorna os dispositivos de uma usina em estrutura de árvore.
    Apenas type=2 (Inversor) e type=3 (Microinversor) são coletados.
    """
    dados = _post('/pvm/api/0/station/select_device_of_tree',
                  {'id': id_usina}, sessao, token)
    dispositivos = dados.get('data') or []

    resultado = []

    def _percorrer(itens):
        for item in itens:
            tipo = item.get('type')
            if tipo in (2, 3):
                resultado.append(item)
            filhos = item.get('children') or []
            if filhos:
                _percorrer(filhos)

    _percorrer(dispositivos)
    return resultado


def listar_alertas(sessao: requests.Session, token: str) -> list[dict]:
    """
    Retorna todas as usinas com seus flags de alerta (warn_data).
    O endpoint não filtra por usina — retorna conta inteira.
    """
    todos = []
    pagina = 1
    while True:
        dados = _post('/monitor/api/0/ng/station/flsw',
                      {'page': pagina, 'page_size': 100}, sessao, token)
        pagina_dados = dados.get('data') or {}
        registros = pagina_dados.get('list') or []
        todos.extend(registros)
        total = pagina_dados.get('total', 0)
        if len(todos) >= total or not registros:
            break
        pagina += 1

    return todos
