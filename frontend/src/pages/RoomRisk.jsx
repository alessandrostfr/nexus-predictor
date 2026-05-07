import { AlertTriangle, Clock3, Database, Map as MapIcon, Radar, Route, Sparkles, UsersRound } from 'lucide-react';
import { useMemo, useState } from 'react';

import { EmptyPanel } from '../components/EmptyPanel.jsx';
import { EditionSelector } from '../components/EditionSelector.jsx';
import { MetricCard } from '../components/MetricCard.jsx';
import { RoomCapacityCard } from '../components/RoomCapacityCard.jsx';
import { ShellCard } from '../components/ShellCard.jsx';
import { FabrikThreeMap } from '../components/FabrikThreeMap.jsx';

function formatNumber(value) {
  if (value === undefined || value === null) {
    return '—';
  }

  return new Intl.NumberFormat('es-ES').format(value);
}

function pressureLabel(level) {
  const labels = {
    critical: 'Crítico',
    high: 'Alto',
    medium: 'Medio',
    low: 'Bajo',
    calm: 'Tranquilo',
  };

  return labels[level] ?? level ?? '—';
}

function dataStatusLabel(roomRisk) {
  if (!roomRisk) {
    return 'Cargando simulación';
  }

  return roomRisk.official_timetable_available
    ? 'Timetable oficial importado'
    : 'Simulación teórica · sin horarios oficiales';
}

function selectedRoomFallback(rooms, selectedSlug) {
  return rooms.find((room) => room.slug === selectedSlug) ?? rooms[0] ?? null;
}

function shortTimeLabel(label = '') {
  return label.split(' · ')[0] || label;
}

function buildTimeBands(heatmap) {
  const timeBands = new Map();

  heatmap.forEach((cell) => {
    if (cell?.time_band && !timeBands.has(cell.time_band)) {
      timeBands.set(cell.time_band, {
        key: cell.time_band,
        label: cell.label ?? cell.time_band,
      });
    }
  });

  return [...timeBands.values()];
}

function findHeatmapCell(heatmap, roomSlug, selectedTimeBand) {
  return heatmap.find((cell) => cell.room_slug === roomSlug && cell.time_band === selectedTimeBand) ?? null;
}

function applyTimeBandToRoom(room, heatmap, selectedTimeBand) {
  const cell = findHeatmapCell(heatmap, room.slug, selectedTimeBand);

  if (!cell) {
    return room;
  }

  const hourlyScore = Number(cell.score ?? room.room_pressure_score ?? 0);
  const capacity = Number(room.estimated_capacity ?? 0);

  return {
    ...room,
    room_pressure_score: hourlyScore,
    pressure_level: cell.pressure_level ?? room.pressure_level,
    simulated_expected_peak: capacity ? Math.round((capacity * hourlyScore) / 100) : room.simulated_expected_peak,
    selected_time_band: cell.time_band,
    selected_time_label: cell.label,
    selected_time_data_status: cell.data_status,
  };
}

function resolveSelectedTimeBand(timeBands, selectedTimeBand) {
  if (timeBands.some((band) => band.key === selectedTimeBand)) {
    return selectedTimeBand;
  }

  return timeBands[0]?.key ?? '';
}

function TimeBandFilter({ timeBands, selectedTimeBand, onChange }) {
  if (!timeBands.length) {
    return null;
  }

  return (
    <ShellCard
      eyebrow="Filtro por hora"
      title="Saturación por franja horaria"
      description="Los colores del mapa cambian con la hora seleccionada. Mientras no haya timetable oficial, estos valores siguen siendo una simulación honesta."
    >
      <div className="time-band-filter" role="tablist" aria-label="Seleccionar franja horaria">
        {timeBands.map((band) => {
          const isActive = band.key === selectedTimeBand;

          return (
            <button
              key={band.key}
              type="button"
              className={isActive ? 'time-band-button time-band-button-active' : 'time-band-button'}
              onClick={() => onChange(band.key)}
              aria-pressed={isActive}
            >
              <Clock3 size={15} />
              <span>{shortTimeLabel(band.label)}</span>
              <small>{band.label.includes('·') ? band.label.split('·')[1].trim() : 'simulación'}</small>
            </button>
          );
        })}
      </div>
    </ShellCard>
  );
}

