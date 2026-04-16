---
title: Módulo — Provedores
tipo: modulo
tags: [provedores, credenciais, criptografia, adaptadores]
updated: 2026-04-15
---

# Módulo: Provedores

Gerencia credenciais, criptografia, adaptadores e rate limiting dos provedores de dados. Expõe CRUD completo via API REST e metadados dinâmicos para forms do frontend.

**Arquivos:**
- `provedores/models.py` — `CredencialProvedor`, `CacheTokenProvedor`
- `provedores/base.py` — Interface `AdaptadorProvedor` + dataclasses
- `provedores/cripto.py` — Fernet
- `provedores/registro.py` — Factory
- `provedores/limitador.py` — Rate limit distribuído via Redis
- `provedores/excecoes.py` — `ProvedorErro`, `ProvedorErroAuth`, `ProvedorErroRateLimit`
- `provedores/campos.py` — **Fonte única** de metadados por provedor
- `provedores/fusionsolar/`, `provedores/hoymiles/`, `provedores/solis/`, `provedores/solarman/`, `provedores/auxsol/`

---

## Models

### CredencialProvedor

```python
class CredencialProvedor:
    PROVEDORES = [
        ('solis',       'Solis Cloud'),
        ('hoymiles',    'Hoymiles S-Cloud'),
        ('fusionsolar', 'Huawei FusionSolar'),
        ('solarman',    'Solarman Pro'),
        ('auxsol',      'AuxSol Cloud'),
    ]

    id                         : UUIDField (PK)
    provedor                   : CharField (unique)
    credenciais_enc            : TextField (JSON criptografado com Fernet)
    ativo                      : BooleanField
    precisa_atencao            : BooleanField  # marcado em falha de auth
    intervalo_coleta_minutos   : PositiveIntegerField (default 30, min 30)
    criado_em, atualizado_em   : DateTimeField
```

### CacheTokenProvedor

Armazena o token de sessão dos provedores stateful (Hoymiles, FusionSolar, AuxSol). `OneToOneField` para a credencial. Dados criptografados com Fernet.

---

## Criptografia (cripto.py)

```python
def criptografar_credenciais(dados: dict) -> str
def descriptografar_credenciais(dados_enc: str) -> dict
```

