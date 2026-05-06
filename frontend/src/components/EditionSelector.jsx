import { CalendarDays } from 'lucide-react';

// Mobile-friendly year selector required by Block 7.
export function EditionSelector({ years, selectedYear, onYearChange }) {
  return (
    <div className="edition-selector" aria-label="Seleccionar edición">
      <div className="selector-label">
        <CalendarDays size={16} />
        Edición
      </div>
      <div className="year-chip-row">
        {years.map((year) => {
          const isActive = Number(year) === Number(selectedYear);

          return (
            <button
              key={year}
              type="button"
              className={isActive ? 'year-chip year-chip-active' : 'year-chip'}
              onClick={() => onYearChange(Number(year))}
              aria-pressed={isActive}
            >
              {year}
            </button>
          );
        })}
      </div>
    </div>
  );
}
