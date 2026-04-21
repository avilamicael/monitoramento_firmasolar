"""
Adaptador FoxESS — normaliza a FoxESS OpenAPI para os dataclasses do sistema.

Particularidades desta API (validadas em produção):

  1. Não há endpoint de alertas/alarmes. Alertas são sintetizados a partir
     dos campos `currentFault`/`currentFaultCount` reportados no real/query.
     `id_alerta_provedor` é `{deviceSN}_{currentFault}` — a persistência do
     `inicio` fica a cargo do ServicoIngestao (primeira detecção ganha).

  2. O campo `status` de `device/list` e `device/detail` é inconsistente
     (foi observado 3=offline em todos os devices mesmo gerando). O estado
     real é derivado do tempo real: `aviso` se há currentFault, senão `normal`.
     Usinas sem dado ficam a cargo do alerta interno `sem_geracao_diurna`.

  3. `generation.cumulative` tem bug conhecido (às vezes < `generation.today`).
     O total acumulado é preferencialmente lido de `PVEnergyTotal` no real/query.

  4. O contrato do sistema chama `buscar_usinas()`, `buscar_inversores(id)` e
     `buscar_alertas()` no mesmo ciclo. Para evitar N chamadas desperdiçadas
     e respeitar o orçamento de 1440 req/inversor/dia, o adaptador hidrata
     um cache local na primeira chamada e reutiliza nas demais. O cache vive
     apenas pela duração da instância (um ciclo de coleta).
"""
from datetime import datetime, timezone
import logging

from provedores.base import (
    AdaptadorProvedor,
    CapacidadesProvedor,
    DadosAlerta,
    DadosInversor,
    DadosUsina,
)
from .consultas import (
    consultar_geracao,
    consultar_tempo_real,
    detalhe_dispositivo,
    detalhe_usina,
    listar_dispositivos,
    listar_usinas,
)

logger = logging.getLogger(__name__)


def _para_float(valor) -> float:
    try:
        if valor is None or valor == '':
            return 0.0
        return float(valor)
    except (TypeError, ValueError):
        return 0.0


def _fault_ativo(variaveis: dict) -> bool:
    """
    True se o device tem falha ativa agora.

    `currentFault` vem como string ('' quando sem falha). `currentFaultCount`
    vem como int. Tratamos qualquer valor truthy em currentFault, ou count > 0.
    """
    fault = variaveis.get('currentFault')
    if isinstance(fault, str):
        fault = fault.strip()
    if fault not in (None, '', 0, '0'):
        return True
    try:
        if int(variaveis.get('currentFaultCount') or 0) > 0:
            return True
    except (TypeError, ValueError):
        pass
    return False


