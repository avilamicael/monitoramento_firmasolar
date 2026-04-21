"""
Testes do adaptador FoxESS — foco nos comportamentos específicos desta API:

  - status derivado (device/list reporta status errado; decidimos a partir
    de currentFault e presença de tempo real)
  - energia total: PVEnergyTotal do real/query é preferido a cumulative
    (cumulative tem bug conhecido da API)
  - detecção de fault: currentFault vem como string '' quando normal
  - alertas são sintetizados (não há endpoint nativo)
  - trifásico: média de tensão, soma de corrente só das fases ativas
  - assinatura MD5 com \\r\\n literal (4 caracteres, NÃO CR+LF)
"""
import hashlib
from datetime import datetime, timezone
from unittest.mock import patch

import pytest

from provedores.foxess.adaptador import FoxessAdaptador, _fault_ativo
from provedores.foxess.autenticacao import montar_headers


CREDENCIAIS = {'api_key': 'test-api-key-000'}


# ── assinatura ────────────────────────────────────────────────────────────────

class TestAssinatura:
    def test_signature_usa_barra_r_barra_n_literal_nao_crlf(self):
        """
        A FoxESS exige \\r\\n como 4 chars literais no buffer assinado.
        Se usarmos CR+LF interpretado, o servidor responde errno=40256
        'illegal signature'. Regressão validada em produção.
        """
        headers = montar_headers('/op/v0/plant/list', 'key123')
        ts = headers['timestamp']
        esperado = hashlib.md5(
            fr'/op/v0/plant/list\r\nkey123\r\n{ts}'.encode('utf-8')
        ).hexdigest()
        assert headers['signature'] == esperado

    def test_signature_com_crlf_real_seria_diferente_da_literal(self):
        """Confirmação explícita de que a regra é intencional — não cair em CR+LF."""
        raw_literal = fr'/p\r\nkey\r\n1'
        raw_crlf = '/p\r\nkey\r\n1'
        assert hashlib.md5(raw_literal.encode()).hexdigest() != hashlib.md5(raw_crlf.encode()).hexdigest()


# ── detecção de fault ────────────────────────────────────────────────────────

class TestFaultAtivo:
    def test_string_vazia_nao_eh_fault(self):
        assert _fault_ativo({'currentFault': '', 'currentFaultCount': 0}) is False

    def test_string_com_espacos_nao_eh_fault(self):
        assert _fault_ativo({'currentFault': '   ', 'currentFaultCount': 0}) is False

    def test_codigo_string_eh_fault(self):
        assert _fault_ativo({'currentFault': '0x1234', 'currentFaultCount': 1}) is True

    def test_count_maior_que_zero_eh_fault_mesmo_com_current_vazio(self):
        """Se count>0 mas currentFault vazio, ainda consideramos fault (a API é inconsistente)."""
        assert _fault_ativo({'currentFault': '', 'currentFaultCount': 2}) is True

    def test_currentfault_ausente_nao_eh_fault(self):
        assert _fault_ativo({}) is False

    def test_count_zero_string_nao_eh_fault(self):
        assert _fault_ativo({'currentFault': '', 'currentFaultCount': '0'}) is False


# ── status derivado ──────────────────────────────────────────────────────────

class TestDerivarStatusUsina:
    def test_usina_sem_dispositivos_vira_construcao(self):
        assert FoxessAdaptador._derivar_status_usina(0, 0, False, 0) == 'construcao'

    def test_com_fault_vira_aviso(self):
        assert FoxessAdaptador._derivar_status_usina(
            qtd_alertas=1, qtd_online=2, qualquer_com_dado=True, total_dispositivos=3,
        ) == 'aviso'

    def test_sem_dado_em_nenhum_device_vira_offline(self):
        """Tempo real não respondeu para nenhum device — usina provavelmente offline."""
        assert FoxessAdaptador._derivar_status_usina(
            qtd_alertas=0, qtd_online=0, qualquer_com_dado=False, total_dispositivos=2,
        ) == 'offline'

    def test_tudo_ok_vira_normal(self):
        assert FoxessAdaptador._derivar_status_usina(
            qtd_alertas=0, qtd_online=2, qualquer_com_dado=True, total_dispositivos=2,
        ) == 'normal'