Fernet (AES-128 + HMAC-SHA256). A `CHAVE_CRIPTOGRAFIA` fica **exclusivamente** no `.env`. Ver [[arquitetura/decisoes#ADR-003]].

**Gerar nova chave:**
```bash
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

---

## Metadados por provedor (campos.py)

**Fonte única da verdade** — usado tanto pelo admin Django quanto pela API REST para montar forms dinâmicos no frontend.

```python
CAMPOS_POR_PROVEDOR: dict[str, list[tuple[str, str, str]]] = {
    'solis':       [('api_key', 'API Key', 'texto'), ('app_secret', 'App Secret', 'senha')],
    'hoymiles':    [('username', 'Usuário / Email', 'texto'), ('password', 'Senha', 'senha')],
    'fusionsolar': [('username', 'Usuário', 'texto'), ('system_code', 'System Code', 'senha')],
    'solarman':    [('email', 'Email', 'texto'), ('password', 'Senha', 'senha')],
    'auxsol':      [('account', 'Usuário / Email', 'texto'), ('password', 'Senha', 'senha')],
}

PROVEDORES_TOKEN_MANUAL: set[str] = {'solarman'}  # JWT inserido manualmente
INTERVALO_MINIMO_MINUTOS = 30
```

Ao adicionar um provedor novo:
1. Incluir tupla em `CAMPOS_POR_PROVEDOR`.
2. Registrar adaptador em `provedores/registro.py`.
3. Adicionar à lista `PROVEDORES` do modelo.
4. O frontend **não precisa de alteração** — recebe tudo via `/api/provedores/meta/`.

---

## Endpoints de API (`/api/provedores/`) — staff only

| Método | Path | Descrição |
|---|---|---|
| GET | `/api/provedores/meta/` | Retorna todos os provedores com seus campos e `usa_token_manual`, mais `intervalo_minimo_minutos`. Usado pelo frontend para renderizar forms dinâmicos. |
| GET | `/api/provedores/` | Lista `CredencialProvedor` (credenciais mascaradas). |
| GET | `/api/provedores/{id}/` | Detalhe. |
| POST | `/api/provedores/` | Cria credencial (campos validados por provedor; criptografa antes de salvar). |
| PATCH | `/api/provedores/{id}/` | Atualização parcial. |
| DELETE | `/api/provedores/{id}/` | Remove. |
| POST | `/api/provedores/{id}/forcar-coleta/` | Dispara `coletar_dados_provedor.delay(id)` imediatamente. Retorna 400 se inativa. |

**Frontend:** página `/provedores` (só staff) com lista, botões de ação e form dinâmico por provedor.

Todos os endpoints exigem `is_staff=True` (`IsAdminUser`).

---

## Interface AdaptadorProvedor (base.py)

```python
class AdaptadorProvedor(ABC):
    @property
    @abstractmethod
    def chave_provedor(self) -> str: ...

    @property
    @abstractmethod
    def capacidades(self) -> CapacidadesProvedor: ...

    @abstractmethod
    def buscar_usinas(self) -> list[DadosUsina]: ...

    @abstractmethod
    def buscar_inversores(self, id_usina_provedor: str) -> list[DadosInversor]: ...

    @abstractmethod
    def buscar_alertas(self, id_usina_provedor=None) -> list[DadosAlerta]: ...

    # Opcionais (stateful):
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
    alertas_por_conta             : bool = True
    limite_requisicoes            : int  = 5
    janela_segundos               : int  = 10
    min_intervalo_coleta_segundos : int  = 0
```

### Dataclasses de Dados

`DadosUsina`, `DadosInversor` e `DadosAlerta` (este último contém `estado`, `id_tipo_alarme_provedor` para lookup no catálogo, e o `payload_bruto` completo).

`DadosInversor` inclui agora os campos elétricos usados pela análise interna: `tensao_ac_v`, `corrente_ac_a`, `tensao_dc_v`, `corrente_dc_a`, `frequencia_hz`, `temperatura_c`.

---

## Registro de Provedores (registro.py)

Factory simples:

```python
REGISTRO = {
    'solis':       SolisAdaptador,
    'hoymiles':    HoymilesAdaptador,
    'fusionsolar': FusionSolarAdaptador,
    'solarman':    SolarmanAdaptador,
    'auxsol':      AuxSolAdaptador,
}

def get_adaptador(chave_provedor, credenciais): ...
```

---

## Rate Limiting (limitador.py)

Redis distribuído (janela deslizante). Parâmetros em `CapacidadesProvedor.limite_requisicoes` e `janela_segundos` definidos por adaptador. Tipicamente:

| Provedor | Limite |
|---|---|
| FusionSolar | 1 req / 5s, `min_intervalo_coleta_segundos=900` |
| Hoymiles | 5 req / 10s |
| Solis | 3 req / 5s |
| Solarman | configurável |
| AuxSol | configurável |

Uso:
```python
with LimitadorRequisicoes('solis'):
    resposta = requests.post(url, ...)
```

---

## Exceções

```python
class ProvedorErro(Exception):         """Erro genérico"""
class ProvedorErroAuth(ProvedorErro):  """Credenciais inválidas — sem retry, marca precisa_atencao"""
class ProvedorErroRateLimit(ProvedorErro): """Rate limit — sem retry, aguarda próximo ciclo do Beat"""
```

Ver [[modulos/coleta#Tratamento de erros]].

---

## Management Commands

```bash
# FusionSolar — dedicado
python manage.py fusionsolar_credenciais --usuario U --system-code S --testar
python manage.py fusionsolar_credenciais --mostrar
```

Para outros provedores, usar o frontend (`/provedores`) ou o Django admin.

---

## Veja Também

- [[provedores/fusionsolar]]
- [[provedores/hoymiles]]
- [[provedores/solis]]
- [[operacional/credenciais]]
- [[arquitetura/decisoes]]
