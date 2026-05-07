'use client';

import { AnimatePresence, motion } from 'framer-motion';
import {
  Activity,
  AlertTriangle,
  ArrowLeft,
  BarChart3,
  CalendarClock,
  Clock3,
  Database,
  Flame,
  Gauge,
  Layers3,
  Map as MapIcon,
  Music2,
  Radio,
  RefreshCcw,
  Search,
  ShieldCheck,
  Sparkles,
  Timer,
  TrendingUp,
  Users,
  Zap,
} from 'lucide-react';
import { useEffect, useMemo, useState } from 'react';
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Line,
  LineChart as RechartsLineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';
import {
  api,
  type DemandArtist,
  type OptimizedComparison,
  type OptimizedVariant,
  type SlotList,
  type TimetableSlot,
} from '@/api/client';
import { number, normalizedPercent, percent, score, title } from '@/lib/format';
import { MetricCard } from './MetricCard';
import { EmptyPanel, ErrorPanel, LoadingPanel } from './StatePanels';
import { StatusPill } from './StatusPill';

type MainView = 'dashboard' | 'ranking' | 'rooms' | 'timetables' | 'artist';
type MenuView = Exclude<MainView, 'artist'>;
type ScheduleKey = 'probable' | 'anti_crowding_extreme' | 'balanced' | 'fan_experience';

type DashboardState = {
  health: Awaited<ReturnType<typeof api.health>> | null;
  evidence: Awaited<ReturnType<typeof api.evidenceCoverage>> | null;
  genres: Awaited<ReturnType<typeof api.genreCoverage>> | null;
  demand: Awaited<ReturnType<typeof api.demandCoverage>> | null;
  artists: DemandArtist[];
  probable: Awaited<ReturnType<typeof api.probableCoverage>> | null;
  probableSlots: SlotList | null;
  optimized: OptimizedComparison | null;
  optimizedSlots: Partial<Record<ScheduleKey, SlotList>>;
  social: Awaited<ReturnType<typeof api.socialStatus>> | null;
};

type RoomPressure = {
  room: string;
  slug: string;
  avgPressure: number;
  maxPressure: number;
  highRiskSlots: number;
  totalSlots: number;
  peakArtist: string;
  peakTime: string;
  capacity?: number | null;
};

type TimePressure = {
  room: string;
  time: string;
  pressure: number;
  rawPressure: number;
  artist: string;
  slot?: TimetableSlot;
};

const initialState: DashboardState = {
  health: null,
  evidence: null,
  genres: null,
  demand: null,
  artists: [],
  probable: null,
  probableSlots: null,
  optimized: null,
  optimizedSlots: {},
  social: null,
};

const menu: Array<{ key: MenuView; label: string; icon: typeof Activity }> = [
  { key: 'dashboard', label: 'Dashboard', icon: Activity },
  { key: 'ranking', label: 'Ranking', icon: Gauge },
  { key: 'rooms', label: 'Salas', icon: MapIcon },
  { key: 'timetables', label: 'Horarios', icon: CalendarClock },
];

const scheduleLabels: Record<ScheduleKey, string> = {
  probable: 'Probable 2026',
  anti_crowding_extreme: 'A · Anti-aglomeración',
  balanced: 'B · Equilibrado',
  fan_experience: 'C · Experiencia fan',
};

const roomBlueprint = [
  { slug: 'main-room', name: 'Main Room', x: 45, y: 24, size: 'xl' },
  { slug: 'open-air', name: 'Open Air', x: 70, y: 40, size: 'lg' },
  { slug: 'hangar', name: 'Hangar', x: 28, y: 46, size: 'lg' },
  { slug: 'area-19', name: 'Area 19', x: 20, y: 72, size: 'md' },
  { slug: 'satelite', name: 'Satelite', x: 53, y: 66, size: 'md' },
  { slug: 'club-area', name: 'Club Area', x: 82, y: 68, size: 'sm' },
  { slug: 'crystal-area', name: 'Crystal Area', x: 68, y: 82, size: 'sm' },
];

function clamp(value: number, min = 0, max = 100) {
  return Math.max(min, Math.min(max, value));
}

function pressureFromSlot(slot: TimetableSlot) {
  // V2.8/V2.9 pressure can reach 140 in extreme-capacity scenarios. The UI
  // normalizes that to a 0-100 risk percentage while preserving raw score in details.
  const raw = slot.expected_pressure_score ?? slot.crowding_score ?? slot.demand_score ?? 0;
  return clamp((raw / 140) * 100);
}

function riskTone(value: number) {
  if (value >= 78) return 'critical';
  if (value >= 58) return 'high';
  if (value >= 36) return 'medium';
  return 'low';
}

function scheduleSlotsFor(data: DashboardState, schedule: ScheduleKey) {
  if (schedule === 'probable') return data.probableSlots?.items ?? [];
  return data.optimizedSlots[schedule]?.items ?? [];
}

