"""
Limitador de requisições por provedor.

Usa Redis como estado compartilhado entre workers Celery para garantir
que múltiplos workers não ultrapassem o rate limit de cada provedor.
"""
import time
import redis
from django.conf import settings

# Máximo de requisições permitidas por janela (em segundos)
LIMITES: dict[str, tuple[int, int]] = {
    'solis':       (3, 5),    # 3 req / 5s (documentado pela Solis)
    'hoymiles':    (5, 10),   # 5 req / 10s
    'fusionsolar': (1, 5),    # 1 req / 5s — limite estrito por endpoint
    'solarman':    (10, 60),  # 10 req / 60s
}

_cliente_redis = None


def _get_redis():
    global _cliente_redis
    if _cliente_redis is None:
        _cliente_redis = redis.from_url(settings.REDIS_URL, decode_responses=True)
    return _cliente_redis


class LimitadorRequisicoes:
    """
    Context manager que controla o ritmo de chamadas por provedor.

    Uso:
        with LimitadorRequisicoes('solis'):
            resposta = requests.post(url, ...)
    """

    def __init__(self, provedor: str):
        self.provedor = provedor
        self.max_requisicoes, self.janela = LIMITES.get(provedor, (5, 10))

    def __enter__(self):
        r = _get_redis()
        chave = f'limitador:{self.provedor}'
        pipe = r.pipeline()
        pipe.incr(chave)
        pipe.expire(chave, self.janela)
        contagem, _ = pipe.execute()

        if contagem > self.max_requisicoes:
            ttl = r.ttl(chave)
            time.sleep(max(0, ttl) + 0.1)
        return self

    def __exit__(self, *args):
        pass