class FoxessAdaptador(AdaptadorProvedor):
    """
    Adaptador para a FoxESS OpenAPI.

    Autenticação stateless via MD5-signed headers por requisição — sem token,
    sem refresh.

    Credenciais (no banco, criptografadas): {"api_key": "..."}
    """

    def __init__(self, credenciais: dict):
        self._api_key = credenciais['api_key']
        # Cache por instância (ciclo de coleta).
        self._hidratado = False
        self._usinas_raw: list[dict] = []
        self._detalhes_usina: dict[str, dict] = {}
        self._dispositivos_raw: list[dict] = []
        self._detalhes_dispositivo: dict[str, dict] = {}
        self._tempo_real: dict[str, dict] = {}
        self._geracao: dict[str, dict] = {}

    @property
    def chave_provedor(self) -> str:
        return 'foxess'

    @property
    def capacidades(self) -> CapacidadesProvedor:
        return CapacidadesProvedor(
            suporta_inversores=True,
            suporta_alertas=True,
            alertas_por_conta=True,
            # 1 req/seg documentado. Orçamento de 1440 chamadas/inversor/dia
            # é vasto para 48 coletas/dia (30min), mas mantemos pool pequeno
            # para não fazer bursts concorrentes.
            limite_requisicoes=1,
            janela_segundos=1,
        )

    # ── Contrato público ────────────────────────────────────────────────────

    def buscar_usinas(self) -> list[DadosUsina]:
        self._hidratar()
        return [self._normalizar_usina(r) for r in self._usinas_raw]

    def buscar_inversores(self, id_usina_provedor: str) -> list[DadosInversor]:
        self._hidratar()
        sns = [
            d['deviceSN'] for d in self._dispositivos_raw
            if str(d.get('stationID')) == str(id_usina_provedor) and d.get('deviceSN')
        ]
        return [self._normalizar_inversor(sn, id_usina_provedor) for sn in sns]

    def buscar_alertas(self, id_usina_provedor: str | None = None) -> list[DadosAlerta]:
        self._hidratar()
        alertas: list[DadosAlerta] = []
        for dispositivo in self._dispositivos_raw:
            sn = dispositivo.get('deviceSN')
            station = str(dispositivo.get('stationID') or '')
            if not sn or not station:
                continue
            if id_usina_provedor and str(id_usina_provedor) != station:
                continue
            variaveis = self._tempo_real.get(sn, {})
            if not _fault_ativo(variaveis):
                continue
            alertas.append(self._sintetizar_alerta(sn, station, variaveis))
        return alertas

    # ── Hidratação do cache ─────────────────────────────────────────────────

    def _hidratar(self) -> None:
        """
        Faz todas as chamadas HTTP que o ciclo de coleta precisa, uma vez.

        Sequência:
          1. plant/list           — 1 chamada
          2. plant/detail × N     — N usinas
          3. device/list          — 1 chamada
          4. device/detail × M    — M dispositivos (para capacity, versões, baterias)
          5. device/real/query    — em lotes de 50 SNs
          6. device/generation × M — M dispositivos

        Com 14 usinas e 50 devices: 1+14+1+50+1+50 = 117 chamadas por ciclo.
        """
        if self._hidratado:
            return

        self._usinas_raw = listar_usinas(self._api_key)
        for usina in self._usinas_raw:
            sid = str(usina.get('stationID') or '')
            if not sid:
                continue
            try:
                self._detalhes_usina[sid] = detalhe_usina(sid, self._api_key)
            except Exception as exc:  # noqa: BLE001 — hidratação é best-effort
                logger.warning('FoxESS: falha ao obter detalhe da usina %s — %s', sid, exc)
                self._detalhes_usina[sid] = {}

        self._dispositivos_raw = listar_dispositivos(self._api_key)
        sns = [d['deviceSN'] for d in self._dispositivos_raw if d.get('deviceSN')]

        for sn in sns:
            try:
                self._detalhes_dispositivo[sn] = detalhe_dispositivo(sn, self._api_key)
            except Exception as exc:  # noqa: BLE001
                logger.warning('FoxESS: falha ao obter detalhe do device %s — %s', sn, exc)
                self._detalhes_dispositivo[sn] = {}

        try:
            self._tempo_real = consultar_tempo_real(sns, self._api_key)
        except Exception as exc:  # noqa: BLE001
            logger.warning('FoxESS: falha no real/query em lote — %s', exc)
            self._tempo_real = {}

        for sn in sns:
            try:
                self._geracao[sn] = consultar_geracao(sn, self._api_key)
            except Exception as exc:  # noqa: BLE001
                logger.warning('FoxESS: falha em generation do device %s — %s', sn, exc)
                self._geracao[sn] = {}

        self._hidratado = True

    # ── Normalização ────────────────────────────────────────────────────────

    def _normalizar_usina(self, r: dict) -> DadosUsina:
        sid = str(r.get('stationID') or '')
        detalhe = self._detalhes_usina.get(sid, {})
        dispositivos_da_usina = [
            d for d in self._dispositivos_raw if str(d.get('stationID') or '') == sid
        ]

        potencia_kw = 0.0
        energia_hoje_kwh = 0.0
        energia_mes_kwh = 0.0
        energia_total_kwh = 0.0
        qtd_online = 0
        qtd_alertas = 0
        qualquer_com_dado = False

        for d in dispositivos_da_usina:
            sn = d.get('deviceSN')
            if not sn:
                continue
            variaveis = self._tempo_real.get(sn, {})
            geracao = self._geracao.get(sn, {})

            potencia_kw += _para_float(variaveis.get('generationPower'))
            # `todayYield` do real/query é a fonte confiável do valor diário.
            # `generation.today` tem bug conhecido: em ~75% dos devices testados
            # retorna o valor acumulado total ao invés do diário. Fallback mesmo
            # assim para o caso de variaveis vazio (device offline).
            hoje_sn = _para_float(variaveis.get('todayYield'))
            if hoje_sn == 0.0 and not variaveis:
                hoje_sn = _para_float(geracao.get('today'))
            energia_hoje_kwh += hoje_sn
            energia_mes_kwh += _para_float(geracao.get('month'))
            # Total: PVEnergyTotal (real/query) e cumulative (generation) batem na
            # maioria dos casos. Pegamos o maior para cobrir imprecisões numéricas.
            total_sn = max(
                _para_float(variaveis.get('PVEnergyTotal')),
                _para_float(geracao.get('cumulative')),
            )
            energia_total_kwh += total_sn

            if variaveis:  # o device respondeu no real/query
                qualquer_com_dado = True
                if _fault_ativo(variaveis):
                    qtd_alertas += 1
                else:
                    qtd_online += 1

        status = self._derivar_status_usina(qtd_alertas, qtd_online, qualquer_com_dado,
                                            total_dispositivos=len(dispositivos_da_usina))

        endereco = ', '.join(filter(None, [
            detalhe.get('address'), detalhe.get('city'), detalhe.get('country'),
        ]))

        return DadosUsina(
            id_usina_provedor=sid,
            nome=r.get('name') or detalhe.get('stationName') or '(sem nome)',
            capacidade_kwp=_para_float(detalhe.get('capacity')),
            potencia_atual_kw=round(potencia_kw, 3),
            energia_hoje_kwh=round(energia_hoje_kwh, 3),
            energia_mes_kwh=round(energia_mes_kwh, 3),
            energia_total_kwh=round(energia_total_kwh, 3),
            status=status,
            data_medicao=datetime.now(timezone.utc),
            fuso_horario=r.get('ianaTimezone') or detalhe.get('timezone') or 'America/Sao_Paulo',
            endereco=endereco,
            qtd_inversores=len(dispositivos_da_usina),
            qtd_inversores_online=qtd_online,
            qtd_alertas=qtd_alertas,
            payload_bruto={'plant': r, 'detail': detalhe},
        )

    @staticmethod
    def _derivar_status_usina(qtd_alertas: int, qtd_online: int,
                              qualquer_com_dado: bool, total_dispositivos: int) -> str:
        """
        Regras:
          - algum device em fault                     → 'aviso'
          - nenhum device respondeu ao real/query     → 'offline'
          - pelo menos um respondeu, nenhum em fault  → 'normal'
          - usina sem dispositivos cadastrados        → 'construcao'
        """
        if total_dispositivos == 0:
            return 'construcao'
        if qtd_alertas > 0:
            return 'aviso'
        if not qualquer_com_dado:
            return 'offline'
        return 'normal'

    def _normalizar_inversor(self, sn: str, id_usina: str) -> DadosInversor:
        detalhe = self._detalhes_dispositivo.get(sn, {})
        variaveis = self._tempo_real.get(sn, {})
        geracao = self._geracao.get(sn, {})

        estado = 'aviso' if _fault_ativo(variaveis) else ('normal' if variaveis else 'offline')

        # Strings MPPT: pv1..pv18. Só grava os que vieram com potência.
        strings_mppt: dict[str, float] = {}
        for i in range(1, 19):
            p = variaveis.get(f'pv{i}Power')
            if p is not None:
                strings_mppt[f'string{i}'] = _para_float(p)

        # Trifásico vs monofásico: se S/T têm tensão > 0, é trifásico → média das 3.
        tensao_r = _para_float(variaveis.get('RVolt'))
        tensao_s = _para_float(variaveis.get('SVolt'))
        tensao_t = _para_float(variaveis.get('TVolt'))
        fases_ativas = [v for v in (tensao_r, tensao_s, tensao_t) if v > 0]
        tensao_ac = (sum(fases_ativas) / len(fases_ativas)) if fases_ativas else None

        corrente_r = _para_float(variaveis.get('RCurrent'))
        corrente_s = _para_float(variaveis.get('SCurrent'))
        corrente_t = _para_float(variaveis.get('TCurrent'))
        correntes_ativas = [c for c in (corrente_r, corrente_s, corrente_t) if c > 0]
        corrente_ac = sum(correntes_ativas) if correntes_ativas else None

        frequencia = _para_float(variaveis.get('RFreq')) or None

        # Energia total: max(PVEnergyTotal, cumulative) — ambos cobrem-se mutuamente.
        energia_total = max(
            _para_float(variaveis.get('PVEnergyTotal')),
            _para_float(geracao.get('cumulative')),
        )
        # Energia hoje: `todayYield` do real/query é confiável; `generation.today`
        # vem bugado em ~75% dos devices (retorna o total acumulado). Fallback só
        # quando não temos dado de tempo real.
        energia_hoje = _para_float(variaveis.get('todayYield'))
        if energia_hoje == 0.0 and not variaveis:
            energia_hoje = _para_float(geracao.get('today'))

        return DadosInversor(
            id_inversor_provedor=sn,
            id_usina_provedor=id_usina,
            numero_serie=sn,
            modelo=detalhe.get('deviceType') or '',
            estado=estado,
            pac_kw=_para_float(variaveis.get('generationPower')),
            energia_hoje_kwh=energia_hoje,
            energia_total_kwh=energia_total,
            soc_bateria=_para_float(variaveis.get('SoC')) or None,
            strings_mppt=strings_mppt,
            tensao_ac_v=tensao_ac,
            corrente_ac_a=corrente_ac,
            tensao_dc_v=_para_float(variaveis.get('pv1Volt')) or None,
            corrente_dc_a=_para_float(variaveis.get('pv1Current')) or None,
            frequencia_hz=frequencia,
            temperatura_c=_para_float(variaveis.get('invTemperation')) or None,
            data_medicao=datetime.now(timezone.utc),
            payload_bruto={'detail': detalhe, 'real': variaveis, 'generation': geracao},
        )

    def _sintetizar_alerta(self, sn: str, id_usina: str, variaveis: dict) -> DadosAlerta:
        """
        Sintetiza um alerta a partir de currentFault/currentFaultCount.

        `id_alerta_provedor` = `{sn}_{codigo_fault}`. Mesmo código no mesmo device
        mantém a identidade ao longo do tempo — o ServicoIngestao preserva o
        registro original (e seu `inicio`) via upsert.
        """
        fault = variaveis.get('currentFault')
        if isinstance(fault, str):
            fault = fault.strip()
        codigo = str(fault) if fault not in (None, '', 0, '0') else 'fault'
        id_alerta = f'{sn}_{codigo}'
        mensagem = f'Código de falha {codigo} reportado pelo inversor'
        return DadosAlerta(
            id_alerta_provedor=id_alerta,
            id_usina_provedor=id_usina,
            mensagem=mensagem,
            # Sem catálogo público de severidade — alertas da FoxESS são 'critico'
            # por padrão. O operador pode reclassificar via CatalogoAlarme.
            nivel='critico',
            inicio=datetime.now(timezone.utc),
            equipamento_sn=sn,
            estado='ativo',
            sugestao='',
            id_tipo_alarme_provedor=codigo,
            payload_bruto={'currentFault': variaveis.get('currentFault'),
                           'currentFaultCount': variaveis.get('currentFaultCount')},
        )