function aggregateRoomPressure(slots: TimetableSlot[]): RoomPressure[] {
  const grouped = new globalThis.Map<string, TimetableSlot[]>();

  for (const slot of slots) {
    const key = slot.room_slug || slot.room_name;
    grouped.set(key, [...(grouped.get(key) ?? []), slot]);
  }

  return Array.from(grouped.entries())
    .map(([slug, roomSlots]) => {
      const pressures = roomSlots.map(pressureFromSlot);
      const rawPressures = roomSlots.map((slot) => slot.expected_pressure_score ?? slot.crowding_score ?? slot.demand_score ?? 0);
      const maxIndex = rawPressures.indexOf(Math.max(...rawPressures));
      const peak = roomSlots[maxIndex] ?? roomSlots[0];
      return {
        slug,
        room: peak?.room_name ?? slug,
        avgPressure: pressures.reduce((sum, value) => sum + value, 0) / Math.max(1, pressures.length),
        maxPressure: rawPressures[maxIndex] ?? 0,
        highRiskSlots: roomSlots.filter((slot) => pressureFromSlot(slot) >= 58 || ['high', 'very_high', 'critical'].includes(slot.crowd_risk ?? '')).length,
        totalSlots: roomSlots.length,
        peakArtist: peak?.artist_name ?? 'Sin artista',
        peakTime: peak ? `${title(peak.event_day)} · ${peak.start_time}` : '—',
        capacity: peak?.room_capacity,
      };
    })
    .sort((a, b) => b.avgPressure - a.avgPressure);
}

function buildTimeMatrix(slots: TimetableSlot[], selectedRoom: string) {
  const filtered = selectedRoom === 'all' ? slots : slots.filter((slot) => slot.room_slug === selectedRoom || slot.room_name === selectedRoom);
  return filtered
    .map((slot) => ({
      room: slot.room_name,
      time: slot.start_time,
      pressure: pressureFromSlot(slot),
      rawPressure: slot.expected_pressure_score ?? slot.crowding_score ?? slot.demand_score ?? 0,
      artist: slot.artist_name,
      slot,
    }))
    .sort((a, b) => (a.slot?.start_minutes ?? 0) - (b.slot?.start_minutes ?? 0) || a.room.localeCompare(b.room));
}

