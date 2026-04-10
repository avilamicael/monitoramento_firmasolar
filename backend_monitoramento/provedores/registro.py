"""
Registro de provedores disponíveis no sistema.

Para adicionar um novo provedor:
    1. Crie a pasta provedores/novo_provedor/ com autenticacao.py, consultas.py e adaptador.py
    2. Adicione uma linha no dicionário REGISTRO abaixo

O resto do sistema usa get_adaptador() — não precisa ser alterado.
"""
from provedores.base import AdaptadorProvedor

REGISTRO: dict[str, type] = {}


def _carregar_provedores():
    """Importação lazy para evitar problemas de circular import."""
    from provedores.solis import SolisAdaptador
    from provedores.hoymiles import HoymilesAdaptador
    from provedores.fusionsolar import FusionSolarAdaptador
    from provedores.auxsol import AuxsolAdaptador

    REGISTRO['solis'] = SolisAdaptador
    REGISTRO['hoymiles'] = HoymilesAdaptador
    REGISTRO['fusionsolar'] = FusionSolarAdaptador
    REGISTRO['auxsol'] = AuxsolAdaptador


def get_adaptador(chave_provedor: str, credenciais: dict) -> AdaptadorProvedor:
    """
    Retorna uma instância do adaptador para o provedor especificado.

    Args:
        chave_provedor: 'solis', 'hoymiles' ou 'fusionsolar'
        credenciais: dicionário já descriptografado com as credenciais

    Raises:
        ValueError: se o provedor não for reconhecido
    """
    if not REGISTRO:
        _carregar_provedores()

    classe = REGISTRO.get(chave_provedor)
    if not classe:
        provedores_disponiveis = ', '.join(REGISTRO.keys())
        raise ValueError(
            f'Provedor "{chave_provedor}" não reconhecido. '
            f'Disponíveis: {provedores_disponiveis}'
        )

    return classe(credenciais)
