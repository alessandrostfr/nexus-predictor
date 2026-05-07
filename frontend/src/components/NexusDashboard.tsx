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
import type { LucideIcon } from 'lucide-react';
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
  type OptimizedCoverage,
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
type DayFilter = 'all' | 'friday' | 'saturday';

type DashboardState = {
  health: Awaited<ReturnType<typeof api.health>> | null;
  evidence: Awaited<ReturnType<typeof api.evidenceCoverage>> | null;
  genres: Awaited<ReturnType<typeof api.genreCoverage>> | null;
  demand: Awaited<ReturnType<typeof api.demandCoverage>> | null;
  artists: DemandArtist[];
  probable: Awaited<ReturnType<typeof api.probableCoverage>> | null;
  probableSlots: SlotList | null;
  optimizedCoverage: OptimizedCoverage | null;
  optimized: OptimizedComparison | null;
  optimizedSlots: Partial<Record<Exclude<ScheduleKey, 'probable'>, SlotList>>;
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
  headliners: number;
  avgDemand: number;
  avgCrowding: number;
  avgConflict: number;
  avgExperience: number;
  dayBreakdown: Record<string, number>;
};

type TimePressure = {
  room: string;
  slug: string;
  time: string;
  day: string;
  artist: string;
  slotCount: number;
  pressure: number;
  rawPressure: number;
  crowding: number;
  demand: number;
  conflict: number;
  experience: number;
};

type TimelineGroup = {
  key: string;
  label: string;
  day: string;
  room: string;
  slug: string;
  slots: TimetableSlot[];
};

const scheduleLabels: Record<ScheduleKey, string> = {
  probable: 'Horario probable 2026',
  anti_crowding_extreme: 'A · Anti-aglomeraciones extremo',
  balanced: 'B · Equilibrado',
  fan_experience: 'C · Experiencia fan',
};

const variantGoalLabels: Record<Exclude<ScheduleKey, 'probable'>, string> = {
  anti_crowding_extreme: 'Reduce picos de presión extrema y reparte demanda por salas.',
  balanced: 'Equilibra presión, conflictos y protección de sets importantes.',
  fan_experience: 'Maximiza ver artistas top con menos solapes severos.',
};

const menu: Array<{ key: MenuView; label: string; icon: LucideIcon }> = [
  { key: 'dashboard', label: 'Dashboard', icon: Sparkles },
  { key: 'ranking', label: 'Ranking', icon: Gauge },
  { key: 'rooms', label: 'Salas', icon: MapIcon },
  { key: 'timetables', label: 'Horarios', icon: CalendarClock },
];

const roomBlueprint = [
  { slug: 'main-room', name: 'Main Room', x: 43, y: 31, w: 30, h: 24, level: 'xl', capacity: 4000 },
  { slug: 'open-air', name: 'Open Air', x: 13, y: 19, w: 24, h: 21, level: 'lg', capacity: 2600 },
  { slug: 'hangar', name: 'Hangar', x: 70, y: 14, w: 22, h: 20, level: 'lg', capacity: 2000 },
  { slug: 'area-19', name: 'Area 19', x: 66, y: 52, w: 22, h: 18, level: 'md', capacity: 1400 },
  { slug: 'satelite', name: 'Satelite', x: 12, y: 55, w: 22, h: 18, level: 'md', capacity: 1300 },
  { slug: 'club-area', name: 'Club Area', x: 37, y: 65, w: 20, h: 17, level: 'sm', capacity: 800 },
  { slug: 'crystal-area', name: 'Crystal Area', x: 60, y: 75, w: 21, h: 17, level: 'sm', capacity: 750 },
] as const;

const slotStart = 21 * 60;
const slotEnd = 31 * 60; // 07:00 next day, in minute scale used by the backend.

const initialData: DashboardState = {
  health: null,
  evidence: null,
  genres: null,
  demand: null,
  artists: [],
  probable: null,
  probableSlots: null,
  optimizedCoverage: null,
  optimized: null,
  optimizedSlots: {},
  social: null,
};