export function NexusDashboard() {
  const [activeView, setActiveView] = useState<MainView>('dashboard');
  const [selectedSchedule, setSelectedSchedule] = useState<ScheduleKey>('fan_experience');
  const [selectedRoom, setSelectedRoom] = useState('all');
  const [selectedDay, setSelectedDay] = useState('all');
  const [query, setQuery] = useState('');
  const [genre, setGenre] = useState('all');
  const [selectedArtistSlug, setSelectedArtistSlug] = useState('');
  const [data, setData] = useState<DashboardState>(initialState);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  async function loadDashboard() {
    setLoading(true);
    setError(null);

    try {
      // Requests are client-side so `next build` stays independent from the backend.
      const [health, evidence, genres, demand, artistList, probable, probableSlots, optimized, social] = await Promise.all([
        api.health(),
        api.evidenceCoverage(),
        api.genreCoverage(),
        api.demandCoverage(2026),
        api.demandArtists(2026, 100),
        api.probableCoverage(2026),
        api.probableSlots(2026, 220),
        api.optimizedCompare(2026),
        api.socialStatus(),
      ]);

      const optimizedEntries = await Promise.all(
        optimized.variants.map(async (variant) => {
          const slots = await api.optimizedVariantSlots(2026, variant.variant_key, 220);
          return [variant.variant_key as ScheduleKey, slots] as const;
        }),
      );

      setData({
        health,
        evidence,
        genres,
        demand,
        artists: artistList.items ?? [],
        probable,
        probableSlots,
        optimized,
        optimizedSlots: Object.fromEntries(optimizedEntries) as Partial<Record<ScheduleKey, SlotList>>,
        social,
      });

      if (!selectedArtistSlug && artistList.items?.[0]?.artist_slug) {
        setSelectedArtistSlug(artistList.items[0].artist_slug);
      }
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : 'No se pudo conectar con la API.');
      setData(initialState);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void loadDashboard();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const scenarioSlots = useMemo(() => scheduleSlotsFor(data, selectedSchedule), [data, selectedSchedule]);
  const probableSlots = data.probableSlots?.items ?? [];

  const roomPressure = useMemo(() => aggregateRoomPressure(scenarioSlots), [scenarioSlots]);
  const topRiskRoom = roomPressure[0];

  const roomOptions = useMemo(() => {
    const rooms = new globalThis.Map<string, string>();
    scenarioSlots.forEach((slot) => rooms.set(slot.room_slug, slot.room_name));
    return Array.from(rooms.entries()).map(([slug, name]) => ({ slug, name })).sort((a, b) => a.name.localeCompare(b.name));
  }, [scenarioSlots]);

  const timeMatrix = useMemo(() => buildTimeMatrix(scenarioSlots, selectedRoom), [scenarioSlots, selectedRoom]);

  const selectedVariant = useMemo(() => data.optimized?.variants.find((item) => item.variant_key === selectedSchedule), [data.optimized, selectedSchedule]);

  const selectedArtist = useMemo(
    () => data.artists.find((artist) => artist.artist_slug === selectedArtistSlug) ?? data.artists[0],
    [data.artists, selectedArtistSlug],
  );

  const genres = useMemo(() => {
    const values = new Set<string>();
    data.artists.forEach((artist) => {
      if (artist.main_genre) values.add(artist.main_genre);
    });
    return Array.from(values).sort((a, b) => a.localeCompare(b));
  }, [data.artists]);

  const filteredArtists = useMemo(() => {
    const normalizedQuery = query.trim().toLowerCase();
    return data.artists.filter((artist) => {
      const matchesQuery = !normalizedQuery || artist.artist_name.toLowerCase().includes(normalizedQuery) || artist.artist_slug.includes(normalizedQuery);
      const matchesGenre = genre === 'all' || artist.main_genre === genre;
      return matchesQuery && matchesGenre;
    });
  }, [data.artists, query, genre]);

  const scheduleList = useMemo(() => {
    const base = selectedSchedule === 'probable' ? probableSlots : scenarioSlots;
    return base.filter((slot) => selectedDay === 'all' || slot.event_day === selectedDay);
  }, [probableSlots, scenarioSlots, selectedDay, selectedSchedule]);

  const selectedArtistSlots = useMemo(() => {
    if (!selectedArtist) return [];
    const allSlots = [
      ...probableSlots.map((slot) => ({ ...slot, variant_key: 'probable', variant_name: 'Probable 2026' })),
      ...Object.entries(data.optimizedSlots).flatMap(([variantKey, list]) =>
        (list?.items ?? []).map((slot) => ({ ...slot, variant_key: variantKey, variant_name: scheduleLabels[variantKey as ScheduleKey] })),
      ),
    ];
    return allSlots.filter((slot) => slot.artist_slug === selectedArtist.artist_slug);
  }, [data.optimizedSlots, probableSlots, selectedArtist]);

  const demandChart = useMemo(
    () =>
      data.artists.slice(0, 9).map((artist) => ({
        name: artist.artist_name,
        score: artist.demand_score ?? 0,
      })),
    [data.artists],
  );

  const isApiOk = data.health?.status === 'ok';

  function openArtist(artist: DemandArtist) {
    setSelectedArtistSlug(artist.artist_slug);
    setActiveView('artist');
  }

  return (
    <main className="app-shell">
      <header className="topbar">
        <button className="brand" type="button" onClick={() => setActiveView('dashboard')}>
          <div className="brand-mark">
            <Radio size={22} />
          </div>
          <div>
            <h1>Nexus Predictor V2</h1>
            <p>Fabrik Madrid · cyberpunk festival intelligence</p>
          </div>
        </button>

        <nav className="main-nav" aria-label="Secciones principales">
          {menu.map((item) => {
            const Icon = item.icon;
            return (
              <button key={item.key} className={activeView === item.key ? 'main-nav-item active' : 'main-nav-item'} onClick={() => setActiveView(item.key)}>
                <Icon size={16} />
                {item.label}
              </button>
            );
          })}
        </nav>

        <div className="api-indicator" title={isApiOk ? 'Backend conectado' : 'Backend pendiente'}>
          <i className={isApiOk ? 'api-dot ok' : 'api-dot'} />
          <span>{isApiOk ? 'API conectada' : 'API pendiente'}</span>
        </div>
      </header>

      {error ? <ErrorPanel message={error} /> : null}
      {loading ? <LoadingPanel label="Cargando demanda, evidencias, horarios y optimizador V2..." /> : null}

      <AnimatePresence mode="wait">
        {!loading && !error ? (
          <motion.div key={activeView} initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -12 }}>
            {activeView === 'dashboard' ? (
              <DashboardView
                data={data}
                topRiskRoom={topRiskRoom}
                roomPressure={roomPressure}
                demandChart={demandChart}
                selectedVariant={selectedVariant}
                setActiveView={setActiveView}
                openArtist={openArtist}
                refresh={loadDashboard}
              />
            ) : null}

            {activeView === 'ranking' ? (
              <RankingView
                artists={filteredArtists}
                allGenres={genres}
                query={query}
                setQuery={setQuery}
                genre={genre}
                setGenre={setGenre}
                openArtist={openArtist}
              />
            ) : null}

            {activeView === 'rooms' ? (
              <RoomsView
                selectedSchedule={selectedSchedule}
                setSelectedSchedule={setSelectedSchedule}
                roomPressure={roomPressure}
                timeMatrix={timeMatrix}
                roomOptions={roomOptions}
                selectedRoom={selectedRoom}
                setSelectedRoom={setSelectedRoom}
                topRiskRoom={topRiskRoom}
              />
            ) : null}

            {activeView === 'timetables' ? (
              <TimetablesView
                selectedSchedule={selectedSchedule}
                setSelectedSchedule={setSelectedSchedule}
                selectedDay={selectedDay}
                setSelectedDay={setSelectedDay}
                scheduleList={scheduleList}
                optimized={data.optimized}
                probable={data.probable}
                selectedVariant={selectedVariant}
              />
            ) : null}

            {activeView === 'artist' && selectedArtist ? (
              <ArtistDetailView artist={selectedArtist} artistSlots={selectedArtistSlots} back={() => setActiveView('ranking')} />
            ) : null}
          </motion.div>
        ) : null}
      </AnimatePresence>

      <nav className="bottom-nav" aria-label="Navegación móvil">
        {menu.map((item) => {
          const Icon = item.icon;
          return (
            <button key={item.key} className={activeView === item.key ? 'active' : ''} onClick={() => setActiveView(item.key)}>
              <Icon size={18} />
              {item.label}
            </button>
          );
        })}
      </nav>
    </main>
  );
}