# ── normalização de usina ────────────────────────────────────────────────────

class TestNormalizarUsina:
    def _montar_adaptador_com_cache(self, usina_raw, detalhe, dispositivos, tempo_real, geracao):
        adaptador = FoxessAdaptador(CREDENCIAIS)
        adaptador._usinas_raw = [usina_raw]
        adaptador._detalhes_usina = {str(usina_raw['stationID']): detalhe}
        adaptador._dispositivos_raw = dispositivos
        adaptador._tempo_real = tempo_real
        adaptador._geracao = geracao
        adaptador._hidratado = True
        return adaptador

    def test_agrega_potencia_energia_de_todos_os_devices_da_usina(self):
        adaptador = self._montar_adaptador_com_cache(
            usina_raw={'stationID': 'S1', 'name': 'Usina A', 'ianaTimezone': 'America/Sao_Paulo'},
            detalhe={'capacity': 5.0, 'address': 'Rua X', 'city': 'São José', 'country': 'BR'},
            dispositivos=[
                {'deviceSN': 'SN1', 'stationID': 'S1'},
                {'deviceSN': 'SN2', 'stationID': 'S1'},
                {'deviceSN': 'SN3', 'stationID': 'OUTRA'},  # não deve entrar
            ],
            tempo_real={
                'SN1': {'generationPower': 1.5, 'todayYield': 5.0, 'PVEnergyTotal': 1000.0, 'currentFault': '', 'currentFaultCount': 0},
                'SN2': {'generationPower': 0.8, 'todayYield': 3.0, 'PVEnergyTotal': 500.0, 'currentFault': '', 'currentFaultCount': 0},
            },
            geracao={
                'SN1': {'today': 5.0, 'month': 120.0, 'cumulative': 1000.0},
                'SN2': {'today': 3.0, 'month': 80.0, 'cumulative': 500.0},
            },
        )
        [dados] = adaptador.buscar_usinas()
        assert dados.id_usina_provedor == 'S1'
        assert dados.potencia_atual_kw == 2.3
        assert dados.energia_hoje_kwh == 8.0
        assert dados.energia_mes_kwh == 200.0
        assert dados.energia_total_kwh == 1500.0
        assert dados.capacidade_kwp == 5.0
        assert dados.qtd_inversores == 2
        assert dados.qtd_inversores_online == 2
        assert dados.qtd_alertas == 0
        assert dados.status == 'normal'
        assert dados.endereco == 'Rua X, São José, BR'

    def test_energia_total_usa_max_entre_pvenergytotal_e_cumulative(self):
        """Se uma das fontes estiver com valor absurdamente baixo, o max cobre."""
        adaptador = self._montar_adaptador_com_cache(
            usina_raw={'stationID': 'S1', 'name': 'U', 'ianaTimezone': 'America/Sao_Paulo'},
            detalhe={'capacity': 2.5},
            dispositivos=[{'deviceSN': 'SN1', 'stationID': 'S1'}],
            tempo_real={'SN1': {'PVEnergyTotal': 1197.4, 'todayYield': 1.8,
                                'currentFault': '', 'currentFaultCount': 0}},
            geracao={'SN1': {'today': 1198.4, 'cumulative': 0.5, 'month': 50.0}},
        )
        [dados] = adaptador.buscar_usinas()
        assert dados.energia_total_kwh == 1197.4

    def test_energia_hoje_prefere_todayyield_nao_generation_today(self):
        """
        Bug confirmado na API: `generation.today` retorna o acumulado total em
        ~75% dos devices (ex: microinversor 2.5kW reportando 1198kWh num único
        dia). `todayYield` do real/query é sempre o diário correto.
        """
        adaptador = self._montar_adaptador_com_cache(
            usina_raw={'stationID': 'S1', 'name': 'U', 'ianaTimezone': 'America/Sao_Paulo'},
            detalhe={'capacity': 2.5},
            dispositivos=[{'deviceSN': 'SN1', 'stationID': 'S1'}],
            tempo_real={'SN1': {'todayYield': 1.8, 'PVEnergyTotal': 1197.4,
                                'currentFault': '', 'currentFaultCount': 0}},
            geracao={'SN1': {'today': 1198.4, 'cumulative': 1197.4, 'month': 1198.4}},
        )
        [dados] = adaptador.buscar_usinas()
        # Usa todayYield=1.8, não o generation.today=1198.4 bugado
        assert dados.energia_hoje_kwh == 1.8

    def test_energia_hoje_fallback_para_generation_today_quando_device_offline(self):
        """Sem tempo real, recorre a generation.today (melhor que nada)."""
        adaptador = self._montar_adaptador_com_cache(
            usina_raw={'stationID': 'S1', 'name': 'U', 'ianaTimezone': 'America/Sao_Paulo'},
            detalhe={'capacity': 2.5},
            dispositivos=[{'deviceSN': 'SN1', 'stationID': 'S1'}],
            tempo_real={},  # device não respondeu no real/query
            geracao={'SN1': {'today': 7.5, 'cumulative': 1000.0, 'month': 100.0}},
        )
        [dados] = adaptador.buscar_usinas()
        assert dados.energia_hoje_kwh == 7.5

    def test_usina_sem_tempo_real_vira_offline(self):
        adaptador = self._montar_adaptador_com_cache(
            usina_raw={'stationID': 'S1', 'name': 'U', 'ianaTimezone': 'America/Sao_Paulo'},
            detalhe={'capacity': 2.5},
            dispositivos=[{'deviceSN': 'SN1', 'stationID': 'S1'}],
            tempo_real={},  # nenhum device respondeu
            geracao={},
        )
        [dados] = adaptador.buscar_usinas()
        assert dados.status == 'offline'
        assert dados.qtd_inversores_online == 0

    def test_usina_com_fault_em_um_device_vira_aviso(self):
        adaptador = self._montar_adaptador_com_cache(
            usina_raw={'stationID': 'S1', 'name': 'U', 'ianaTimezone': 'America/Sao_Paulo'},
            detalhe={'capacity': 5.0},
            dispositivos=[
                {'deviceSN': 'SN1', 'stationID': 'S1'},
                {'deviceSN': 'SN2', 'stationID': 'S1'},
            ],
            tempo_real={
                'SN1': {'generationPower': 1.5, 'currentFault': '', 'currentFaultCount': 0},
                'SN2': {'generationPower': 0.0, 'currentFault': 'E01', 'currentFaultCount': 1},
            },
            geracao={'SN1': {'today': 5.0}, 'SN2': {'today': 0.0}},
        )
        [dados] = adaptador.buscar_usinas()
        assert dados.status == 'aviso'
        assert dados.qtd_alertas == 1
        assert dados.qtd_inversores_online == 1


