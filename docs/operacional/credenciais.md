---
title: Operacional — Gerenciamento de Credenciais
tipo: operacional
tags: [credenciais, provedores, operacional]
---

# Gerenciamento de Credenciais

---

## Estado Atual dos Provedores

| Provedor | Usuário / Chave | Usinas | Status |
|---|---|---|---|
| FusionSolar | `api_firmasolar` | 50 | ✅ ativo |
| Hoymiles | `firmasolar` | 69 | ✅ ativo |
| Solis | API Key `1300386...` | 12 | ✅ ativo |

---

## FusionSolar — Atualizar Credenciais

Use o management command dedicado:

```bash
# Na VPS
cd ~/monitoramento_firmasolar/backend_monitoramento

# Atualizar e testar imediatamente
sudo docker compose exec web python manage.py fusionsolar_credenciais \
    --usuario api_firmasolar \
    --system-code "nova_senha" \
    --testar

# Ver credenciais atuais (mascaradas)
sudo docker compose exec web python manage.py fusionsolar_credenciais --mostrar
```

O comando:
- Atualiza as credenciais no banco (criptografadas)
- Apaga o cache de token anterior (força novo login)
- Ativa a credencial (`ativo=True`)
- Limpa `precisa_atencao`
- Opcionalmente testa a conexão e lista as usinas

---

## Hoymiles — Atualizar Credenciais

```bash
sudo docker compose exec web python manage.py shell
```

```python
from provedores.cripto import criptografar_credenciais
from provedores.models import CredencialProvedor, CacheTokenProvedor

# Atualizar
cred = CredencialProvedor.objects.get(provedor='hoymiles')
cred.credenciais_enc = criptografar_credenciais({
    'username': 'firmasolar',
    'password': 'nova_senha'
})
cred.precisa_atencao = False
cred.ativo = True
cred.save()

# Apagar token em cache (força re-login)
CacheTokenProvedor.objects.filter(credencial=cred).delete()

print('Atualizado.')
```

---

## Solis — Atualizar Credenciais

```bash
sudo docker compose exec web python manage.py shell
```

```python
from provedores.cripto import criptografar_credenciais
from provedores.models import CredencialProvedor

cred = CredencialProvedor.objects.get(provedor='solis')
cred.credenciais_enc = criptografar_credenciais({
    'api_key': '1300386381677237960',
    'app_secret': 'novo_app_secret'
})
cred.precisa_atencao = False
cred.ativo = True
cred.save()

print('Atualizado.')
```

---

## Cadastrar Novo Provedor

```python
from provedores.cripto import criptografar_credenciais
from provedores.models import CredencialProvedor

CredencialProvedor.objects.create(
    provedor='solarman',   # deve estar em PROVEDORES
    credenciais_enc=criptografar_credenciais({
        # estrutura depende do adaptador
    }),
    ativo=True
)
```

---

## Desativar um Provedor Temporariamente

```python
CredencialProvedor.objects.filter(provedor='hoymiles').update(ativo=False)
```

O Beat ignora credenciais com `ativo=False`. Para reativar:

```python
CredencialProvedor.objects.filter(provedor='hoymiles').update(ativo=True, precisa_atencao=False)
```

---

## Quando `precisa_atencao=True`

Este flag é ativado automaticamente quando a coleta retorna `ProvedorErroAuth` (credenciais inválidas). O sistema **para de tentar** coletar até que o flag seja limpo manualmente.

**O que fazer:**
1. Verificar se a senha/token foi alterado no portal do provedor
2. Atualizar as credenciais (comandos acima)
3. O flag é limpo automaticamente na próxima coleta bem-sucedida

---

## Backup da CHAVE_CRIPTOGRAFIA

A `CHAVE_CRIPTOGRAFIA` é necessária para descriptografar todas as credenciais no banco. Se perdida, será necessário recadastrar todas as credenciais.

```bash
# Ver a chave atual na VPS
grep CHAVE_CRIPTOGRAFIA ~/monitoramento_firmasolar/backend_monitoramento/.env
```

**Guarde esta chave em um local seguro** (ex: gerenciador de senhas).

---

## Veja Também

- [[modulos/provedores]]
- [[provedores/fusionsolar]]
- [[provedores/hoymiles]]
- [[provedores/solis]]