function DashboardView({
  data,
  topRiskRoom,
  roomPressure,
  demandChart,
  selectedVariant,
  setActiveView,
  openArtist,
  refresh,
}: {
  data: DashboardState;
  topRiskRoom: RoomPressure | undefined;
  roomPressure: RoomPressure[];
  demandChart: Array<{ name: string; score: number }>;
  selectedVariant: OptimizedVariant | undefined;
  setActiveView: (view: MainView) => void;
  openArtist: (artist: DemandArtist) => void;
  refresh: () => Promise<void>;
}) {
  return (
    <>
      <section className="hero mvp-hero">
        <motion.div className="hero-panel" initial={{ opacity: 0, y: 18 }} animate={{ opacity: 1, y: 0 }}>
          <div className="kicker">
            <Sparkles size={15} /> V2.10 · estructura MVP, motor V2
          </div>
          <h2>
            Nexus 2026 leído por <span className="hero-gradient">datos, presión y energía.</span>
          </h2>
          <p className="hero-copy">
            Dashboard premium inspirado en el MVP, pero alimentado por la capa V2: evidencias, subgéneros, demanda,
            horarios probables y tres variantes optimizadas no oficiales.
          </p>
          <div className="hero-actions">
            <button className="pill-button primary" onClick={() => setActiveView('ranking')}>
              <Gauge size={17} /> Ver ranking
            </button>
            <button className="pill-button" onClick={() => setActiveView('rooms')}>
              <MapIcon size={17} /> Riesgo por sala
            </button>
            <button className="pill-button" onClick={() => void refresh()}>
              <RefreshCcw size={17} /> Refrescar API
            </button>
          </div>
        </motion.div>

        <aside className="hero-side-grid">
          <MetricCard icon={Users} label="Artistas 2026" value={number(data.demand?.total_artists)} note="Predicciones V2 persistidas" tone="cyan" />
          <MetricCard icon={Database} label="Evidencias" value={number(data.evidence?.evidence_items)} note="Fuente, confianza y trazabilidad" tone="violet" />
          <MetricCard icon={CalendarClock} label="Slots probables" value={number(data.probable?.total_slots)} note="Horario predictivo no oficial" tone="acid" />
          <MetricCard icon={Layers3} label="Variantes" value={number(data.optimized?.variants.length)} note="A/B/C optimizadas con OR-Tools" tone="pink" />
        </aside>
      </section>

      <section className="dashboard-layout">
        <article className="card edition-card">
          <div className="card-header">
            <div>
              <small>Edición activa</small>
              <h3 className="card-title">Nexus Festival 2026</h3>
            </div>
            <StatusPill tone="warning">Predicción no oficial</StatusPill>
          </div>
          <div className="edition-meter">
            <div>
              <strong>{score(data.demand?.average_demand_score)}</strong>
              <span>demanda media</span>
            </div>
            <div>
              <strong>{number(data.probable?.total_rooms)}</strong>
              <span>salas reales</span>
            </div>
            <div>
              <strong>{number(data.demand?.artists_with_historical_timetable)}</strong>
              <span>con histórico</span>
            </div>
          </div>
          <p className="muted-copy">
            La UI diferencia estimación, inferencia y dato oficial. El horario oficial de Nexus/Fabrik todavía no está
            disponible, por eso los horarios se muestran como escenarios predictivos.
          </p>
        </article>

        <article className="card ranking-preview">
          <div className="card-header">
            <div>
              <small>Top demanda V2</small>
              <h3 className="card-title">Artistas principales</h3>
            </div>
            <button className="ghost-link" onClick={() => setActiveView('ranking')}>Ver ranking</button>
          </div>
          <div className="artist-stack compact">
            {data.artists.slice(0, 5).map((artist) => (
              <button key={artist.artist_slug} className="artist-row" onClick={() => openArtist(artist)}>
                <span className="rank-pill">#{artist.rank ?? '—'}</span>
                <span className="artist-row-main">
                  <strong>{artist.artist_name}</strong>
                  <small>{artist.main_genre ?? 'Unknown'} · {title(artist.confidence)}</small>
                </span>
                <span className="badge acid">{score(artist.demand_score)}</span>
              </button>
            ))}
          </div>
        </article>

        <article className="card chart-card">
          <div className="card-header">
            <div>
              <small>Curva de demanda</small>
              <h3 className="card-title">Top 9 por score</h3>
            </div>
            <StatusPill tone="ok">V2.7</StatusPill>
          </div>
          {demandChart.length ? <DemandLine data={demandChart} /> : <EmptyPanel />}
        </article>

        <article className="card model-card">
          <div className="card-header">
            <div>
              <small>Modelo y fuentes</small>
              <h3 className="card-title">Cobertura V2</h3>
            </div>
            <StatusPill>evidence weighted</StatusPill>
          </div>
          <div className="signal-grid">
            <Signal label="Spotify" value={number(data.demand?.artists_with_spotify)} />
            <Signal label="Social/platform" value={number(data.demand?.artists_with_social_or_platform_metrics)} />
            <Signal label="Career signals" value={number(data.demand?.artists_with_career_signals)} />
            <Signal label="Unknown rate" value={percent(data.genres?.unknown_rate)} />
          </div>
        </article>

        <article className="card room-preview">
          <div className="card-header">
            <div>
              <small>Riesgo por sala</small>
              <h3 className="card-title">Presión estimada del modelo</h3>
            </div>
            <button className="ghost-link" onClick={() => setActiveView('rooms')}>Ver salas</button>
          </div>
          <RoomRiskList rooms={roomPressure.slice(0, 4)} />
        </article>

        <article className="card timetable-preview">
          <div className="card-header">
            <div>
              <small>Horarios</small>
              <h3 className="card-title">Probable + 3 variantes</h3>
            </div>
            <button className="ghost-link" onClick={() => setActiveView('timetables')}>Abrir horarios</button>
          </div>
          <ul className="split-list">
            <li>
              <div className="list-main">
                <strong>{selectedVariant?.variant_name ?? 'Variante fan experience'}</strong>
                <span>{selectedVariant?.variant_description ?? 'Escenario optimizado no oficial.'}</span>
              </div>
              <span className="badge acid">{score(selectedVariant?.average_experience_score)}</span>
            </li>
            <li>
              <div className="list-main">
                <strong>Pico de presión</strong>
                <span>{topRiskRoom?.room ?? 'Sin sala'} · {topRiskRoom?.peakArtist ?? 'Sin artista'}</span>
              </div>
              <span className="badge pink">{score(topRiskRoom?.maxPressure)}</span>
            </li>
          </ul>
        </article>
      </section>
    </>
  );
}

