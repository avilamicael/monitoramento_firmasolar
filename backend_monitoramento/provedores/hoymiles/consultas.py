"""
Consultas à API Hoymiles S-Cloud.

Todas as funções recebem a sessão já autenticada (com token no header).
"""
import json
import logging
import struct
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date as date_type

import requests

from provedores.excecoes import ProvedorErro, ProvedorErroAuth, ProvedorErroRateLimit

logger = logging.getLogger(__name__)

BASE_URL = 'https://neapi.hoymiles.com'


def _post(path: str, body: dict, sessao: requests.Session, token: str) -> dict:
    """Executa uma requisição POST autenticada."""
    import time
    inicio = time.time()
    try:
        resp = sessao.post(
            f'{BASE_URL}/{path.lstrip("/")}',
            data=json.dumps(body, ensure_ascii=False),
            headers={'authorization': token},
            timeout=20,
        )
    except requests.RequestException as exc:
        logger.warning('Hoymiles: erro de rede em %s — %s', path, exc)
        raise ProvedorErro(f'Hoymiles: erro de rede em {path}: {exc}') from exc

    duracao_ms = int((time.time() - inicio) * 1000)

    if resp.status_code == 429:
        logger.warning('Hoymiles: rate limit (429) em %s', path)
        raise ProvedorErroRateLimit('Hoymiles: rate limit atingido (429)')
    if resp.status_code == 401:
        logger.error('Hoymiles: token inválido (401) em %s', path)
        raise ProvedorErroAuth('Hoymiles: token inválido (401)')

    try:
        dados = resp.json()
    except Exception as exc:
        logger.error('Hoymiles: resposta inválida de %s — %s', path, resp.text[:200])
        raise ProvedorErro(f'Hoymiles: resposta inválida de {path}: {resp.text[:200]}') from exc

    status = str(dados.get('status', ''))
    if status not in ('0', '200', ''):
        msg = dados.get('message') or str(dados)
        if 'auth' in msg.lower() or 'token' in msg.lower() or status in ('401', '403'):
            logger.error('Hoymiles: erro de autenticação em %s — %s', path, msg)
            raise ProvedorErroAuth(f'Hoymiles: erro de autenticação — {msg}')
        logger.warning('Hoymiles: erro da API em %s — %s', path, msg)
        raise ProvedorErro(f'Hoymiles: erro da API em {path} — {msg}')

    logger.debug('Hoymiles: POST %s → HTTP %d em %dms', path, resp.status_code, duracao_ms)
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


# ── Decoder protobuf para dados elétricos por inversor ────────────────────────

# Mapeamento: field_num → chave no resultado para dados CA (packed float arrays)
_CAMPOS_CA_PROTOBUF = {5: 'frequencia_hz', 6: 'temperatura_c', 7: 'tensao_ca_v'}


def _decodificar_packed_floats(data: bytes) -> list[float]:
    """Decodifica um array packed de floats little-endian de 32 bits."""
    n = len(data) // 4
    if n == 0:
        return []
    return list(struct.unpack_from(f'<{n}f', data, 0))


def _ultimo_valor_valido(vals: list[float]) -> float | None:
    """Retorna o último valor não-zero e finito de uma lista, ou None."""
    for v in reversed(vals):
        if v and v == v and abs(v) < 1e9:  # descarta zero, NaN e infinito
            return round(v, 3)
    return None


def _ler_varint(data: bytes, pos: int) -> tuple[int, int]:
    result, shift = 0, 0
    while pos < len(data):
        b = data[pos]; pos += 1
        result |= (b & 0x7F) << shift
        if not (b & 0x80):
            break
        shift += 7
    return result, pos


def _decodificar_blob(data: bytes) -> list[tuple]:
    """Decodifica um blob binário protobuf em lista de (field_num, wire_type, valor)."""
    pos = 0
    fields = []
    while pos < len(data):
        try:
            tag, pos = _ler_varint(data, pos)
            fn = tag >> 3
            wt = tag & 0x7
            if wt == 0:
                v, pos = _ler_varint(data, pos)
                fields.append((fn, 'varint', v))
            elif wt == 2:
                length, pos = _ler_varint(data, pos)
                raw = data[pos:pos + length]
                pos += length
                try:
                    fields.append((fn, 'str', raw.decode('utf-8')))
                except Exception:
                    fields.append((fn, 'bytes', raw))
            elif wt == 5:
                v = struct.unpack('<f', data[pos:pos + 4])[0]
                pos += 4
                fields.append((fn, 'f32', v))
            else:
                break
        except Exception:
            break
    return fields


def _decodificar_datapoint(dp_raw: bytes) -> dict:
    """
    Decodifica um datapoint de 22 bytes para campos elétricos.

    Estrutura confirmada com dados reais:
      field 1 (f32)    → tensao_dc_v  (V)
      field 2 (f32)    → corrente_dc_a (A)
      field 3 (f32)    → potencia_dc_w (W)
      field 4 (varint) → energia_hoje_wh (Wh acumulado no dia, crescente)
      field 5 (varint) → status (1=ativo)
    """
    pos = 0
    resultado = {}
    mapa_float = {1: 'tensao_dc_v', 2: 'corrente_dc_a', 3: 'potencia_dc_w'}
    while pos < len(dp_raw):
        try:
            tag = dp_raw[pos]; pos += 1
            fn = tag >> 3
            wt = tag & 7
            if wt == 5:
                val = struct.unpack('<f', dp_raw[pos:pos + 4])[0]
                pos += 4
                if fn in mapa_float:
                    resultado[mapa_float[fn]] = round(val, 3)
            elif wt == 0:
                val, pos = _ler_varint(dp_raw, pos)
                if fn == 4:
                    resultado['energia_hoje_wh'] = val
                elif fn == 5:
                    resultado['status'] = val
            else:
                break
        except Exception:
            break
    return resultado


