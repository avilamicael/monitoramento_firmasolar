"""
Testes do adaptador Hoymiles — foco em:
  - parse de data_medicao (usa last_data_time/data_time no fuso da usina)
  - supressão de s_uoff quando a usina está sem comunicar há mais de 24h
    (nesses casos é Wi-Fi/datalogger offline, não desligamento real)
"""
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

import pytest

from provedores.hoymiles.adaptador import (
    HoymilesAdaptador,
    _parsear_data_medicao,
    _HORAS_LIMITE_SUOFF,
)


CREDENCIAIS = {'username': 'u', 'password': 'p', 'token': 'fake-token'}


# ── _parsear_data_medicao ────────────────────────────────────────────────────

class TestParsearDataMedicao:
    def test_last_data_time_em_sao_paulo_convertido_para_utc(self):
        rt = {'last_data_time': '2026-04-18 12:30:15'}
        resultado = _parsear_data_medicao(rt, 'America/Sao_Paulo')
        assert resultado == datetime(2026, 4, 18, 15, 30, 15, tzinfo=timezone.utc)

    def test_fallback_para_data_time_quando_last_data_time_ausente(self):
        rt = {'data_time': '2025-11-04 16:44:52'}
        resultado = _parsear_data_medicao(rt, 'America/Sao_Paulo')
        assert resultado == datetime(2025, 11, 4, 19, 44, 52, tzinfo=timezone.utc)

    def test_prefere_last_data_time_sobre_data_time(self):
        rt = {
            'last_data_time': '2026-04-20 10:00:00',
            'data_time': '2025-01-01 00:00:00',
        }
        resultado = _parsear_data_medicao(rt, 'America/Sao_Paulo')
        assert resultado == datetime(2026, 4, 20, 13, 0, 0, tzinfo=timezone.utc)

    def test_retorna_none_quando_payload_nao_tem_timestamp(self):
        assert _parsear_data_medicao({}, 'America/Sao_Paulo') is None

    def test_retorna_none_para_timestamp_em_formato_invalido(self):
        rt = {'last_data_time': 'quinta às 15h'}
        assert _parsear_data_medicao(rt, 'America/Sao_Paulo') is None

    def test_fuso_desconhecido_usa_sao_paulo_como_fallback(self):
        rt = {'last_data_time': '2026-04-18 12:00:00'}
        resultado = _parsear_data_medicao(rt, 'Mars/Olympus_Mons')
        # Sem erro; fallback para America/Sao_Paulo (UTC-3) → 15:00 UTC.
        assert resultado == datetime(2026, 4, 18, 15, 0, 0, tzinfo=timezone.utc)


# ── Supressão de s_uoff ──────────────────────────────────────────────────────

class TestExtrairAlertasSupressaoSUoff:
    """
    s_uoff deve ser emitido quando a usina comunicou recentemente (desligamento
    real, com dado no inversor) e suprimido quando está sem comunicar há >24h
    (Wi-Fi/datalogger offline — alerta `sem_comunicacao` cobre o caso).
    """

    def _adaptador_com_usina_comunicada(self, id_usina: str, horas_atras: float) -> HoymilesAdaptador:
        adaptador = HoymilesAdaptador(CREDENCIAIS)
        agora = datetime.now(timezone.utc)
        adaptador._ultima_comunicacao_por_usina[id_usina] = agora - timedelta(hours=horas_atras)
        return adaptador

    def test_s_uoff_emitido_quando_usina_comunicou_recentemente(self):
        """Usina reportando dado há 2h → s_uoff=true é real (pode estar desligada)."""
        adaptador = self._adaptador_com_usina_comunicada('12345', horas_atras=2)
        registros = [{'id': 12345, 'warn_data': {'s_uoff': True}}]
        alertas = adaptador._extrair_alertas(registros)
        assert len(alertas) == 1
        assert alertas[0].id_alerta_provedor == '12345_s_uoff'
        assert alertas[0].nivel == 'critico'

    def test_s_uoff_suprimido_quando_sem_comunicar_ha_mais_de_24h(self):
        """Usina sem dado há 5 meses → provavelmente Wi-Fi offline, não desligamento."""
        adaptador = self._adaptador_com_usina_comunicada('12345', horas_atras=24 * 150)
        registros = [{'id': 12345, 'warn_data': {'s_uoff': True}}]
        assert adaptador._extrair_alertas(registros) == []

    def test_s_uoff_proximo_ao_limite_mas_dentro_dele_e_emitido(self):
        """Dentro das 24h (ex: 23h50) ainda considera desligamento real."""
        adaptador = self._adaptador_com_usina_comunicada('12345', horas_atras=_HORAS_LIMITE_SUOFF - 0.2)
        registros = [{'id': 12345, 'warn_data': {'s_uoff': True}}]
        assert len(adaptador._extrair_alertas(registros)) == 1

    def test_s_uoff_logo_apos_limite_e_suprimido(self):
        """Passando do limite (ex: 24h10) já vira caso de sem_comunicacao."""
        adaptador = self._adaptador_com_usina_comunicada('12345', horas_atras=_HORAS_LIMITE_SUOFF + 0.2)
        registros = [{'id': 12345, 'warn_data': {'s_uoff': True}}]
        assert adaptador._extrair_alertas(registros) == []

    def test_outras_flags_nao_sao_afetadas_pela_supressao(self):
        """Apenas s_uoff tem a regra. dl, g_warn etc. sempre emitem."""
        adaptador = self._adaptador_com_usina_comunicada('12345', horas_atras=24 * 150)
        registros = [{
            'id': 12345,
            'warn_data': {'s_uoff': True, 'dl': True, 'g_warn': True},
        }]
        alertas = adaptador._extrair_alertas(registros)
        flags = {a.id_tipo_alarme_provedor for a in alertas}
        assert flags == {'dl', 'g_warn'}  # s_uoff suprimido

    def test_s_uoff_emitido_quando_nao_ha_dado_de_comunicacao_no_cache(self):
        """Sem informação → não suprime (comportamento conservador)."""
        adaptador = HoymilesAdaptador(CREDENCIAIS)  # cache vazio
        registros = [{'id': 99999, 'warn_data': {'s_uoff': True}}]
        assert len(adaptador._extrair_alertas(registros)) == 1


# ── _normalizar_usina popula o cache ─────────────────────────────────────────

class TestNormalizarUsinaPopulaCache:
    def test_normalizar_usina_armazena_last_data_time_no_cache(self):
        adaptador = HoymilesAdaptador(CREDENCIAIS)
        registro = {
            'id': 12230350,
            'name': 'Luciano De Oliveira',
            'capacitor': '6',
            'status': 3,
            'tz_name': 'America/Sao_Paulo',
            '_realtime': {
                'last_data_time': '2026-04-18 12:30:15',
                'data_time': '2026-04-18 12:30:15',
                'real_power': '0',
                'today_eq': '0.0',
                'month_eq': '298977',
                'total_eq': '1524354',
            },
        }
        dados = adaptador._normalizar_usina(registro)
        esperado = datetime(2026, 4, 18, 15, 30, 15, tzinfo=timezone.utc)
        assert dados.data_medicao == esperado
        assert adaptador._ultima_comunicacao_por_usina['12230350'] == esperado

    def test_normalizar_usina_sem_timestamp_usa_now_como_fallback(self):
        adaptador = HoymilesAdaptador(CREDENCIAIS)
        antes = datetime.now(timezone.utc)
        dados = adaptador._normalizar_usina({'id': 1, '_realtime': {}})
        depois = datetime.now(timezone.utc)
        assert antes <= dados.data_medicao <= depois