function RankingView({
  artists,
  allGenres,
  query,
  setQuery,
  genre,
  setGenre,
  openArtist,
}: {
  artists: DemandArtist[];
  allGenres: string[];
  query: string;
  setQuery: (query: string) => void;
  genre: string;
  setGenre: (genre: string) => void;
  openArtist: (artist: DemandArtist) => void;
}) {
  return (
    <section className="page-block">
      <PageHero
        eyebrow="Ranking"
        title="Ranking predictivo de demanda"
        copy="La estructura vuelve a ser directa como en el MVP, pero cada fila conserva los factores V2: popularidad, carrera, momentum, afinidad Nexus, confianza y fallback."
        icon={Gauge}
      />

      <div className="toolbar-card">
        <label className="search-box">
          <Search size={16} />
          <input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Buscar artista, slug o show..." />
        </label>
        <select className="select-control" value={genre} onChange={(event) => setGenre(event.target.value)}>
          <option value="all">Todos los géneros</option>
          {allGenres.map((item) => (
            <option key={item} value={item}>{item}</option>
          ))}
        </select>
      </div>

      <div className="ranking-grid">
        {artists.map((artist) => (
          <button key={artist.artist_slug} className="ranking-card" onClick={() => openArtist(artist)}>
            <div className="ranking-card-top">
              <span className="rank-pill">#{artist.rank ?? '—'}</span>
              <span className={`risk-dot ${riskTone((artist.demand_score ?? 0) / 1.4)}`} />
            </div>
            <h3>{artist.artist_name}</h3>
            <p>{artist.main_genre ?? 'Unknown'} · {title(artist.crowd_risk)}</p>
            <div className="score-track">
              <span style={{ width: `${clamp(artist.demand_score ?? 0)}%` }} />
            </div>
            <div className="score-row">
              <span>Demand</span>
              <strong>{score(artist.demand_score)}</strong>
            </div>
            <div className="mini-factors">
              <span>Pop {score(artist.popularity_score)}</span>
              <span>Career {score(artist.career_score)}</span>
              <span>Momentum {score(artist.momentum_score)}</span>
            </div>
          </button>
        ))}
      </div>
    </section>
  );
}

