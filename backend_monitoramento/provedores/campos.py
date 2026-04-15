"""
Metadados de campos por provedor.

Fonte única da verdade — usado tanto pelo admin Django quanto pela API REST.
Cada entrada define os campos que o operador precisa preencher para
autenticar no provedor e quais campos são sensíveis (devem ser tratados
como senha).

Formato de cada item em 'campos':
    (chave_interna, label_humano, tipo)
        tipo = 'texto' ou 'senha'

Quando adicionar um novo provedor:
  1. Inclua a tupla correspondente aqui.
  2. Registre o adaptador em provedores/registro.py.
  3. O frontend recebe esta estrutura via /api/provedores/meta/ e renderiza
     o form dinamicamente — não precisa alterar o frontend.
"""

CAMPOS_POR_PROVEDOR: dict[str, list[tuple[str, str, str]]] = {
    'solis':       [('api_key', 'API Key', 'texto'), ('app_secret', 'App Secret', 'senha')],
    'hoymiles':    [('username', 'Usuário / Email', 'texto'), ('password', 'Senha', 'senha')],
    'fusionsolar': [('username', 'Usuário', 'texto'), ('system_code', 'System Code', 'senha')],
    'solarman':    [('email', 'Email', 'texto'), ('password', 'Senha', 'senha')],
    'auxsol':      [('account', 'Usuário / Email', 'texto'), ('password', 'Senha', 'senha')],
}

# Provedores que usam token JWT inserido manualmente pelo operador
PROVEDORES_TOKEN_MANUAL: set[str] = {'solarman'}

# Intervalo mínimo de coleta aceito (em minutos)
INTERVALO_MINIMO_MINUTOS = 30