def parsear_dados_dia(blob: bytes) -> dict[int, dict]:
    """
    Decodifica o binário protobuf de down_module_day_data.

    Retorna dict {micro_id: dados_agregados} onde dados_agregados contém:
      tensao_dc_v     — tensão DC média entre os ports (V)
      corrente_dc_a   — corrente DC total (soma dos ports) (A)
      pac_kw          — potência total (soma dos ports) (kW)
      energia_hoje_kwh— energia do dia (soma dos ports) (kWh)
      strings_mppt    — {port: {tensao, corrente}} por port
    """
    resultado: dict[int, dict] = {}

    top = _decodificar_blob(blob)
    # field 3 (repetido) = bloco por microinversor
    for fn, ft, val in top:
        if fn != 3 or ft != 'bytes':
            continue
        inner = _decodificar_blob(val)
        micro_id = next((v for f, t, v in inner if t == 'varint'), None)
        micro_data_raw = next((v for f, t, v in inner if t == 'bytes'), None)
        if micro_id is None or micro_data_raw is None:
            continue

        inner2 = _decodificar_blob(micro_data_raw)
        times = [v for f, t, v in inner2 if t == 'str' and len(v) == 5 and ':' in v]
        port_blocks = [(f, v) for f, t, v in inner2 if t == 'bytes']

        # Dados CA: packed float arrays nos campos 5 (freq), 6 (temp), 7 (tensão AC)
        dados_ca: dict[str, float | None] = {}
        for fn, ft, val in inner2:
            if ft == 'bytes' and fn in _CAMPOS_CA_PROTOBUF:
                floats = _decodificar_packed_floats(val)
                dados_ca[_CAMPOS_CA_PROTOBUF[fn]] = _ultimo_valor_valido(floats)

        port_data: dict[int, dict] = {}
        for _, pb_val in port_blocks:
            pb_fields = _decodificar_blob(pb_val)
            port_num = next((v for f, t, v in pb_fields if t == 'varint'), None)
            if port_num is None or port_num == 0:
                continue
            dp_bytes_raw = next((v for f, t, v in pb_fields if t == 'bytes'), None)
            if dp_bytes_raw is None:
                continue
            all_dps = _decodificar_blob(dp_bytes_raw)
            dp_list = [v for f, t, v in all_dps if t == 'bytes']
            if not dp_list:
                continue
            # Buscar o último datapoint com dados válidos
            ultimo_dp = None
            for dp_raw in reversed(dp_list):
                dp = _decodificar_datapoint(dp_raw)
                if dp.get('potencia_dc_w', 0) > 0 or dp.get('energia_hoje_wh', 0) > 0:
                    ultimo_dp = dp
                    break
            if ultimo_dp is None and dp_list:
                ultimo_dp = _decodificar_datapoint(dp_list[-1])
            if ultimo_dp:
                port_data[port_num] = ultimo_dp

        if not port_data:
            continue

        tensoes = [p['tensao_dc_v'] for p in port_data.values() if 'tensao_dc_v' in p]
        correntes = [p['corrente_dc_a'] for p in port_data.values() if 'corrente_dc_a' in p]
        potencias = [p['potencia_dc_w'] for p in port_data.values() if 'potencia_dc_w' in p]
        energias = [p['energia_hoje_wh'] for p in port_data.values() if 'energia_hoje_wh' in p]

        resultado[micro_id] = {
            'tensao_dc_v': round(sum(tensoes) / len(tensoes), 2) if tensoes else None,
            'corrente_dc_a': round(sum(correntes), 3) if correntes else None,
            'pac_kw': round(sum(potencias) / 1000, 4) if potencias else None,
            'energia_hoje_kwh': round(sum(energias) / 1000, 4) if energias else None,
            'strings_mppt': {
                str(port): {
                    'tensao': p.get('tensao_dc_v'),
                    'corrente': p.get('corrente_dc_a'),
                }
                for port, p in port_data.items()
            },
            **dados_ca,
        }

    return resultado


def baixar_dados_dia(id_usina: str, sessao: requests.Session, token: str) -> dict[int, dict]:
    """
    Baixa e decodifica os dados elétricos do dia para todos os microinversores
    de uma usina. Retorna dict {micro_id: dados} ou {} em caso de falha.
    """
    hoje = date_type.today().strftime('%Y-%m-%d')
    try:
        resp = sessao.post(
            f'{BASE_URL}/pvm-data/api/0/module/data/down_module_day_data',
            data=json.dumps({'sid': int(id_usina), 'date': hoje}),
            headers={'authorization': token},
            timeout=30,
        )
    except requests.RequestException as exc:
        logger.warning('Hoymiles: erro de rede em down_module_day_data — %s', exc)
        return {}

    if resp.status_code != 200 or not resp.content:
        logger.warning('Hoymiles: down_module_day_data retornou HTTP %d', resp.status_code)
        return {}

    try:
        return parsear_dados_dia(resp.content)
    except Exception as exc:
        logger.warning('Hoymiles: falha ao parsear dados do dia — %s', exc)
        return {}