function RoomsView({
  selectedSchedule,
  setSelectedSchedule,
  roomPressure,
  timeMatrix,
  roomOptions,
  selectedRoom,
  setSelectedRoom,
  topRiskRoom,
}: {
  selectedSchedule: ScheduleKey;
  setSelectedSchedule: (schedule: ScheduleKey) => void;
  roomPressure: RoomPressure[];
  timeMatrix: TimePressure[];
  roomOptions: Array<{ slug: string; name: string }>;
  selectedRoom: string;
  setSelectedRoom: (room: string) => void;
  topRiskRoom: RoomPressure | undefined;
}) {
  return (
    <section className="page-block">
      <PageHero
        eyebrow="Salas"
        title="Mapa de presión por sala y franja"
        copy="La sección mantiene el mapa V2 y calcula los porcentajes desde expected_pressure_score/crowding_score/demand_score del modelo, no desde valores decorativos."
        icon={MapIcon}
      />

      <div className="toolbar-card">
        <select className="select-control" value={selectedSchedule} onChange={(event) => setSelectedSchedule(event.target.value as ScheduleKey)}>
          {Object.entries(scheduleLabels).map(([key, label]) => <option key={key} value={key}>{label}</option>)}
        </select>
        <select className="select-control" value={selectedRoom} onChange={(event) => setSelectedRoom(event.target.value)}>
          <option value="all">Todas las salas</option>
          {roomOptions.map((room) => <option key={room.slug} value={room.slug}>{room.name}</option>)}
        </select>
      </div>

      <div className="rooms-layout">
        <article className="card venue-card">
          <div className="card-header">
            <div>
              <small>Fabrik model · 7 salas</small>
              <h3 className="card-title">Mapa Nexus/Fabrik</h3>
            </div>
            <StatusPill tone="warning">Modelo estimado</StatusPill>
          </div>
          <FabrikPressureMap rooms={roomPressure} selectedRoom={selectedRoom} setSelectedRoom={setSelectedRoom} />
        </article>

        <article className="card room-focus-card">
          <div className="card-header">
            <div>
              <small>Sala con mayor presión</small>
              <h3 className="card-title">{topRiskRoom?.room ?? 'Sin datos'}</h3>
            </div>
            <span className={`pressure-badge ${riskTone(topRiskRoom?.avgPressure ?? 0)}`}>{normalizedPercent(topRiskRoom?.avgPressure)}</span>
          </div>
          <ul className="split-list">
            <li><div className="list-main"><strong>Pico bruto</strong><span>expected_pressure_score máximo</span></div><span className="badge pink">{score(topRiskRoom?.maxPressure)}</span></li>
            <li><div className="list-main"><strong>Artista pico</strong><span>{topRiskRoom?.peakTime ?? '—'}</span></div><span className="badge cyan">{topRiskRoom?.peakArtist ?? '—'}</span></li>
            <li><div className="list-main"><strong>Slots de riesgo</strong><span>Franja con presión media/alta</span></div><span className="badge orange">{number(topRiskRoom?.highRiskSlots)}</span></li>
          </ul>
        </article>

        <article className="card room-heatmap-card">
          <div className="card-header">
            <div>
              <small>Heatmap por franja</small>
              <h3 className="card-title">Presión estimada</h3>
            </div>
            <StatusPill>Score normalizado</StatusPill>
          </div>
          <PressureHeatmap matrix={timeMatrix} />
        </article>

        <article className="card room-list-card">
          <div className="card-header">
            <div>
              <small>Ranking de salas</small>
              <h3 className="card-title">Riesgo medio</h3>
            </div>
          </div>
          <RoomRiskList rooms={roomPressure} />
        </article>
      </div>
    </section>
  );
}

function TimetablesView({
  selectedSchedule,
  setSelectedSchedule,
  selectedDay,
  setSelectedDay,
  scheduleList,
  optimized,
  probable,
  selectedVariant,
}: {
  selectedSchedule: ScheduleKey;
  setSelectedSchedule: (schedule: ScheduleKey) => void;
  selectedDay: string;
  setSelectedDay: (day: string) => void;
  scheduleList: TimetableSlot[];
  optimized: OptimizedComparison | null;
  probable: DashboardState['probable'];
  selectedVariant: OptimizedVariant | undefined;
}) {
  const grouped = useMemo(() => groupSlots(scheduleList), [scheduleList]);

  return (
    <section className="page-block">
      <PageHero
        eyebrow="Horarios"
        title="Probable 2026 vs variantes óptimas"
        copy="Ventana dedicada para comparar el horario probable con los tres escenarios optimizados: anti-aglomeración, equilibrado y experiencia fan. Ninguno es oficial hasta que exista fuente verificada."
        icon={CalendarClock}
      />

      <div className="toolbar-card">
        <select className="select-control" value={selectedSchedule} onChange={(event) => setSelectedSchedule(event.target.value as ScheduleKey)}>
          {Object.entries(scheduleLabels).map(([key, label]) => <option key={key} value={key}>{label}</option>)}
        </select>
        <select className="select-control" value={selectedDay} onChange={(event) => setSelectedDay(event.target.value)}>
          <option value="all">Viernes + sábado</option>
          <option value="friday">Viernes</option>
          <option value="saturday">Sábado</option>
        </select>
      </div>

      <div className="timetable-summary-grid">
        <MetricCard icon={CalendarClock} label="Slots visibles" value={number(scheduleList.length)} note="Filtrados por escenario/día" tone="cyan" />
        <MetricCard icon={AlertTriangle} label="High-risk" value={number(selectedVariant?.high_risk_slots ?? 0)} note="Solo variantes optimizadas" tone="pink" />
        <MetricCard icon={Zap} label="Experience" value={score(selectedVariant?.average_experience_score ?? probable?.average_probability_score)} note="Mayor es mejor" tone="acid" />
        <MetricCard icon={ShieldCheck} label="Estado" value="No oficial" note="source_status: no_official_timetable_yet" tone="orange" />
      </div>

      {optimized?.variants?.length ? <VariantComparison variants={optimized.variants} /> : null}

      <div className="schedule-columns">
        {Object.entries(grouped).map(([group, slots]) => (
          <article className="card schedule-column" key={group}>
            <div className="card-header">
              <div>
                <small>{title(slots[0]?.event_day)}</small>
                <h3 className="card-title">{group}</h3>
              </div>
              <span className="badge cyan">{slots.length} slots</span>
            </div>
            <ul className="slot-feed">
              {slots.map((slot) => (
                <li key={`${slot.artist_slug}-${slot.event_day}-${slot.room_slug}-${slot.start_time}`}>
                  <time>{slot.start_time}</time>
                  <div>
                    <strong>{slot.artist_name}</strong>
                    <span>{slot.room_name} · {slot.slot_type ?? 'standard'} · {title(slot.crowd_risk)}</span>
                  </div>
                  <span className={`pressure-badge ${riskTone(pressureFromSlot(slot))}`}>{normalizedPercent(pressureFromSlot(slot))}</span>
                </li>
              ))}
            </ul>
          </article>
        ))}
      </div>
    </section>
  );
}

