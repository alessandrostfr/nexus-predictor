import { Filter, Search, X } from 'lucide-react';

function getGenreOptions(genreTaxonomy, prediction) {
  const taxonomyNames = genreTaxonomy?.taxonomy?.map((genre) => genre.name) ?? [];
  const distributionNames = prediction?.genre_distribution?.map((genre) => genre.name) ?? [];
  return [...new Set([...taxonomyNames, ...distributionNames])]
    .filter((name) => name && name !== 'Unknown')
    .sort((a, b) => a.localeCompare(b));
}

// Search and genre filters for rankings. The layout is mobile-first.
export function GenreFilter({ filters, genreTaxonomy, prediction, onFiltersChange }) {
  const genres = getGenreOptions(genreTaxonomy, prediction);

  function updateFilter(key, value) {
    onFiltersChange({ ...filters, [key]: value });
  }

  function clearFilters() {
    onFiltersChange({ genre: '', query: '' });
  }

  return (
    <div className="filter-panel">
      <label className="filter-control">
        <span>
          <Search size={15} />
          Buscar artista
        </span>
        <input
          type="search"
          value={filters.query}
          placeholder="Angerfist, Project One..."
          onChange={(event) => updateFilter('query', event.target.value)}
        />
      </label>

      <label className="filter-control">
        <span>
          <Filter size={15} />
          Subgénero
        </span>
        <select value={filters.genre} onChange={(event) => updateFilter('genre', event.target.value)}>
          <option value="">Todos los subgéneros</option>
          {genres.map((genre) => (
            <option key={genre} value={genre}>
              {genre}
            </option>
          ))}
        </select>
      </label>

      <button className="clear-filter-button" type="button" onClick={clearFilters}>
        <X size={15} />
        Limpiar
      </button>
    </div>
  );
}