export function NexusDashboard() {
  const [activeView, setActiveView] = useState<MainView>('dashboard');
  const [previousView, setPreviousView] = useState<MenuView>('ranking');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [data, setData] = useState<DashboardState>(initialData);
  const [query, setQuery] = useState('');
  const [genre, setGenre] = useState('all');
  const [selectedSchedule, setSelectedSchedule] = useState<ScheduleKey>('fan_experience');
  const [selectedDay, setSelectedDay] = useState<DayFilter>('all');
  const [selectedRoom, setSelectedRoom] = useState('all');
  const [selectedArtist, setSelectedArtist] = useState<DemandArtist | null>(null);

  async function loadDashboard() {
    setLoading(true);
    setError(null);
    try {
      const [health, evidence, genres, demand, artists, probable, probableSlots, optimizedCoverage, optimized, antiSlots, balancedSlots, fanSlots, social] = await Promise.all([
        api.health(),
        api.evidenceCoverage(),
        api.genreCoverage(),
        api.demandCoverage(2026),
        api.demandArtists(2026, 140),
        api.probableCoverage(2026),
        api.probableSlots(2026, 240),
        api.optimizedCoverage(2026),
        api.optimizedCompare(2026),
        api.optimizedVariantSlots(2026, 'anti_crowding_extreme', 240),
        api.optimizedVariantSlots(2026, 'balanced', 240),
        api.optimizedVariantSlots(2026, 'fan_experience', 240),
        api.socialStatus(),
      ]);

      setData({
        health,
        evidence,
        genres,
        demand,
        artists: artists.items,
        probable,
        probableSlots,
        optimizedCoverage,
        optimized,
        optimizedSlots: {
          anti_crowding_extreme: antiSlots,
          balanced: balancedSlots,
          fan_experience: fanSlots,
        },
        social,
      });
    } catch (unknownError) {
      const message = unknownError instanceof Error ? unknownError.message : 'No se pudo conectar con la API.';
      setError(message);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void loadDashboard();
  }, []);

  const scheduleSlots = useMemo(() => getSlotsForSchedule(data, selectedSchedule), [data, selectedSchedule]);
  const visibleSlots = useMemo(
    () => filterSlots(scheduleSlots, selectedDay, selectedRoom),
    [scheduleSlots, selectedDay, selectedRoom],
  );
  const roomPressure = useMemo(() => computeRoomPressure(scheduleSlots), [scheduleSlots]);
  const visibleRoomPressure = useMemo(
    () => (selectedRoom === 'all' ? roomPressure : roomPressure.filter((room) => room.slug === selectedRoom)),
    [roomPressure, selectedRoom],
  );
  const topRiskRoom = roomPressure[0];
  const timeMatrix = useMemo(() => computeTimeMatrix(visibleSlots), [visibleSlots]);
  const hourlySummary = useMemo(() => computeHourlySummary(visibleSlots), [visibleSlots]);
  const timelineGroups = useMemo(() => groupTimelineSlots(visibleSlots), [visibleSlots]);
  const allGenres = useMemo(() => Array.from(new Set(data.artists.map((artist) => artist.main_genre).filter(Boolean) as string[])).sort(), [data.artists]);
  const filteredArtists = useMemo(() => {
    const normalized = query.trim().toLowerCase();
    return data.artists.filter((artist) => {
      const genreMatch = genre === 'all' || artist.main_genre === genre;
      const queryMatch =
        !normalized ||
        artist.artist_name.toLowerCase().includes(normalized) ||
        artist.artist_slug.toLowerCase().includes(normalized) ||
        artist.secondary_genres?.some((item) => item.toLowerCase().includes(normalized));
      return genreMatch && queryMatch;
    });
  }, [data.artists, genre, query]);
  const selectedVariant = data.optimized?.variants.find((variant) => variant.variant_key === selectedSchedule);
  const demandChart = useMemo(() => data.artists.slice(0, 10).map((artist) => ({ name: artist.artist_name, score: artist.demand_score ?? 0 })), [data.artists]);
  const selectedArtistSlots = useMemo(() => {
    if (!selectedArtist) return [];
    const allSlots = [
      ...(data.probableSlots?.items ?? []),
      ...(data.optimizedSlots.anti_crowding_extreme?.items ?? []),
      ...(data.optimizedSlots.balanced?.items ?? []),
      ...(data.optimizedSlots.fan_experience?.items ?? []),
    ];
    return allSlots.filter((slot) => slot.artist_slug === selectedArtist.artist_slug);
  }, [data, selectedArtist]);

  const openArtist = (artist: DemandArtist) => {
    setPreviousView(activeView === 'artist' ? previousView : (activeView as MenuView));
    setSelectedArtist(artist);
    setActiveView('artist');
  };

  const navigate = (view: MenuView) => {
    setActiveView(view);
    setPreviousView(view);
  };

  return (
    <main className="nexus-shell">
      <AppChrome activeView={activeView} navigate={navigate} apiConnected={data.health?.status === 'ok'} refresh={() => void loadDashboard()} />

      {loading ? <LoadingPanel label="Cargando motor V2 y mapas de horarios..." /> : null}
      {error ? <ErrorPanel message={error} /> : null}

      {!loading && !error ? (
        <AnimatePresence mode="wait">
          <motion.div
            key={activeView}
            initial={{ opacity: 0, y: 18, filter: 'blur(10px)' }}
            animate={{ opacity: 1, y: 0, filter: 'blur(0px)' }}
            exit={{ opacity: 0, y: -12, filter: 'blur(6px)' }}
            transition={{ duration: 0.22 }}
          >
            {activeView === 'dashboard' ? (
              <DashboardView
                data={data}
                topRiskRoom={topRiskRoom}
                roomPressure={roomPressure}
                demandChart={demandChart}
                selectedVariant={data.optimized?.variants.find((variant) => variant.variant_key === 'fan_experience')}
                setActiveView={navigate}
                openArtist={openArtist}
                refresh={loadDashboard}
              />
            ) : null}

            {activeView === 'ranking' ? (
              <RankingView
                artists={filteredArtists}
                allGenres={allGenres}
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
                selectedDay={selectedDay}
                setSelectedDay={setSelectedDay}
                roomPressure={visibleRoomPressure}
                allRoomPressure={roomPressure}
                timeMatrix={timeMatrix}
                hourlySummary={hourlySummary}
                roomOptions={roomOptionsFromSlots(scheduleSlots)}
                selectedRoom={selectedRoom}
                setSelectedRoom={setSelectedRoom}
                topRiskRoom={topRiskRoom}
                visibleSlots={visibleSlots}
              />
            ) : null}

            {activeView === 'timetables' ? (
              <TimetablesView
                selectedSchedule={selectedSchedule}
                setSelectedSchedule={setSelectedSchedule}
                selectedDay={selectedDay}
                setSelectedDay={setSelectedDay}
                selectedRoom={selectedRoom}
                setSelectedRoom={setSelectedRoom}
                scheduleList={visibleSlots}
                roomOptions={roomOptionsFromSlots(scheduleSlots)}
                optimized={data.optimized}
                optimizedCoverage={data.optimizedCoverage}
                probable={data.probable}
                selectedVariant={selectedVariant}
                timelineGroups={timelineGroups}
              />
            ) : null}

            {activeView === 'artist' && selectedArtist ? (
              <ArtistDetailView artist={selectedArtist} artistSlots={selectedArtistSlots} back={() => setActiveView(previousView)} />
            ) : null}
          </motion.div>
        </AnimatePresence>
      ) : null}
    </main>
  );
}