function Heatmap({ heatmap, rooms, selectedTimeBand, onTimeBandChange }) {
  const roomOrder = rooms.map((room) => room.slug);
  const bands = [...new Map(heatmap.map((cell) => [cell.time_band, cell.label])).entries()];
  const cellsByKey = new Map(heatmap.map((cell) => [`${cell.room_slug}-${cell.time_band}`, cell]));

  if (!heatmap.length || !rooms.length) {
    return <EmptyPanel title="Heatmap pendiente" message="No hay datos suficientes para el heatmap de salas." />;
  }

  return (
    <div className="room-heatmap" style={{ '--heatmap-columns': bands.length }}>
      <div className="heatmap-header heatmap-room-label">Sala</div>
      {bands.map(([band, label]) => (
        <button
          key={band}
          type="button"
          className={band === selectedTimeBand ? 'heatmap-header heatmap-band-active' : 'heatmap-header'}
          onClick={() => onTimeBandChange(band)}
        >
          {shortTimeLabel(label)}
        </button>
      ))}

      {roomOrder.map((roomSlug) => {
        const room = rooms.find((item) => item.slug === roomSlug);
        return [
          <div key={`${roomSlug}-label`} className="heatmap-room-label">{room?.name ?? roomSlug}</div>,
          ...bands.map(([band]) => {
            const cell = cellsByKey.get(`${roomSlug}-${band}`);
            return (
              <button
                key={`${roomSlug}-${band}`}
                type="button"
                className={band === selectedTimeBand ? 'heatmap-cell heatmap-cell-active' : 'heatmap-cell'}
                data-pressure={cell?.pressure_level ?? 'calm'}
                onClick={() => onTimeBandChange(band)}
              >
                <strong>{Math.round(cell?.score ?? 0)}%</strong>
                <span>{pressureLabel(cell?.pressure_level)}</span>
              </button>
            );
          }),
        ];
      })}
    </div>
  );
}

