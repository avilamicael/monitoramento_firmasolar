import 'leaflet/dist/leaflet.css'
import { MapContainer, TileLayer, Marker, Popup } from 'react-leaflet'
import L from 'leaflet'
import { XIcon } from 'lucide-react'
import type { MapaUsina } from '@/types/analytics'

interface MapaUsinasProps {
  usinas: MapaUsina[]
  filtroProvedor?: string | null
  onLimparFiltro?: () => void
}

type CorMarcador = 'verde' | 'vermelho' | 'cinza'

const coresHex: Record<CorMarcador, string> = {
  verde: '#22c55e',
  vermelho: '#ef4444',
  cinza: '#9ca3af',
}

function criarIcone(cor: CorMarcador): L.DivIcon {
  return L.divIcon({
    className: '',
    html: `<div style="width:14px;height:14px;border-radius:50%;background:${coresHex[cor]};border:2px solid white;box-shadow:0 2px 4px rgba(0,0,0,0.3)"></div>`,
    iconSize: [14, 14],
    iconAnchor: [7, 7],
  })
}

function getCorMarcador(usina: MapaUsina): CorMarcador {
  if (!usina.ativo) return 'cinza'
  if (usina.status === 'normal') return 'verde'
  if (usina.status === 'sem_dados') return 'cinza'
  return 'vermelho'
}

function calcularCentro(usinas: MapaUsina[]): [number, number] {
  if (usinas.length === 0) return [-15.0, -47.0]

  const somaLat = usinas.reduce((acc, u) => acc + (u.latitude as number), 0)
  const somaLng = usinas.reduce((acc, u) => acc + (u.longitude as number), 0)

  return [somaLat / usinas.length, somaLng / usinas.length]
}

export function MapaUsinas({ usinas, filtroProvedor, onLimparFiltro }: MapaUsinasProps) {
  const usinasComCoordenadas = usinas.filter(
    (u) => u.latitude !== null && u.longitude !== null,
  )

  const usinasFiltradas = filtroProvedor
    ? usinasComCoordenadas.filter((u) => u.provedor === filtroProvedor)
    : usinasComCoordenadas

  if (usinasComCoordenadas.length === 0) {
    return (
      <p className="text-muted-foreground text-center py-8">
        Nenhuma usina com coordenadas disponíveis
      </p>
    )
  }

  const centro = calcularCentro(usinasFiltradas.length > 0 ? usinasFiltradas : usinasComCoordenadas)

  return (
    <div className="relative">
      {filtroProvedor && (
        <div className="absolute top-3 right-3 z-[1000] bg-background border rounded-md px-3 py-1.5 flex items-center gap-2 shadow-sm">
          <span className="text-sm font-medium">{filtroProvedor}</span>
          <button
            onClick={onLimparFiltro}
            className="text-muted-foreground hover:text-foreground"
            aria-label="Limpar filtro de provedor"
          >
            <XIcon className="size-4" />
          </button>
        </div>
      )}
      <MapContainer
        center={centro}
        zoom={filtroProvedor ? 6 : 5}
        style={{ height: '400px', width: '100%' }}
        className="rounded-lg border"
      >
        <TileLayer
          url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
          attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
        />
        {usinasFiltradas.map((usina) => (
          <Marker
            key={usina.id}
            position={[usina.latitude as number, usina.longitude as number]}
            icon={criarIcone(getCorMarcador(usina))}
          >
            <Popup>
              <div className="text-sm space-y-1">
                <p className="font-semibold">{usina.nome}</p>
                <p className="text-muted-foreground">Provedor: {usina.provedor}</p>
                <p className="text-muted-foreground">Status: {usina.status}</p>
              </div>
            </Popup>
          </Marker>
        ))}
      </MapContainer>
    </div>
  )
}