# ── normalização de inversor ─────────────────────────────────────────────────

class TestNormalizarInversor:
    def _montar(self, detalhe, variaveis, geracao):
        a = FoxessAdaptador(CREDENCIAIS)
        a._dispositivos_raw = [{'deviceSN': 'SN1', 'stationID': 'S1'}]
        a._detalhes_dispositivo = {'SN1': detalhe}
        a._tempo_real = {'SN1': variaveis}
        a._geracao = {'SN1': geracao}
        a._hidratado = True
        return a

    def test_monofasico_tensao_ac_vem_da_fase_r(self):
        """
        Só a fase R tem tensão. Média deve usar apenas fases ativas,
        não puxar 0s das fases S e T (senão daria 73V ao invés de 220V).
        """
        adaptador = self._montar(
            detalhe={'deviceType': 'Q1-2500-E'},
            variaveis={
                'generationPower': 1.7, 'todayYield': 1.8, 'PVEnergyTotal': 1197.4,
                'RVolt': 219.3, 'SVolt': 0.0, 'TVolt': 0.0,
                'RCurrent': 7.8, 'SCurrent': 0.0, 'TCurrent': 0.0, 'RFreq': 60.03,
                'invTemperation': 48.0, 'pv1Volt': 39.3, 'pv1Current': 11.4,
                'pv1Power': 0.448, 'pv2Power': 0.444, 'currentFault': '',
            },
            # `generation.today` vem bugado, mas o adaptador deve ignorar
            # quando há tempo real disponível.
            geracao={'today': 1197.4, 'cumulative': 1197.4, 'month': 1197.4},
        )
        [inv] = adaptador.buscar_inversores('S1')
        assert inv.tensao_ac_v == 219.3
        assert inv.corrente_ac_a == 7.8
        assert inv.frequencia_hz == 60.03
        assert inv.temperatura_c == 48.0
        assert inv.tensao_dc_v == 39.3
        assert inv.modelo == 'Q1-2500-E'
        assert inv.pac_kw == 1.7
        assert inv.energia_hoje_kwh == 1.8  # todayYield, não o generation.today bugado
        assert inv.energia_total_kwh == 1197.4
        assert inv.strings_mppt == {'string1': 0.448, 'string2': 0.444}

    def test_trifasico_tensao_ac_eh_media_das_tres_fases(self):
        adaptador = self._montar(
            detalhe={'deviceType': 'T3-10'},
            variaveis={
                'generationPower': 9.0, 'RVolt': 220.0, 'SVolt': 221.0, 'TVolt': 219.0,
                'RCurrent': 13.0, 'SCurrent': 13.2, 'TCurrent': 12.8, 'RFreq': 60.0,
                'currentFault': '', 'currentFaultCount': 0,
            },
            geracao={'today': 45.0, 'cumulative': 5000.0},
        )
        [inv] = adaptador.buscar_inversores('S1')
        assert inv.tensao_ac_v == pytest.approx(220.0)
        assert inv.corrente_ac_a == pytest.approx(39.0)  # soma das três

    def test_device_sem_tempo_real_fica_offline(self):
        adaptador = self._montar(
            detalhe={'deviceType': 'Q1-2500-E'},
            variaveis={},
            geracao={},
        )
        [inv] = adaptador.buscar_inversores('S1')
        assert inv.estado == 'offline'
        assert inv.pac_kw == 0.0

    def test_device_com_fault_fica_aviso(self):
        adaptador = self._montar(
            detalhe={'deviceType': 'Q1-2500-E'},
            variaveis={'generationPower': 0.0, 'currentFault': 'E05', 'currentFaultCount': 1},
            geracao={'today': 0.0},
        )
        [inv] = adaptador.buscar_inversores('S1')
        assert inv.estado == 'aviso'