export function RoomRisk({ roomRisk, isLoading, error, selectedYear, availableYears, onYearChange }) {
  const [selectedRoomSlug, setSelectedRoomSlug] = useState('main-room');
  const [selectedTimeBand, setSelectedTimeBand] = useState('00-03');

  const rawRooms = roomRisk?.rooms ?? [];
  const heatmap = roomRisk?.heatmap ?? [];
  const supportAreas = roomRisk?.venue_support_areas ?? [];
  const timeBands = useMemo(() => buildTimeBands(heatmap), [heatmap]);
  const activeTimeBand = resolveSelectedTimeBand(timeBands, selectedTimeBand);
  const activeTimeLabel = timeBands.find((band) => band.key === activeTimeBand)?.label ?? 'Pico simulado';
  const rooms = useMemo(
    () => rawRooms.map((room) => applyTimeBandToRoom(room, heatmap, activeTimeBand)),
    [activeTimeBand, heatmap, rawRooms],
  );
  const selectedRoom = useMemo(() => selectedRoomFallback(rooms, selectedRoomSlug), [rooms, selectedRoomSlug]);
  const topRisk = useMemo(
    () => [...rooms].sort((a, b) => (b.room_pressure_score ?? 0) - (a.room_pressure_score ?? 0))[0],
    [rooms],
  );
  const totalCapacity = rawRooms.reduce((total, room) => total + (room.estimated_capacity ?? 0), 0);

  function handleTimeBandChange(nextBand) {
    setSelectedTimeBand(nextBand);
  }

  return (
    <div className="page-stack">
      <section className="hero-panel room-risk-hero">
        <div className="hero-panel-copy">
          <span className="shell-kicker">Bloque 8 · Salas · Timetable · Saturación</span>
          <h1>Mapa 3D profesional y saturación por hora.</h1>
          <p>
            Visor Three.js con el mapa real como textura y las áreas de cada sala como zonas interactivas. Cambia la franja horaria para ver cómo varía la presión simulada.
          </p>
        </div>
        <div className="status-card room-status-card">
          <MapIcon size={22} />
          <strong>{dataStatusLabel(roomRisk)}</strong>
          <span>{roomRisk?.mode ?? 'theoretical_simulation'}</span>
        </div>
      </section>

      <EditionSelector years={availableYears} selectedYear={selectedYear} onYearChange={onYearChange} />

      {error ? (
        <EmptyPanel title="No se pudo cargar el riesgo por salas" message={error} />
      ) : null}

      <section className="metric-grid">
        <MetricCard icon={Route} label="Salas modeladas" value={formatNumber(rawRooms.length)} description="Hotel excluido del cálculo" />
        <MetricCard icon={UsersRound} label="Capacidad estimada total" value={formatNumber(totalCapacity)} description="Suma editable de salas" tone="accent" />
        <MetricCard icon={AlertTriangle} label="Mayor riesgo ahora" value={topRisk?.name ?? '—'} description={topRisk ? `${Math.round(topRisk.room_pressure_score)}% · ${pressureLabel(topRisk.pressure_level)} · ${shortTimeLabel(activeTimeLabel)}` : 'Pendiente'} />
        <MetricCard icon={Database} label="Timetable oficial" value={roomRisk?.official_timetable_available ? 'Sí' : 'No'} description="Preparado para importar slots" />
      </section>

      <TimeBandFilter timeBands={timeBands} selectedTimeBand={activeTimeBand} onChange={handleTimeBandChange} />

      <section className="room-risk-grid">
        <ShellCard
          eyebrow="Mapa"
          title="Recinto Fabrik · áreas 3D interactivas"
          description="Mapa real embebido en base64. Las propias áreas de las salas son interactivas y cambian de color según la saturación de la hora seleccionada."
          className="map-card"
        >
          {isLoading ? (
            <EmptyPanel title="Cargando mapa" message="Leyendo capacidades y predicciones del backend." />
          ) : rooms.length > 0 ? (
            <FabrikThreeMap
              rooms={rooms}
              supportAreas={supportAreas}
              selectedRoom={selectedRoom}
              selectedTimeLabel={shortTimeLabel(activeTimeLabel)}
              onSelectRoom={setSelectedRoomSlug}
            />
          ) : (
            <EmptyPanel title="Sin salas" message="El endpoint de room-risk todavía no devuelve salas." />
          )}
        </ShellCard>

        <ShellCard
          eyebrow="Sala seleccionada"
          title={selectedRoom?.name ?? 'Selecciona una sala'}
          description={`Lectura para ${shortTimeLabel(activeTimeLabel)}. room_pressure_score cambia según la franja horaria.`}
        >
          {selectedRoom ? (
            <div className="selected-room-panel">
              <RoomCapacityCard room={selectedRoom} isSelected onSelect={setSelectedRoomSlug} />

              <div className="room-detail-list">
                <div><span>Capacidad baja</span><strong>{formatNumber(selectedRoom.min_capacity)}</strong></div>
                <div><span>Capacidad estimada</span><strong>{formatNumber(selectedRoom.estimated_capacity)}</strong></div>
                <div><span>Capacidad alta</span><strong>{formatNumber(selectedRoom.max_capacity)}</strong></div>
                <div><span>Pico en franja</span><strong>{formatNumber(selectedRoom.simulated_expected_peak)}</strong></div>
              </div>

              <div className="room-time-note">
                <Clock3 size={16} />
                <div>
                  <strong>{shortTimeLabel(selectedRoom.selected_time_label ?? activeTimeLabel)}</strong>
                  <span>{selectedRoom.selected_time_data_status === 'official_timetable' ? 'Calculado desde timetable oficial.' : 'Simulación teórica hasta importar horarios oficiales.'}</span>
                </div>
              </div>

              <div className="room-artist-list">
                <span className="mini-section-title">Artistas que más presión podrían generar</span>
                {selectedRoom.top_candidate_artists.length > 0 ? selectedRoom.top_candidate_artists.slice(0, 5).map((artist) => (
                  <div key={artist.slug} className="room-artist-row">
                    <span>#{artist.rank ?? '—'}</span>
                    <strong>{artist.name}</strong>
                    <small>{artist.main_genre} · {Math.round(artist.demand_score)} pts</small>
                  </div>
                )) : <p className="muted-copy">No hay artistas candidatos para esta sala.</p>}
              </div>
            </div>
          ) : (
            <EmptyPanel title="Sin sala seleccionada" message="Elige una sala del mapa para ver detalle." />
          )}
        </ShellCard>
      </section>

      <ShellCard
        eyebrow="Heatmap"
        title="Riesgo por sala y franja"
        description="Pulsa cualquier columna para cambiar la hora del mapa. Ahora es teórico; cuando haya timetable oficial se recalculará por solapes reales."
      >
        <Heatmap heatmap={heatmap} rooms={rawRooms} selectedTimeBand={activeTimeBand} onTimeBandChange={handleTimeBandChange} />
      </ShellCard>

      <ShellCard
        eyebrow="Preparado para horarios oficiales"
        title="Contrato de importación de timetable 2026"
        description="El JSON backend/app/data/timetables/2026.json ya define la estructura esperada."
      >
        <div className="timetable-status-grid">
          <div>
            <Clock3 size={18} />
            <strong>{roomRisk?.timetable?.official_available ? 'Horarios importados' : 'Horarios pendientes'}</strong>
            <p>{roomRisk?.timetable?.notes?.[0] ?? 'Aún no hay horarios oficiales publicados.'}</p>
          </div>
          <div>
            <Radar size={18} />
            <strong>Campos esperados</strong>
            <p>room_slug, room_name, start_time, end_time, artist_slugs, artist_names, source_status.</p>
          </div>
          <div>
            <Sparkles size={18} />
            <strong>Modo honesto</strong>
            <p>La UI etiqueta claramente si los datos son simulados o proceden de un timetable oficial.</p>
          </div>
        </div>
      </ShellCard>

      <ShellCard eyebrow="Salas" title="Todas las salas modeladas" description={`Cards rápidas para revisar presión y capacidad en ${shortTimeLabel(activeTimeLabel)}.`}>
        <div className="room-card-grid">
          {rooms.map((room) => (
            <RoomCapacityCard
              key={room.slug}
              room={room}
              isSelected={selectedRoom?.slug === room.slug}
              onSelect={setSelectedRoomSlug}
            />
          ))}
        </div>
      </ShellCard>
    </div>
  );
}
