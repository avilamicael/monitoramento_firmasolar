"""
Management command para extrair cidade e geocodificar (lat/lng) usinas a partir do endereço.

Usa a API gratuita Nominatim (OpenStreetMap) — sem API key necessária.
Limite: 1 req/segundo (respeitado automaticamente).

Uso:
    python manage.py geocode_usinas              # Processa apenas usinas com endereço mas sem lat/lng
    python manage.py geocode_usinas --force      # Reprocessa todas com endereço (sobrescreve lat/lng)
    python manage.py geocode_usinas --dry-run    # Mostra o que faria sem alterar o banco
"""

import re
import time

import requests
from django.core.management.base import BaseCommand

from usinas.models import Usina

NOMINATIM_URL = 'https://nominatim.openstreetmap.org/search'
HEADERS = {'User-Agent': 'FirmaSolar/1.0 (monitoramento solar)'}

# Cidades conhecidas de SC para fallback em endereços colados
CIDADES_SC = [
    'Florianópolis', 'São José', 'Palhoça', 'Biguaçu', 'Brusque',
    'Camboriú', 'Balneário Camboriú', 'Itajaí', 'Blumenau', 'Joinville',
    'Canelinha', 'Urubici', 'Santo Amaro da Imperatriz', 'Imbituba',
    'Tijucas', 'Garopaba', 'Governador Celso Ramos', 'Criciúma',
    'Tubarão', 'Laguna', 'Araranguá', 'Lages', 'Chapecó',
]


def limpar_endereco_colado(endereco: str) -> str:
    """
    Limpa endereços no formato colado dos provedores.
    "BrasilSCFlorianópolisCantoRua Tupinambá, 315" → "Rua Tupinambá, 315, Canto, Florianópolis, SC, Brasil"
    "BrasilSCSão JoséSerrariaRua Veríssimo..." → "Rua Veríssimo..., Serraria, São José, SC, Brasil"
    """
    if not endereco.startswith('Brasil'):
        return endereco

    # Remove "Brasil" e tenta encontrar o estado (2 letras maiúsculas)
    sem_brasil = endereco[6:]  # remove "Brasil"

    # Procurar UF (2 letras maiúsculas no início)
    uf_match = re.match(r'^([A-Z]{2})', sem_brasil)
    if not uf_match:
        return endereco
    uf = uf_match.group(1)
    resto = sem_brasil[2:]

    # Tentar encontrar cidade conhecida no início do resto
    cidade_encontrada = ''
    bairro_e_rua = resto
    for cidade in sorted(CIDADES_SC, key=len, reverse=True):
        if resto.startswith(cidade):
            cidade_encontrada = cidade
            bairro_e_rua = resto[len(cidade):]
            break

    if not cidade_encontrada:
        # Tentar split por padrão: primeira palavra com maiúscula seguida de minúsculas
        parts = re.match(r'^([A-ZÀ-Ÿ][a-zà-ÿ]+(?:\s+[A-ZÀ-Ÿ][a-zà-ÿ]+)*)', resto)
        if parts:
            cidade_encontrada = parts.group(1)
            bairro_e_rua = resto[len(cidade_encontrada):]

    if cidade_encontrada:
        # Tentar separar bairro da rua
        rua_match = re.match(r'^([A-ZÀ-Ÿa-zà-ÿ\s]+?)((?:Rua|R\.|Av\.|Avenida|Servidão|Travessa|Rod\.|Rodovia|Estrada|Alameda).*)', bairro_e_rua)
        if rua_match:
            bairro = rua_match.group(1).strip()
            rua = rua_match.group(2).strip()
            return f'{rua}, {bairro}, {cidade_encontrada}, {uf}, Brasil'
        # Sem rua identificável — pode ser só bairro+CEP
        return f'{bairro_e_rua.strip()}, {cidade_encontrada}, {uf}, Brasil'

    return endereco


def extrair_cidade(endereco: str) -> str:
    """
    Tenta extrair a cidade do endereço em vários formatos.
    """
    if not endereco:
        return ''

    # Formato colado: "BrasilSCFlorianópolis..."
    if endereco.startswith('Brasil'):
        sem_brasil = endereco[6:]
        uf_match = re.match(r'^[A-Z]{2}', sem_brasil)
        if uf_match:
            resto = sem_brasil[2:]
            for cidade in sorted(CIDADES_SC, key=len, reverse=True):
                if resto.startswith(cidade):
                    return cidade
            # Fallback: primeira sequência de palavras capitalizadas
            parts = re.match(r'^([A-ZÀ-Ÿ][a-zà-ÿ]+(?:\s+[A-ZÀ-Ÿ][a-zà-ÿ]+)*)', resto)
            if parts:
                return parts.group(1)

    # Formato "ANTÔNIO JOVITA...,SÃO JOSÉ" (tudo maiúsculo, separado por vírgula)
    if endereco.isupper() or re.search(r',[A-ZÀ-Ÿ\s]{3,}$', endereco):
        for cidade in CIDADES_SC:
            if cidade.upper() in endereco.upper():
                return cidade

    # Formato padrão: "Bairro, Cidade - UF" ou "Cidade - UF"
    match = re.search(r'([A-Za-zÀ-ÿ\s]+)\s*-\s*[A-Z]{2}', endereco)
    if match:
        cidade = match.group(1).strip()
        if ',' in cidade:
            cidade = cidade.split(',')[-1].strip()
        return cidade

    # Fallback: procurar cidade conhecida em qualquer posição
    endereco_lower = endereco.lower()
    for cidade in sorted(CIDADES_SC, key=len, reverse=True):
        if cidade.lower() in endereco_lower:
            return cidade

    return ''


