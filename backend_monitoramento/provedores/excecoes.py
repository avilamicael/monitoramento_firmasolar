"""
Exceções específicas dos provedores de energia solar.

Separadas em categorias para que o sistema de coleta possa decidir:
- ProvedorErroAuth → marcar credencial como 'precisa_atencao', sem retry
- ProvedorErroRateLimit → retry com backoff exponencial
- ProvedorErro → retry genérico
"""


class ProvedorErro(Exception):
    """Erro genérico de provedor. Pode ser tentado novamente."""


class ProvedorErroAuth(ProvedorErro):
    """
    Erro de autenticação — credenciais inválidas ou expiradas.
    Não deve ser tentado novamente automaticamente.
    Requer atenção manual na credencial.
    """


class ProvedorTokenExpirado(ProvedorErroAuth):
    """Token de sessão expirou. Deve forçar re-login."""


class ProvedorErroRateLimit(ProvedorErro):
    """
    Limite de requisições atingido.
    Deve aguardar e tentar novamente com backoff exponencial.
    """


class ProvedorErroDados(ProvedorErro):
    """Resposta inesperada do provedor — formato de dados inválido ou inesperado."""
