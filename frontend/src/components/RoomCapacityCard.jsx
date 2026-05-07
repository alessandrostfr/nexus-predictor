import { AlertTriangle, Gauge, MapPin, UsersRound } from 'lucide-react';

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

// One room card used by the map and the room list. It keeps simulation labels visible.
export function RoomCapacityCard({ room, isSelected = false, onSelect }) {
  if (!room) {
    return null;
  }

  return (
    <button
      type="button"
      className={isSelected ? 'room-card room-card-active' : 'room-card'}
      data-pressure={room.pressure_level}
      onClick={() => onSelect(room.slug)}
    >
      <div className="room-card-header">
        <span className="room-icon"><MapPin size={17} /></span>
        <div>
          <strong>{room.name}</strong>
          <small>{room.area_type} · {room.capacity_confidence}</small>
        </div>
      </div>

      <div className="room-card-metrics">
        <span>
          <UsersRound size={15} />
          {formatNumber(room.estimated_capacity)} cap.
        </span>
        <span>
          <Gauge size={15} />
          {Math.round(room.room_pressure_score)}%
        </span>
        <span>
          <AlertTriangle size={15} />
          {pressureLabel(room.pressure_level)}
        </span>
      </div>

      <div className="room-card-progress" aria-label={`Pressure ${room.room_pressure_score}%`}>
        <span style={{ width: `${Math.min(100, room.room_pressure_score ?? 0)}%` }} />
      </div>

      <p>{room.suggested_use}</p>
    </button>
  );
}