function ArtistDetailView({ artist, artistSlots, back }: { artist: DemandArtist; artistSlots: TimetableSlot[]; back: () => void }) {
  return (
    <section className="page-block">
      <button className="back-button" onClick={back}><ArrowLeft size={16} /> Volver al ranking</button>
      <div className="artist-detail-hero">
        <div>
          <small>{artist.main_genre ?? 'Unknown'} · #{artist.rank ?? '—'}</small>
          <h2>{artist.artist_name}</h2>
          <p>Ficha rápida conectada al modelo V2: demanda, carrera, momentum, afinidad Nexus, confianza y slots estimados.</p>
          <div className="badge-row">
            {(artist.secondary_genres ?? []).map((item) => <span key={item} className="badge cyan">{item}</span>)}
            <StatusPill tone={artist.fallback_used ? 'warning' : 'ok'}>{artist.fallback_used ? 'Fallback activo' : 'Evidence rich'}</StatusPill>
          </div>
        </div>
        <div className="artist-score-orb">
          <strong>{score(artist.demand_score)}</strong>
          <span>demand score</span>
        </div>
      </div>

      <div className="artist-detail-grid">
        <article className="card">
          <div className="card-header"><div><small>Score breakdown</small><h3 className="card-title">Factores V2.7</h3></div></div>
          <FactorBars artist={artist} />
        </article>
        <article className="card">
          <div className="card-header"><div><small>Explicación</small><h3 className="card-title">Por qué sube o baja</h3></div><StatusPill>{title(artist.confidence)}</StatusPill></div>
          {(artist.explanation ?? []).length ? (
            <ul className="split-list">
              {(artist.explanation ?? []).slice(0, 8).map((item) => <li key={item}><div className="list-main"><strong>{item}</strong></div></li>)}
            </ul>
          ) : <EmptyPanel label="No hay explicación detallada para este artista." />}
        </article>
        <article className="card span-2">
          <div className="card-header"><div><small>Horarios relacionados</small><h3 className="card-title">Slots probables y óptimos</h3></div></div>
          {artistSlots.length ? (
            <ul className="slot-feed compact-feed">
              {artistSlots.slice(0, 8).map((slot) => (
                <li key={`${slot.variant_key}-${slot.artist_slug}-${slot.start_time}`}>
                  <time>{slot.start_time}</time>
                  <div><strong>{slot.variant_name ?? scheduleLabels[(slot.variant_key as ScheduleKey) ?? 'probable']}</strong><span>{title(slot.event_day)} · {slot.room_name}</span></div>
                  <span className={`pressure-badge ${riskTone(pressureFromSlot(slot))}`}>{normalizedPercent(pressureFromSlot(slot))}</span>
                </li>
              ))}
            </ul>
          ) : <EmptyPanel label="Todavía no hay slot asociado para este artista." />}
        </article>
      </div>
    </section>
  );
}

function PageHero({ eyebrow, title: pageTitle, copy, icon: Icon }: { eyebrow: string; title: string; copy: string; icon: typeof Activity }) {
  return (
    <div className="page-hero-card">
      <div className="page-hero-icon"><Icon size={22} /></div>
      <div>
        <small>{eyebrow}</small>
        <h2>{pageTitle}</h2>
        <p>{copy}</p>
      </div>
    </div>
  );
}

function Signal({ label, value }: { label: string; value: string }) {
  return <div className="signal"><span>{label}</span><strong>{value}</strong></div>;
}

function RoomRiskList({ rooms }: { rooms: RoomPressure[] }) {
  if (!rooms.length) return <EmptyPanel label="No hay presión de salas disponible." />;
  return (
    <ul className="split-list room-risk-list">
      {rooms.map((room) => (
        <li key={room.slug}>
          <div className="list-main">
            <strong>{room.room}</strong>
            <span>{room.totalSlots} slots · pico {room.peakArtist} · {room.peakTime}</span>
          </div>
          <span className={`pressure-badge ${riskTone(room.avgPressure)}`}>{normalizedPercent(room.avgPressure)}</span>
        </li>
      ))}
    </ul>
  );
}