# ── alertas sintéticos ───────────────────────────────────────────────────────

class TestBuscarAlertas:
    def _montar(self, dispositivos, tempo_real):
        a = FoxessAdaptador(CREDENCIAIS)
        a._dispositivos_raw = dispositivos
        a._tempo_real = tempo_real
        a._hidratado = True
        return a

    def test_nenhum_device_com_fault_nenhum_alerta(self):
        adaptador = self._montar(
            dispositivos=[{'deviceSN': 'SN1', 'stationID': 'S1'}],
            tempo_real={'SN1': {'currentFault': '', 'currentFaultCount': 0}},
        )
        assert adaptador.buscar_alertas() == []

    def test_sintetiza_alerta_por_device_com_fault(self):
        adaptador = self._montar(
            dispositivos=[
                {'deviceSN': 'SN1', 'stationID': 'S1'},
                {'deviceSN': 'SN2', 'stationID': 'S1'},
                {'deviceSN': 'SN3', 'stationID': 'S2'},
            ],
            tempo_real={
                # 4125 = PV4 curto-circuito interno → critico
                'SN1': {'currentFault': '4125', 'currentFaultCount': 1},
                'SN2': {'currentFault': '', 'currentFaultCount': 0},
                # 4158 = Tensão AC abaixo do limite → aviso
                'SN3': {'currentFault': '4158', 'currentFaultCount': 1},
            },
        )
        alertas = adaptador.buscar_alertas()
        assert len(alertas) == 2
        ids = {a.id_alerta_provedor for a in alertas}
        assert ids == {'SN1_4125', 'SN3_4158'}

        sn1 = next(a for a in alertas if a.equipamento_sn == 'SN1')
        assert sn1.nivel == 'critico'
        assert 'PV4 curto-circuito interno' in sn1.mensagem
        assert '4125' in sn1.mensagem

        sn3 = next(a for a in alertas if a.equipamento_sn == 'SN3')
        assert sn3.nivel == 'aviso'
        assert 'Tensão AC abaixo do limite' in sn3.mensagem

    def test_alerta_com_codigo_desconhecido_usa_fallback_generico(self):
        """Código fora do catálogo FoxESS Q — mensagem genérica, nível aviso."""
        adaptador = self._montar(
            dispositivos=[{'deviceSN': 'SN1', 'stationID': 'S1'}],
            tempo_real={'SN1': {'currentFault': '9999', 'currentFaultCount': 1}},
        )
        [alerta] = adaptador.buscar_alertas()
        assert alerta.id_alerta_provedor == 'SN1_9999'
        assert 'não catalogado' in alerta.mensagem
        assert alerta.nivel == 'aviso'

    def test_alerta_com_multiplos_codigos_usa_mais_severo(self):
        """
        Quando a rede cai, o inversor reporta "4151,4156,4158" (Lost AC +
        Under Freq + Under Voltage) — todos 'aviso'. Mensagem deve conter as 3.
        """
        adaptador = self._montar(
            dispositivos=[{'deviceSN': 'SN1', 'stationID': 'S1'}],
            tempo_real={'SN1': {'currentFault': '4151,4156,4158', 'currentFaultCount': 3}},
        )
        [alerta] = adaptador.buscar_alertas()
        assert alerta.id_alerta_provedor == 'SN1_4151,4156,4158'
        assert alerta.nivel == 'aviso'
        assert 'Perda de AC' in alerta.mensagem
        assert 'Frequência AC abaixo' in alerta.mensagem
        assert 'Tensão AC abaixo' in alerta.mensagem

    def test_codigo_critico_domina_quando_combinado_com_aviso(self):
        """Mistura de severidades — o nível do alerta sobe para o mais severo."""
        adaptador = self._montar(
            dispositivos=[{'deviceSN': 'SN1', 'stationID': 'S1'}],
            # 4125 = critico (PV4 curto), 4158 = aviso (Under Voltage)
            tempo_real={'SN1': {'currentFault': '4125,4158', 'currentFaultCount': 2}},
        )
        [alerta] = adaptador.buscar_alertas()
        assert alerta.nivel == 'critico'

    def test_alerta_com_currentfault_count_mas_codigo_vazio_usa_fallback(self):
        """Se count>0 mas currentFault vazio (inconsistência da API), usa 'fault' como código."""
        adaptador = self._montar(
            dispositivos=[{'deviceSN': 'SN1', 'stationID': 'S1'}],
            tempo_real={'SN1': {'currentFault': '', 'currentFaultCount': 3}},
        )
        [alerta] = adaptador.buscar_alertas()
        assert alerta.id_alerta_provedor == 'SN1_fault'
        assert alerta.id_tipo_alarme_provedor == 'fault'
        assert alerta.nivel == 'critico'

    def test_filtra_por_usina_quando_id_fornecido(self):
        adaptador = self._montar(
            dispositivos=[
                {'deviceSN': 'SN1', 'stationID': 'S1'},
                {'deviceSN': 'SN2', 'stationID': 'S2'},
            ],
            tempo_real={
                'SN1': {'currentFault': 'A', 'currentFaultCount': 1},
                'SN2': {'currentFault': 'B', 'currentFaultCount': 1},
            },
        )
        alertas = adaptador.buscar_alertas(id_usina_provedor='S1')
        assert [a.equipamento_sn for a in alertas] == ['SN1']


# ── capacidades e contrato ──────────────────────────────────────────────────

class TestContrato:
    def test_chave_provedor(self):
        assert FoxessAdaptador(CREDENCIAIS).chave_provedor == 'foxess'

    def test_capacidades_declaradas(self):
        cap = FoxessAdaptador(CREDENCIAIS).capacidades
        assert cap.suporta_inversores is True
        assert cap.suporta_alertas is True
        assert cap.alertas_por_conta is True
        assert cap.limite_requisicoes == 1
        assert cap.janela_segundos == 1

    def test_nao_tem_cache_de_token(self):
        """FoxESS é stateless — não precisa persistir token."""
        assert FoxessAdaptador(CREDENCIAIS).obter_cache_token() is None
        assert FoxessAdaptador(CREDENCIAIS).precisa_renovar_token() is False