function AppChrome({
  activeView,
  navigate,
  apiConnected,
  refresh,
}: {
  activeView: MainView;
  navigate: (view: MenuView) => void;
  apiConnected: boolean;
  refresh: () => void;
}) {
  return (
    <>
      <header className="topbar">
        <button className="brand-mark" onClick={() => navigate('dashboard')} aria-label="Volver al dashboard">
          <span className="brand-logo"><Music2 size={18} /></span>
          <span>
            <strong>Nexus Predictor</strong>
            <small>V2 · Fabrik intelligence</small>
          </span>
        </button>
        <nav className="desktop-nav" aria-label="Navegación principal">
          {menu.map((item) => {
            const Icon = item.icon;
            return (
              <button key={item.key} className={activeView === item.key ? 'active' : ''} onClick={() => navigate(item.key)}>
                <Icon size={16} /> {item.label}
              </button>
            );
          })}
        </nav>
        <div className="topbar-actions">
          <StatusPill tone={apiConnected ? 'ok' : 'warning'}>{apiConnected ? 'API conectada' : 'API pendiente'}</StatusPill>
          <button className="icon-button" onClick={refresh} aria-label="Refrescar datos"><RefreshCcw size={16} /></button>
        </div>
      </header>

      <nav className="bottom-nav" aria-label="Navegación móvil">
        {menu.map((item) => {
          const Icon = item.icon;
          return (
            <button key={item.key} className={activeView === item.key ? 'active' : ''} onClick={() => navigate(item.key)}>
              <Icon size={17} />
              <span>{item.label}</span>
            </button>
          );
        })}
      </nav>
    </>
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
  setActiveView: (view: MenuView) => void;
  openArtist: (artist: DemandArtist) => void;
  refresh: () => Promise<void>;
}) {
  return (
    <>
      <section className="hero v211-hero">
        <motion.div className="hero-panel" initial={{ opacity: 0, y: 18 }} animate={{ opacity: 1, y: 0 }}>
          <div className="kicker"><Sparkles size={15} /> V2.11 · mapa y horarios calibrados</div>
          <h1>
            Venue map, horario probable y optimizadores <span className="hero-gradient">en una cabina visual.</span>
          </h1>
          <p className="hero-copy">
            Esta capa pule la experiencia visual sin cambiar el backend: compara el horario probable con las 3 variantes
            óptimas, explica presión por sala/franja y mantiene la estética cyberpunk/Fabrik night.
          </p>
          <div className="hero-actions">
            <button className="pill-button primary" onClick={() => setActiveView('timetables')}><CalendarClock size={17} /> Comparar horarios</button>
            <button className="pill-button" onClick={() => setActiveView('rooms')}><MapIcon size={17} /> Abrir mapa</button>
            <button className="pill-button" onClick={() => void refresh()}><RefreshCcw size={17} /> Refrescar API</button>
          </div>
        </motion.div>

        <aside className="hero-side-grid">
          <MetricCard icon={Users} label="Artistas" value={number(data.demand?.total_artists)} note="Predicciones V2.7" tone="cyan" />
          <MetricCard icon={CalendarClock} label="Slots probables" value={number(data.probable?.total_slots)} note="No oficial" tone="acid" />
          <MetricCard icon={Layers3} label="Variantes" value={number(data.optimizedCoverage?.generated_variants ?? data.optimized?.variants.length)} note="V2.9 · OR-Tools" tone="violet" />
          <MetricCard icon={AlertTriangle} label="Pico sala" value={normalizedPercent(topRiskRoom?.maxPressure)} note={topRiskRoom?.room ?? 'Modelo pendiente'} tone="pink" />
        </aside>
      </section>

      <section className="dashboard-layout">
        <article className="card edition-card grid-span-2">
          <div className="card-header">
            <div><small>Estado de la edición</small><h3 className="card-title">Nexus 2026 · escenario predictivo</h3></div>
            <StatusPill tone="warning">No oficial</StatusPill>
          </div>
          <div className="edition-meter">
            <div><strong>{score(data.demand?.average_demand_score)}</strong><span>demanda media</span></div>
            <div><strong>{number(data.probable?.total_rooms)}</strong><span>salas reales</span></div>
            <div><strong>{number(data.optimizedCoverage?.total_slots)}</strong><span>slots optimizados</span></div>
            <div><strong>{data.optimizedCoverage?.uses_ortools ? 'Sí' : '—'}</strong><span>OR-Tools</span></div>
          </div>
          <p className="muted-copy">
            El dashboard resume el motor V2, pero la experiencia completa de saturación y comparativa vive ahora en
            <strong> Salas</strong> y <strong>Horarios</strong>. Los datos siguen distinguiendo estimación, inferencia y ausencia de horario oficial.
          </p>
        </article>

        <article className="card ranking-preview">
          <div className="card-header">
            <div><small>Top demanda V2</small><h3 className="card-title">Headliners probables</h3></div>
            <button className="ghost-link" onClick={() => setActiveView('ranking')}>Ver ranking</button>
          </div>
          <div className="artist-mini-list">
            {data.artists.slice(0, 5).map((artist) => (
              <button key={artist.artist_slug} onClick={() => openArtist(artist)}>
                <span>#{artist.rank ?? '—'}</span>
                <strong>{artist.artist_name}</strong>
                <em>{score(artist.demand_score)}</em>
              </button>
            ))}
          </div>
        </article>

        <article className="card chart-card">
          <div className="card-header">
            <div><small>Curva del modelo</small><h3 className="card-title">Top 10 demanda</h3></div>
            <StatusPill tone="ok">V2.7</StatusPill>
          </div>
          {demandChart.length ? <DemandLine data={demandChart} /> : <EmptyPanel />}
        </article>

        <article className="card model-card">
          <div className="card-header">
            <div><small>Datos y confianza</small><h3 className="card-title">Cobertura V2</h3></div>
            <StatusPill>evidence weighted</StatusPill>
          </div>
          <div className="signal-grid">
            <Signal label="Evidencias" value={number(data.evidence?.evidence_items)} />
            <Signal label="Spotify" value={number(data.demand?.artists_with_spotify)} />
            <Signal label="Social/platform" value={number(data.demand?.artists_with_social_or_platform_metrics)} />
            <Signal label="Unknown" value={percent(data.genres?.unknown_rate)} />
          </div>
        </article>

        <article className="card room-preview">
          <div className="card-header">
            <div><small>Mapa profesional</small><h3 className="card-title">Sala más sensible</h3></div>
            <button className="ghost-link" onClick={() => setActiveView('rooms')}>Abrir mapa</button>
          </div>
          <RoomRiskList rooms={roomPressure.slice(0, 4)} />
        </article>

        <article className="card timetable-preview grid-span-2">
          <div className="card-header">
            <div><small>Comparador V2.11</small><h3 className="card-title">Probable vs variantes óptimas</h3></div>
            <button className="ghost-link" onClick={() => setActiveView('timetables')}>Abrir horarios</button>
          </div>
          <div className="variant-strip">
            {data.optimized?.variants.map((variant) => (
              <div key={variant.variant_key} className="variant-chip-card">
                <strong>{variant.variant_name}</strong>
                <span>{variant.high_risk_slots} high-risk · {variant.changed_slots_from_probable} cambios</span>
                <em>{score(variant.average_optimization_score)}</em>
              </div>
            ))}
          </div>
          <p className="muted-copy">Recomendación visual: {selectedVariant?.variant_name ?? 'Experiencia fan'} para revisar recorridos de sets top.</p>
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
        copy="Acceso directo a las fichas de artista. La ficha no aparece en el menú principal para mantener una navegación más limpia."
        icon={Gauge}
      />

      <div className="toolbar-card">
        <label className="search-box"><Search size={16} /><input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Buscar artista, género o slug..." /></label>
        <select className="select-control" value={genre} onChange={(event) => setGenre(event.target.value)}>
          <option value="all">Todos los géneros</option>
          {allGenres.map((item) => <option key={item} value={item}>{item}</option>)}
        </select>
      </div>

      <div className="ranking-list full-ranking">
        {artists.map((artist) => (
          <button className="artist-row" key={artist.artist_slug} onClick={() => openArtist(artist)}>
            <span className="rank-number">#{artist.rank ?? '—'}</span>
            <div className="artist-row-main">
              <strong>{artist.artist_name}</strong>
              <span>{artist.main_genre ?? 'Unknown'} · {artist.secondary_genres?.slice(0, 2).join(' / ') || 'sin secundarios'} · {artist.confidence ?? 'medium'}</span>
            </div>
            <div className="artist-score-cluster">
              <span className={`pressure-badge ${riskTone(artist.demand_score ?? 0)}`}>{score(artist.demand_score)}</span>
              <em>{title(artist.crowd_risk)}</em>
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
  selectedDay,
  setSelectedDay,
  roomPressure,
  allRoomPressure,
  timeMatrix,
  hourlySummary,
  roomOptions,
  selectedRoom,
  setSelectedRoom,
  topRiskRoom,
  visibleSlots,
}: {
  selectedSchedule: ScheduleKey;
  setSelectedSchedule: (schedule: ScheduleKey) => void;
  selectedDay: DayFilter;
  setSelectedDay: (day: DayFilter) => void;
  roomPressure: RoomPressure[];
  allRoomPressure: RoomPressure[];
  timeMatrix: TimePressure[];
  hourlySummary: TimePressure[];
  roomOptions: Array<{ slug: string; name: string }>;
  selectedRoom: string;
  setSelectedRoom: (room: string) => void;
  topRiskRoom: RoomPressure | undefined;
  visibleSlots: TimetableSlot[];
}) {
  const focusedRoom = selectedRoom === 'all' ? topRiskRoom : allRoomPressure.find((room) => room.slug === selectedRoom);

  return (
    <section className="page-block">
      <PageHero
        eyebrow="Salas"
        title="Mapa profesional de presión por sala"
        copy="V2.11 calibra el mapa con los campos del modelo: expected_pressure_score, crowding_score, demand_score, conflict_score y capacidad estimada."
        icon={MapIcon}
      />

      <div className="toolbar-card sticky-toolbar">
        <select className="select-control" value={selectedSchedule} onChange={(event) => setSelectedSchedule(event.target.value as ScheduleKey)}>
          {Object.entries(scheduleLabels).map(([key, label]) => <option key={key} value={key}>{label}</option>)}
        </select>
        <select className="select-control" value={selectedDay} onChange={(event) => setSelectedDay(event.target.value as DayFilter)}>
          <option value="all">Viernes + sábado</option>
          <option value="friday">Viernes</option>
          <option value="saturday">Sábado</option>
        </select>
        <select className="select-control" value={selectedRoom} onChange={(event) => setSelectedRoom(event.target.value)}>
          <option value="all">Todas las salas</option>
          {roomOptions.map((room) => <option key={room.slug} value={room.slug}>{room.name}</option>)}
        </select>
      </div>

      <div className="venue-command-grid">
        <article className="card venue-map-card grid-span-2">
          <div className="card-header">
            <div><small>Fabrik Madrid · modelo 7 salas</small><h3 className="card-title">Plano de saturación calibrado</h3></div>
            <StatusPill tone="warning">Predicción no oficial</StatusPill>
          </div>
          <ProfessionalVenueMap rooms={allRoomPressure} selectedRoom={selectedRoom} setSelectedRoom={setSelectedRoom} />
        </article>

        <article className="card room-profile-card">
          <div className="card-header">
            <div><small>Ficha de sala</small><h3 className="card-title">{focusedRoom?.room ?? 'Selecciona una sala'}</h3></div>
            <span className={`pressure-badge ${riskTone(focusedRoom?.avgPressure ?? 0)}`}>{normalizedPercent(focusedRoom?.avgPressure)}</span>
          </div>
          <div className="room-profile-metrics">
            <Signal label="Pico presión" value={normalizedPercent(focusedRoom?.maxPressure)} />
            <Signal label="Demanda media" value={score(focusedRoom?.avgDemand)} />
            <Signal label="Headliners" value={number(focusedRoom?.headliners)} />
            <Signal label="Capacidad" value={number(focusedRoom?.capacity)} />
          </div>
          <p className="muted-copy">
            Pico actual: <strong>{focusedRoom?.peakArtist ?? '—'}</strong> · {focusedRoom?.peakTime ?? '—'}. Los porcentajes se normalizan para UI, pero la presión bruta se conserva como referencia del modelo.
          </p>
        </article>

        <article className="card heatmap-card grid-span-2">
          <div className="card-header">
            <div><small>Saturación por hora</small><h3 className="card-title">Heatmap de sala/franja</h3></div>
            <StatusPill>Slots visibles: {number(visibleSlots.length)}</StatusPill>
          </div>
          <PressureHeatmap matrix={timeMatrix} />
        </article>

        <article className="card hourly-card">
          <div className="card-header">
            <div><small>Horas críticas</small><h3 className="card-title">Picos por franja</h3></div>
            <StatusPill tone="danger">V2 model</StatusPill>
          </div>
          <CriticalHours rows={hourlySummary} />
        </article>

        <article className="card room-list-card grid-span-3">
          <div className="card-header">
            <div><small>Ranking de salas</small><h3 className="card-title">Presión media, picos y explicación</h3></div>
          </div>
          <RoomRiskList rooms={roomPressure} expanded />
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
  selectedRoom,
  setSelectedRoom,
  scheduleList,
  roomOptions,
  optimized,
  optimizedCoverage,
  probable,
  selectedVariant,
  timelineGroups,
}: {
  selectedSchedule: ScheduleKey;
  setSelectedSchedule: (schedule: ScheduleKey) => void;
  selectedDay: DayFilter;
  setSelectedDay: (day: DayFilter) => void;
  selectedRoom: string;
  setSelectedRoom: (room: string) => void;
  scheduleList: TimetableSlot[];
  roomOptions: Array<{ slug: string; name: string }>;
  optimized: OptimizedComparison | null;
  optimizedCoverage: OptimizedCoverage | null;
  probable: DashboardState['probable'];
  selectedVariant: OptimizedVariant | undefined;
  timelineGroups: TimelineGroup[];
}) {
  return (
    <section className="page-block">
      <PageHero
        eyebrow="Horarios"
        title="Probable 2026 vs horarios óptimos"
        copy="Comparador visual para ver qué cambia entre el horario probable y las tres variantes: anti-aglomeraciones, equilibrio y experiencia fan."
        icon={CalendarClock}
      />

      <div className="toolbar-card sticky-toolbar">
        <select className="select-control" value={selectedSchedule} onChange={(event) => setSelectedSchedule(event.target.value as ScheduleKey)}>
          {Object.entries(scheduleLabels).map(([key, label]) => <option key={key} value={key}>{label}</option>)}
        </select>
        <select className="select-control" value={selectedDay} onChange={(event) => setSelectedDay(event.target.value as DayFilter)}>
          <option value="all">Viernes + sábado</option>
          <option value="friday">Viernes</option>
          <option value="saturday">Sábado</option>
        </select>
        <select className="select-control" value={selectedRoom} onChange={(event) => setSelectedRoom(event.target.value)}>
          <option value="all">Todas las salas</option>
          {roomOptions.map((room) => <option key={room.slug} value={room.slug}>{room.name}</option>)}
        </select>
      </div>

      <div className="timetable-summary-grid">
        <MetricCard icon={CalendarClock} label="Slots visibles" value={number(scheduleList.length)} note="Filtrados por escenario, día y sala" tone="cyan" />
        <MetricCard icon={AlertTriangle} label="High-risk" value={number(selectedVariant?.high_risk_slots ?? countHighRisk(scheduleList))} note="Presión alta detectada" tone="pink" />
        <MetricCard icon={Zap} label="Experience" value={score(selectedVariant?.average_experience_score ?? probable?.average_probability_score)} note="Mayor es mejor" tone="acid" />
        <MetricCard icon={ShieldCheck} label="Estado" value="No oficial" note={optimizedCoverage?.source_status ?? probable?.source_status ?? 'sin fuente oficial'} tone="orange" />
      </div>

      {optimized?.variants?.length ? <VariantComparison variants={optimized.variants} selectedSchedule={selectedSchedule} setSelectedSchedule={setSelectedSchedule} /> : null}

      <article className="card timetable-explainer">
        <div className="card-header">
          <div><small>Cómo leerlo</small><h3 className="card-title">Diferencia entre probable y óptimos</h3></div>
          <StatusPill tone="warning">Inferido</StatusPill>
        </div>
        <div className="explanation-grid">
          <Explain icon={Radio} title="Probable" copy="Lo que probablemente haría la organización según patrones históricos y demanda." />
          <Explain icon={ShieldCheck} title="Anti-aglomeración" copy="Reasigna sets para evitar picos de presión en salas pequeñas o franjas críticas." />
          <Explain icon={Layers3} title="Equilibrado" copy="Compromiso entre seguridad de flujo, sala adecuada y protección de sets principales." />
          <Explain icon={Zap} title="Fan experience" copy="Prioriza poder ver más artistas top con menos conflictos severos." />
        </div>
      </article>

      <div className="timeline-layout">
        {timelineGroups.map((group) => (
          <article className="card timeline-room" key={group.key}>
            <div className="card-header compact">
              <div><small>{title(group.day)}</small><h3 className="card-title">{group.label}</h3></div>
              <span className="badge cyan">{group.slots.length} slots</span>
            </div>
            <div className="timeline-track">
              {group.slots.map((slot) => <TimelineSlot key={`${slot.artist_slug}-${slot.event_day}-${slot.room_slug}-${slot.start_time}`} slot={slot} />)}
            </div>
          </article>
        ))}
      </div>

      {!timelineGroups.length ? <EmptyPanel label="No hay slots para los filtros seleccionados." /> : null}
    </section>
  );
}

function ArtistDetailView({ artist, artistSlots, back }: { artist: DemandArtist; artistSlots: TimetableSlot[]; back: () => void }) {
  return (
    <section className="page-block">
      <button className="back-button" onClick={back}><ArrowLeft size={16} /> Volver</button>
      <div className="artist-detail-hero">
        <div>
          <small>{artist.main_genre ?? 'Unknown'} · #{artist.rank ?? '—'}</small>
          <h2>{artist.artist_name}</h2>
          <p>Ficha deeplink con demanda, factores explicables y apariciones en horarios predictivos/optimizados.</p>
        </div>
        <div className="artist-hero-score">
          <span>{score(artist.demand_score)}</span>
          <small>demand_score</small>
        </div>
      </div>

      <div className="artist-detail-grid">
        <MetricCard icon={TrendingUp} label="Popularidad" value={score(artist.popularity_score)} note="Spotify/social/fallback" tone="cyan" />
        <MetricCard icon={Flame} label="Carrera" value={score(artist.career_score)} note="Eventos y prestigio" tone="violet" />
        <MetricCard icon={Zap} label="Momentum" value={score(artist.momentum_score)} note="Señales recientes" tone="acid" />
        <MetricCard icon={Database} label="Evidencias" value={number(artist.evidence_count)} note={artist.fallback_used ? 'Incluye fallback' : 'Dato trazable'} tone="orange" />

        <article className="card grid-span-2">
          <div className="card-header"><div><small>Score explicable</small><h3 className="card-title">Factores del modelo</h3></div></div>
          <FactorBars artist={artist} />
        </article>

        <article className="card grid-span-2">
          <div className="card-header"><div><small>Slots relacionados</small><h3 className="card-title">Probable y variantes</h3></div></div>
          <ul className="slot-feed compact-feed">
            {artistSlots.slice(0, 12).map((slot) => (
              <li key={`${slot.variant_key ?? 'probable'}-${slot.artist_slug}-${slot.start_time}-${slot.room_slug}`}>
                <time>{slot.start_time}</time>
                <div><strong>{scheduleLabels[(slot.variant_key as ScheduleKey) ?? 'probable'] ?? 'Horario probable'}</strong><span>{slot.room_name} · {title(slot.event_day)} · {title(slot.slot_type)}</span></div>
                <span className={`pressure-badge ${riskTone(pressureFromSlot(slot))}`}>{normalizedPercent(pressureFromSlot(slot))}</span>
              </li>
            ))}
          </ul>
          {!artistSlots.length ? <EmptyPanel label="Este artista todavía no tiene slot visible en los horarios cargados." /> : null}
        </article>
      </div>
    </section>
  );
}

function PageHero({ eyebrow, title: pageTitle, copy, icon: Icon }: { eyebrow: string; title: string; copy: string; icon: LucideIcon }) {
  return (
    <section className="page-hero">
      <div className="kicker"><Icon size={15} /> {eyebrow}</div>
      <h2>{pageTitle}</h2>
      <p>{copy}</p>
    </section>
  );
}

function Signal({ label, value }: { label: string; value: string | number }) {
  return <div className="signal"><span>{label}</span><strong>{value}</strong></div>;
}

function Explain({ icon: Icon, title: explainTitle, copy }: { icon: LucideIcon; title: string; copy: string }) {
  return <div className="explain-card"><Icon size={18} /><strong>{explainTitle}</strong><span>{copy}</span></div>;
}

function DemandLine({ data }: { data: Array<{ name: string; score: number }> }) {
  return (
    <div className="chart-wrap">
      <ResponsiveContainer width="100%" height="100%">
        <RechartsLineChart data={data} margin={{ top: 12, right: 10, left: -20, bottom: 18 }}>
          <CartesianGrid stroke="rgba(255,255,255,0.08)" vertical={false} />
          <XAxis dataKey="name" tick={{ fill: '#b8bfd9', fontSize: 10 }} angle={-18} textAnchor="end" height={44} />
          <YAxis tick={{ fill: '#b8bfd9', fontSize: 10 }} />
          <Tooltip contentStyle={{ background: '#090914', border: '1px solid rgba(255,255,255,0.16)', borderRadius: 14 }} />
          <Line type="monotone" dataKey="score" stroke="#f8f871" strokeWidth={3} dot={{ r: 4, fill: '#8b5cf6' }} />
        </RechartsLineChart>
      </ResponsiveContainer>
    </div>
  );
}

function ProfessionalVenueMap({ rooms, selectedRoom, setSelectedRoom }: { rooms: RoomPressure[]; selectedRoom: string; setSelectedRoom: (room: string) => void }) {
  const bySlug = new globalThis.Map(rooms.map((room) => [room.slug, room] as const));
  return (
    <div className="professional-map">
      <div className="map-layer map-layer-grid" />
      <div className="map-layer map-layer-core" />
      <div className="map-route route-a" />
      <div className="map-route route-b" />
      <div className="map-route route-c" />
      {roomBlueprint.map((room) => {
        const risk = bySlug.get(room.slug);
        const pressure = risk?.avgPressure ?? 0;
        return (
          <button
            key={room.slug}
            className={`venue-room ${room.level} ${riskTone(pressure)} ${selectedRoom === room.slug ? 'selected' : ''}`}
            style={{ left: `${room.x}%`, top: `${room.y}%`, width: `${room.w}%`, height: `${room.h}%` }}
            onClick={() => setSelectedRoom(room.slug)}
            title={`${room.name}: ${normalizedPercent(pressure)} · raw ${score(risk?.maxPressure)}`}
          >
            <span className="room-glow" />
            <strong>{room.name}</strong>
            <em>{normalizedPercent(pressure)}</em>
            <small>{number(risk?.totalSlots)} slots</small>
          </button>
        );
      })}
      <div className="map-legend">
        <span><i className="legend-low" /> Baja</span>
        <span><i className="legend-medium" /> Media</span>
        <span><i className="legend-high" /> Alta</span>
        <span><i className="legend-extreme" /> Extrema</span>
      </div>
    </div>
  );
}

function PressureHeatmap({ matrix }: { matrix: TimePressure[] }) {
  if (!matrix.length) return <EmptyPanel label="No hay slots para la sala o escenario seleccionado." />;
  return (
    <div className="heatmap-list calibrated">
      {matrix.slice(0, 64).map((item) => (
        <div key={`${item.room}-${item.day}-${item.time}-${item.artist}`} className={`heat-cell ${riskTone(item.pressure)}`}>
          <time>{item.time}</time>
          <strong>{item.room}</strong>
          <span>{item.artist}</span>
          <em>{normalizedPercent(item.pressure)} · raw {score(item.rawPressure)} · demand {score(item.demand)}</em>
        </div>
      ))}
    </div>
  );
}

function CriticalHours({ rows }: { rows: TimePressure[] }) {
  if (!rows.length) return <EmptyPanel label="No hay franjas críticas con los filtros actuales." />;
  return (
    <ul className="critical-list">
      {rows.slice(0, 8).map((row) => (
        <li key={`${row.day}-${row.time}-${row.slug}`}>
          <div><strong>{row.time} · {row.room}</strong><span>{title(row.day)} · {row.artist}</span></div>
          <span className={`pressure-badge ${riskTone(row.pressure)}`}>{normalizedPercent(row.pressure)}</span>
        </li>
      ))}
    </ul>
  );
}

function RoomRiskList({ rooms, expanded = false }: { rooms: RoomPressure[]; expanded?: boolean }) {
  if (!rooms.length) return <EmptyPanel label="No hay presión de salas disponible." />;
  return (
    <ul className={`split-list room-risk-list ${expanded ? 'expanded' : ''}`}>
      {rooms.map((room) => (
        <li key={room.slug}>
          <div className="list-main">
            <strong>{room.room}</strong>
            <span>{room.totalSlots} slots · pico {room.peakArtist} · {room.peakTime}</span>
            {expanded ? <em>crowding {score(room.avgCrowding)} · conflict {score(room.avgConflict)} · experience {score(room.avgExperience)}</em> : null}
          </div>
          <span className={`pressure-badge ${riskTone(room.avgPressure)}`}>{normalizedPercent(room.avgPressure)}</span>
        </li>
      ))}
    </ul>
  );
}

function VariantComparison({ variants, selectedSchedule, setSelectedSchedule }: { variants: OptimizedVariant[]; selectedSchedule: ScheduleKey; setSelectedSchedule: (value: ScheduleKey) => void }) {
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
      <div className="variant-cards-grid">
        {variants.map((variant) => (
          <button key={variant.variant_key} className={selectedSchedule === variant.variant_key ? 'variant-option active' : 'variant-option'} onClick={() => setSelectedSchedule(variant.variant_key as ScheduleKey)}>
            <strong>{variant.variant_name}</strong>
            <span>{variantGoalLabels[variant.variant_key as Exclude<ScheduleKey, 'probable'>]}</span>
            <div><em>{score(variant.average_crowding_score)}</em><small>crowding</small><em>{score(variant.average_conflict_score)}</em><small>conflict</small><em>{score(variant.average_experience_score)}</em><small>experience</small></div>
          </button>
        ))}
      </div>
      <div className="chart-wrap compact-chart">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={chartData} margin={{ top: 8, right: 8, left: -18, bottom: 18 }}>
            <CartesianGrid stroke="rgba(255,255,255,0.08)" vertical={false} />
            <XAxis dataKey="name" tick={{ fill: '#b8bfd9', fontSize: 10 }} angle={-12} textAnchor="end" height={46} />
            <YAxis tick={{ fill: '#b8bfd9', fontSize: 10 }} />
            <Tooltip contentStyle={{ background: '#090914', border: '1px solid rgba(255,255,255,0.16)', borderRadius: 14 }} />
            <Bar dataKey="crowding" radius={[8, 8, 0, 0]}>
              {chartData.map((entry) => <Cell key={`crowd-${entry.name}`} fill="#22d3ee" />)}
            </Bar>
            <Bar dataKey="conflict" radius={[8, 8, 0, 0]}>
              {chartData.map((entry) => <Cell key={`conflict-${entry.name}`} fill="#f97316" />)}
            </Bar>
            <Bar dataKey="experience" radius={[8, 8, 0, 0]}>
              {chartData.map((entry) => <Cell key={`experience-${entry.name}`} fill="#f8f871" />)}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>
    </article>
  );
}

function TimelineSlot({ slot }: { slot: TimetableSlot }) {
  const start = slot.start_minutes ?? timeToMinutes(slot.start_time);
  const end = slot.end_minutes ?? timeToMinutes(slot.end_time);
  const left = ((start - slotStart) / (slotEnd - slotStart)) * 100;
  const width = Math.max(7, ((end - start) / (slotEnd - slotStart)) * 100);
  const pressure = pressureFromSlot(slot);
  return (
    <div className={`timeline-slot ${riskTone(pressure)} ${slot.is_headliner_slot ? 'headliner' : ''}`} style={{ left: `${clamp(left, 0, 95)}%`, width: `${clamp(width, 7, 28)}%` }}>
      <strong>{slot.artist_name}</strong>
      <span>{slot.start_time}-{slot.end_time}</span>
      <em>{normalizedPercent(pressure)}</em>
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

function getSlotsForSchedule(data: DashboardState, schedule: ScheduleKey) {
  if (schedule === 'probable') return data.probableSlots?.items ?? [];
  return data.optimizedSlots[schedule]?.items ?? [];
}

function filterSlots(slots: TimetableSlot[], day: DayFilter, room: string) {
  return slots.filter((slot) => (day === 'all' || slot.event_day === day) && (room === 'all' || slot.room_slug === room));
}

function roomOptionsFromSlots(slots: TimetableSlot[]) {
  const map = new globalThis.Map<string, string>();
  slots.forEach((slot) => map.set(slot.room_slug, slot.room_name));
  roomBlueprint.forEach((room) => {
    if (!map.has(room.slug)) map.set(room.slug, room.name);
  });
  return Array.from(map.entries()).map(([slug, name]) => ({ slug, name })).sort((a, b) => a.name.localeCompare(b.name));
}

function computeRoomPressure(slots: TimetableSlot[]): RoomPressure[] {
  const groups = new globalThis.Map<string, TimetableSlot[]>();
  slots.forEach((slot) => groups.set(slot.room_slug, [...(groups.get(slot.room_slug) ?? []), slot]));

  return Array.from(groups.entries())
    .map(([slug, roomSlots]) => {
      const first = roomSlots[0];
      const normalizedPressures = roomSlots.map(pressureFromSlot);
      const peak = roomSlots.reduce((current, next) => (pressureFromSlot(next) > pressureFromSlot(current) ? next : current), first);
      const blueprint = roomBlueprint.find((room) => room.slug === slug);
      return {
        room: first.room_name,
        slug,
        avgPressure: avg(normalizedPressures),
        maxPressure: Math.max(...normalizedPressures),
        highRiskSlots: roomSlots.filter((slot) => pressureFromSlot(slot) >= 68 || slot.crowd_risk === 'high').length,
        totalSlots: roomSlots.length,
        peakArtist: peak.artist_name,
        peakTime: `${title(peak.event_day)} ${peak.start_time}`,
        capacity: first.room_capacity ?? blueprint?.capacity,
        headliners: roomSlots.filter((slot) => slot.is_headliner_slot).length,
        avgDemand: avg(roomSlots.map((slot) => slot.demand_score ?? 0)),
        avgCrowding: avg(roomSlots.map((slot) => slot.crowding_score ?? pressureFromSlot(slot))),
        avgConflict: avg(roomSlots.map((slot) => slot.conflict_score ?? 0)),
        avgExperience: avg(roomSlots.map((slot) => slot.experience_score ?? slot.probability_score ?? 0)),
        dayBreakdown: countBy(roomSlots, (slot) => slot.event_day),
      };
    })
    .sort((a, b) => b.avgPressure - a.avgPressure);
}

function computeTimeMatrix(slots: TimetableSlot[]): TimePressure[] {
  const groups = new globalThis.Map<string, TimetableSlot[]>();
  slots.forEach((slot) => {
    const key = `${slot.event_day}-${slot.room_slug}-${slot.start_time}`;
    groups.set(key, [...(groups.get(key) ?? []), slot]);
  });

  return Array.from(groups.values())
    .map((group) => {
      const top = group.reduce((current, next) => (pressureFromSlot(next) > pressureFromSlot(current) ? next : current), group[0]);
      return {
        room: top.room_name,
        slug: top.room_slug,
        time: top.start_time,
        day: top.event_day,
        artist: top.artist_name,
        slotCount: group.length,
        pressure: avg(group.map(pressureFromSlot)),
        rawPressure: avg(group.map(rawPressureFromSlot)),
        crowding: avg(group.map((slot) => slot.crowding_score ?? pressureFromSlot(slot))),
        demand: avg(group.map((slot) => slot.demand_score ?? 0)),
        conflict: avg(group.map((slot) => slot.conflict_score ?? 0)),
        experience: avg(group.map((slot) => slot.experience_score ?? slot.probability_score ?? 0)),
      };
    })
    .sort((a, b) => b.pressure - a.pressure || a.time.localeCompare(b.time));
}

function computeHourlySummary(slots: TimetableSlot[]) {
  const matrix = computeTimeMatrix(slots);
  return matrix.filter((item) => item.pressure >= 58).sort((a, b) => b.pressure - a.pressure);
}

function groupTimelineSlots(slots: TimetableSlot[]): TimelineGroup[] {
  const groups = new globalThis.Map<string, TimetableSlot[]>();
  slots.forEach((slot) => {
    const key = `${slot.event_day}-${slot.room_slug}`;
    groups.set(key, [...(groups.get(key) ?? []), slot]);
  });
  return Array.from(groups.entries())
    .map(([key, groupSlots]) => {
      const first = groupSlots[0];
      return {
        key,
        label: first.room_name,
        day: first.event_day,
        room: first.room_name,
        slug: first.room_slug,
        slots: [...groupSlots].sort((a, b) => (a.start_minutes ?? 0) - (b.start_minutes ?? 0)),
      };
    })
    .sort((a, b) => a.day.localeCompare(b.day) || roomOrder(a.slug) - roomOrder(b.slug));
}

function roomOrder(slug: string) {
  const index = roomBlueprint.findIndex((room) => room.slug === slug);
  return index === -1 ? 99 : index;
}

function rawPressureFromSlot(slot: TimetableSlot) {
  return slot.expected_pressure_score ?? slot.crowding_score ?? slot.demand_score ?? slot.probability_score ?? 0;
}

function pressureFromSlot(slot: TimetableSlot) {
  const raw = rawPressureFromSlot(slot);
  // V2.9 can intentionally output raw pressure above 100 (up to ~140) to flag overpressure.
  // The UI normalizes it to 0-100 while still showing raw values in detail panels.
  if ((slot.expected_pressure_score ?? 0) > 100 || raw > 100) return clamp((raw / 140) * 100);
  return clamp(raw);
}

function countHighRisk(slots: TimetableSlot[]) {
  return slots.filter((slot) => pressureFromSlot(slot) >= 68 || slot.crowd_risk === 'high').length;
}

function timeToMinutes(time: string) {
  const [hourString, minuteString] = time.split(':');
  const hour = Number(hourString);
  const minute = Number(minuteString ?? 0);
  const adjustedHour = hour < 12 ? hour + 24 : hour;
  return adjustedHour * 60 + minute;
}

function riskTone(value: number) {
  if (value >= 82) return 'extreme';
  if (value >= 68) return 'high';
  if (value >= 46) return 'medium';
  return 'low';
}

function avg(values: number[]) {
  const valid = values.filter((value) => Number.isFinite(value));
  if (!valid.length) return 0;
  return Math.round((valid.reduce((sum, value) => sum + value, 0) / valid.length) * 100) / 100;
}

function clamp(value: number, min = 0, max = 100) {
  return Math.max(min, Math.min(max, value));
}

function countBy<T>(rows: T[], picker: (row: T) => string) {
  return rows.reduce<Record<string, number>>((acc, row) => {
    const key = picker(row);
    acc[key] = (acc[key] ?? 0) + 1;
    return acc;
  }, {});
}