def geocodificar(endereco: str) -> tuple[float | None, float | None]:
    """Consulta Nominatim para obter lat/lng. Tenta endereço limpo e fallbacks."""
    tentativas = []

    # Tentativa 1: endereço limpo
    limpo = limpar_endereco_colado(endereco)
    tentativas.append(limpo)

    # Tentativa 2: só a parte principal (sem CEP, sem Brazil/Brasil)
    simplificado = re.sub(r'\d{5}-?\d{3}', '', limpo)
    simplificado = re.sub(r',?\s*(Brazil|Brasil)\s*$', '', simplificado).strip().rstrip(',')
    if simplificado != limpo:
        tentativas.append(simplificado)

    # Tentativa 3: só cidade + estado
    cidade = extrair_cidade(endereco)
    if cidade:
        tentativas.append(f'{cidade}, SC, Brasil')

    for tentativa in tentativas:
        try:
            response = requests.get(
                NOMINATIM_URL,
                params={'q': tentativa, 'format': 'json', 'limit': 1, 'countrycodes': 'br'},
                headers=HEADERS,
                timeout=10,
            )
            response.raise_for_status()
            results = response.json()
            if results:
                return float(results[0]['lat']), float(results[0]['lon'])
        except Exception:
            pass
        time.sleep(1.1)

    return None, None


class Command(BaseCommand):
    help = 'Extrai cidade e geocodifica usinas a partir do endereço cadastrado'

    def add_arguments(self, parser):
        parser.add_argument('--force', action='store_true', help='Reprocessar todas (sobrescreve lat/lng existentes)')
        parser.add_argument('--dry-run', action='store_true', help='Mostra o que faria sem alterar o banco')
        parser.add_argument('--skip-geocode', action='store_true', help='Apenas extrair cidade, sem consultar Nominatim')

    def handle(self, *args, **options):
        force = options['force']
        dry_run = options['dry_run']
        skip_geocode = options['skip_geocode']

        qs = Usina.objects.exclude(endereco='')
        if not force:
            qs = qs.filter(
                latitude__isnull=True
            ) | Usina.objects.exclude(endereco='').filter(cidade='')
            qs = qs.distinct()

        usinas = list(qs.order_by('nome'))
        total = len(usinas)
        self.stdout.write(f'Usinas a processar: {total}')

        if total == 0:
            self.stdout.write(self.style.SUCCESS('Nenhuma usina para processar.'))
            return

        processadas = 0
        geocodificadas = 0
        cidades_extraidas = 0
        erros = 0

        for usina in usinas:
            campos_alterados = []

            # Extrair cidade
            if not usina.cidade or force:
                cidade = extrair_cidade(usina.endereco)
                if cidade:
                    if dry_run:
                        self.stdout.write(f'  [DRY] {usina.nome}: cidade = "{cidade}"')
                    else:
                        usina.cidade = cidade
                        campos_alterados.append('cidade')
                    cidades_extraidas += 1
                else:
                    self.stdout.write(self.style.WARNING(f'  [CIDADE?] {usina.nome}: nao extraiu cidade de "{usina.endereco}"'))

            # Geocodificar
            if not skip_geocode and (usina.latitude is None or force):
                self.stdout.write(f'  Geocodificando: {usina.nome}...')
                lat, lng = geocodificar(usina.endereco)
                if lat is not None:
                    if dry_run:
                        self.stdout.write(self.style.SUCCESS(f'    OK: lat={lat:.6f}, lng={lng:.6f}'))
                    else:
                        usina.latitude = lat
                        usina.longitude = lng
                        campos_alterados.extend(['latitude', 'longitude'])
                    geocodificadas += 1
                else:
                    self.stdout.write(self.style.WARNING(f'    FALHOU: "{usina.endereco}"'))
                    erros += 1

            if campos_alterados and not dry_run:
                usina.save(update_fields=campos_alterados)

            processadas += 1
            if processadas % 10 == 0:
                self.stdout.write(f'  Progresso: {processadas}/{total}')

        prefix = '[DRY RUN] ' if dry_run else ''
        self.stdout.write(self.style.SUCCESS(
            f'\n{prefix}Concluído: {processadas} processadas, '
            f'{cidades_extraidas} cidades extraídas, '
            f'{geocodificadas} geocodificadas, '
            f'{erros} erros'
        ))
