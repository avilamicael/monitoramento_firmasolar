import 'leaflet/dist/leaflet.css'
import { MapContainer, TileLayer, Marker, Popup } from 'react-leaflet'
import L from 'leaflet'
import type { MapaUsina } from '@/types/analytics'

interface MapaUsinasProps {
  usinas: MapaUsina[]
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
  // aviso | offline | construcao — qualquer anomalia e vermelho (fail-safe)
  return 'vermelho'
}

export function MapaUsinas({ usinas }: MapaUsinasProps) {
  const usinasComCoordenadas = usinas.filter(
    (u) => u.latitude !== null && u.longitude !== null,
  )

  if (usinasComCoordenadas.length === 0) {
    return (
      <p className="text-muted-foreground text-center py-8">
        Nenhuma usina com coordenadas disponíveis
      </p>
    )
  }

  return (
    <MapContainer
      center={[-15.0, -47.0]}
      zoom={5}
      style={{ height: '400px', width: '100%' }}
      className="rounded-lg border"
    >
      <TileLayer
        url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
        attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
      />
      {usinasComCoordenadas.map((usina) => (
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
  )
}