function FabrikPressureMap({ rooms, selectedRoom, setSelectedRoom }: { rooms: RoomPressure[]; selectedRoom: string; setSelectedRoom: (room: string) => void }) {
  const bySlug = new globalThis.Map(rooms.map((room) => [room.slug, room] as const));
  return (
    <div className="fabrik-map">
      <div className="map-grid-glow" />
      {roomBlueprint.map((room) => {
        const risk = bySlug.get(room.slug);
        const pressure = risk?.avgPressure ?? 0;
        return (
          <button
            key={room.slug}
            className={`map-room ${room.size} ${riskTone(pressure)} ${selectedRoom === room.slug ? 'selected' : ''}`}
            style={{ left: `${room.x}%`, top: `${room.y}%` }}
            onClick={() => setSelectedRoom(room.slug)}
            title={`${room.name}: ${normalizedPercent(pressure)}`}
          >
            <strong>{room.name}</strong>
            <span>{normalizedPercent(pressure)}</span>
          </button>
        );
      })}
      <div className="map-caption">Presión normalizada desde el modelo V2.8/V2.9 · 7 salas Fabrik</div>
    </div>
  );
}

function PressureHeatmap({ matrix }: { matrix: TimePressure[] }) {
  if (!matrix.length) return <EmptyPanel label="No hay slots para la sala o escenario seleccionado." />;
  return (
    <div className="heatmap-list">
      {matrix.slice(0, 48).map((item) => (
        <div key={`${item.room}-${item.time}-${item.artist}`} className={`heat-cell ${riskTone(item.pressure)}`}>
          <time>{item.time}</time>
          <strong>{item.room}</strong>
          <span>{item.artist}</span>
          <em>{normalizedPercent(item.pressure)} · raw {score(item.rawPressure)}</em>
        </div>
      ))}
    </div>
  );
}

function FactorBars({ artist }: { artist: DemandArtist }) {
  const rows = [
    { label: 'Popularidad', value: artist.popularity_score ?? 0, className: 'cyan' },
    { label: 'Carrera', value: artist.career_score ?? 0, className: 'violet' },
    { label: 'Momentum', value: artist.momentum_score ?? 0, className: 'acid' },
    { label: 'Afinidad Nexus', value: artist.nexus_affinity_score ?? 0, className: 'pink' },
  ];
  return (
    <div className="factor-bars">
      {rows.map((row) => (
        <div key={row.label}>
          <div className="score-row"><span>{row.label}</span><strong>{score(row.value)}</strong></div>
          <div className="score-track"><span className={row.className} style={{ width: `${clamp(row.value)}%` }} /></div>
        </div>
      ))}
    </div>
  );
}

function VariantComparison({ variants }: { variants: OptimizedVariant[] }) {
  const chartData = variants.map((item) => ({
    name: item.variant_key.replaceAll('_', ' '),
    crowding: item.average_crowding_score,
    conflict: item.average_conflict_score,
    experience: item.average_experience_score,
  }));
  return (
    <article className="card variant-comparison-card">
      <div className="card-header">
        <div><small>Comparativa V2.9</small><h3 className="card-title">Crowding · conflict · experience</h3></div>
        <StatusPill tone="ok">3 variantes</StatusPill>
      </div>
      <div className="chart-wrap compact-chart">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={chartData} margin={{ top: 8, right: 8, left: -18, bottom: 18 }}>
            <CartesianGrid stroke="rgba(255,255,255,0.08)" vertical={false} />
            <XAxis dataKey="name" tick={{ fill: '#aeb1ca', fontSize: 11 }} interval={0} angle={-14} textAnchor="end" height={58} />
            <YAxis tick={{ fill: '#aeb1ca', fontSize: 11 }} />
            <Tooltip contentStyle={{ background: '#10111c', border: '1px solid rgba(255,255,255,.16)', borderRadius: 14 }} />
            <Bar dataKey="crowding" fill="#ff3d9a" radius={[8, 8, 0, 0]} />
            <Bar dataKey="conflict" fill="#a95cff" radius={[8, 8, 0, 0]} />
            <Bar dataKey="experience" fill="#d7ff55" radius={[8, 8, 0, 0]} />
          </BarChart>
        </ResponsiveContainer>
      </div>
    </article>
  );
}

function DemandLine({ data }: { data: Array<{ name: string; score: number }> }) {
  return (
    <div className="chart-wrap">
      <ResponsiveContainer width="100%" height="100%">
        <RechartsLineChart data={data} margin={{ top: 8, right: 16, left: -18, bottom: 18 }}>
          <CartesianGrid stroke="rgba(255,255,255,0.08)" vertical={false} />
          <XAxis dataKey="name" tick={{ fill: '#aeb1ca', fontSize: 11 }} interval={0} angle={-18} textAnchor="end" height={56} />
          <YAxis tick={{ fill: '#aeb1ca', fontSize: 11 }} />
          <Tooltip contentStyle={{ background: '#10111c', border: '1px solid rgba(255,255,255,.16)', borderRadius: 14 }} />
          <Line type="monotone" dataKey="score" stroke="#55f7ff" strokeWidth={3} dot={{ r: 3, stroke: '#d7ff55' }} />
        </RechartsLineChart>
      </ResponsiveContainer>
    </div>
  );
}

function groupSlots(slots: TimetableSlot[]) {
  return slots.reduce<Record<string, TimetableSlot[]>>((acc, slot) => {
    const key = `${title(slot.event_day)} · ${slot.room_name}`;
    acc[key] = [...(acc[key] ?? []), slot];
    return acc;
  }, {});
}
