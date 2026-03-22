---
title: Módulo — Provedores
tipo: modulo
tags: [provedores, credenciais, criptografia, adaptadores]
---

# Módulo: Provedores

Gerencia credenciais, criptografia, adaptadores e rate limiting dos provedores de dados.

**Arquivos:**
- `provedores/models.py`
- `provedores/base.py`
- `provedores/cripto.py`
- `provedores/registro.py`
- `provedores/limitador.py`
- `provedores/excecoes.py`
- `provedores/fusionsolar/`
- `provedores/hoymiles/`
- `provedores/solis/`

---

## Models

### CredencialProvedor

```python
class CredencialProvedor:
    id              : UUIDField (PK)
    provedor        : 'solis' | 'hoymiles' | 'fusionsolar' | 'solarman'  (unique)
    credenciais_enc : TextField (JSON criptografado com Fernet)
    ativo           : BooleanField
    precisa_atencao : BooleanField (marcado em falha de autenticação)
    criado_em       : DateTimeField
    atualizado_em   : DateTimeField
```

### CacheTokenProvedor

```python
class CacheTokenProvedor:
    credencial      : OneToOneField → CredencialProvedor
    dados_token_enc : TextField (JSON criptografado)
    expira_em       : DateTimeField (null)
    atualizado_em   : DateTimeField
```

Usado por provedores com sessão (Hoymiles, FusionSolar) para evitar re-login a cada coleta.

---

## Criptografia (cripto.py)

```python
from cryptography.fernet import Fernet

def criptografar_credenciais(dados: dict) -> str:
    chave = settings.CHAVE_CRIPTOGRAFIA
    f = Fernet(chave.encode())
    return f.encrypt(json.dumps(dados).encode()).decode()

def descriptografar_credenciais(dados_enc: str) -> dict:
    chave = settings.CHAVE_CRIPTOGRAFIA
    f = Fernet(chave.encode())
    return json.loads(f.decrypt(dados_enc.encode()))
```

A `CHAVE_CRIPTOGRAFIA` fica **exclusivamente** no `.env`, nunca no repositório. Se perdida, as credenciais armazenadas se tornam ilegíveis.

**Gerar nova chave:**
```bash
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

---

## Interface AdaptadorProvedor (base.py)

Contrato que todo adaptador deve implementar:

```python
class AdaptadorProvedor(ABC):

    @property
    @abstractmethod
    def chave_provedor(self) -> str:
        """'solis', 'hoymiles' ou 'fusionsolar'"""

    @property
    @abstractmethod
    def capacidades(self) -> CapacidadesProvedor:
        """Rate limits, suporte a inversores/alertas, intervalo mínimo"""

    @abstractmethod
    def buscar_usinas(self) -> list[DadosUsina]: ...

    @abstractmethod
    def buscar_inversores(self, id_usina_provedor: str) -> list[DadosInversor]: ...

    @abstractmethod
    def buscar_alertas(self, id_usina_provedor: str | None = None) -> list[DadosAlerta]: ...

    # Opcionais (provedores com sessão):
    def precisa_renovar_token(self) -> bool: return False
    def renovar_token(self, dados_token: dict) -> dict: return dados_token
    def obter_cache_token(self) -> dict | None: return None
```

### CapacidadesProvedor

```python
@dataclass
class CapacidadesProvedor:
    suporta_inversores            : bool = True
    suporta_alertas               : bool = True
    alertas_por_conta             : bool = True   # True = uma chamada p/ toda conta
    limite_requisicoes            : int = 5
    janela_segundos               : int = 10
    min_intervalo_coleta_segundos : int = 0       # 0 = sem restrição
```

### Dataclasses de Dados

```python
@dataclass
class DadosUsina:
    id_usina_provedor, nome, capacidade_kwp
    potencia_atual_kw, energia_hoje_kwh, energia_mes_kwh, energia_total_kwh
    status, data_medicao, fuso_horario, endereco
    qtd_inversores, qtd_inversores_online, qtd_alertas
    payload_bruto: dict

@dataclass
class DadosInversor:
    id_inversor_provedor, id_usina_provedor
    numero_serie, modelo, estado
    pac_kw, energia_hoje_kwh, energia_total_kwh
    data_medicao
    soc_bateria: float | None    # baterias
    strings_mppt: dict           # {'mppt_1_cap': 120.5, ...}
    payload_bruto: dict

@dataclass
class DadosAlerta:
    id_alerta_provedor, id_usina_provedor
    mensagem, nivel, inicio
    equipamento_sn, estado, sugestao
    id_tipo_alarme_provedor      # lookup no CatalogoAlarme
    payload_bruto: dict
```

---

## Registro de Provedores (registro.py)

Factory que retorna o adaptador correto:

```python
REGISTRO = {
    'solis':       SolisAdaptador,
    'hoymiles':    HoymilesAdaptador,
    'fusionsolar': FusionSolarAdaptador,
}

def get_adaptador(chave_provedor: str, credenciais: dict) -> AdaptadorProvedor:
    classe = REGISTRO[chave_provedor]
    return classe(credenciais)
```

Para adicionar um novo provedor: criar o adaptador, registrar no `REGISTRO`.

---

## Rate Limiting (limitador.py)

Limita requisições por provedor de forma distribuída (Redis), compartilhada entre workers.

```python
LIMITES = {
    'solis':       (3, 5),    # 3 req / 5s
    'hoymiles':    (5, 10),   # 5 req / 10s
    'fusionsolar': (1, 5),    # 1 req / 5s
    'solarman':    (10, 60),  # 10 req / 60s
}

# Uso:
with LimitadorRequisicoes('solis'):
    resposta = requests.post(url, ...)
```

---

## Exceções (excecoes.py)

```python
class ProvedorErro(Exception):
    """Erro genérico de API (rede, resposta inválida)"""

class ProvedorErroAuth(ProvedorErro):
    """Credenciais inválidas — sem retry, marca precisa_atencao"""

class ProvedorErroRateLimit(ProvedorErro):
    """Rate limit atingido — retry com backoff exponencial"""
```

---

## Management Command: fusionsolar_credenciais

```bash
# Atualizar credenciais FusionSolar
python manage.py fusionsolar_credenciais \
    --usuario api_firmasolar \
    --system-code "senha" \
    --testar

# Ver credenciais atuais (mascaradas)
python manage.py fusionsolar_credenciais --mostrar
```

Para outros provedores, use o shell Django. Ver [[operacional/credenciais]].

---

## Veja Também

- [[provedores/fusionsolar]]
- [[provedores/hoymiles]]
- [[provedores/solis]]
- [[operacional/credenciais]]
