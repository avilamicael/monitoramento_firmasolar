/**
 * Formatadores padronizados pt-BR para todo o frontend.
 * Máximo 3 casas decimais, separador de milhar com ponto.
 */

export function formatarNumero(valor: number, casas = 3): string {
  return valor.toLocaleString('pt-BR', {
    minimumFractionDigits: 0,
    maximumFractionDigits: casas,
  })
}

export function formatarEnergia(kwh: number): string {
  if (kwh >= 1_000_000) {
    return `${formatarNumero(kwh / 1_000_000)} GWh`
  }
  if (kwh >= 1_000) {
    return `${formatarNumero(kwh / 1_000)} MWh`
  }
  return `${formatarNumero(kwh)} kWh`
}

export function formatarPotencia(kw: number): string {
  if (kw >= 1_000) {
    return `${formatarNumero(kw / 1_000)} MW`
  }
  return `${formatarNumero(kw)} kW`
}

export function formatarMoeda(valor: number): string {
  return valor.toLocaleString('pt-BR', {
    style: 'currency',
    currency: 'BRL',
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  })
}

export function formatarDias(dias: number): string {
  return `${formatarNumero(dias, 0)} dia${dias !== 1 ? 's' : ''}`
}
