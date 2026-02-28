/**
 * CityCard - Display a city in the journey timeline (without day plans)
 */
import { memo, useState } from 'react';
import { Calendar, ChevronDown, ChevronUp, Clock, MapPin, Star } from 'lucide-react';
import type { V6CityStop } from '@/types';
import { categoryStyles, cityColorPalettes, getCategoryIcon } from './styles';

interface CityCardProps {
  city: V6CityStop;
  index: number;
  isLast: boolean;
}

export const CityCard = memo(function CityCard({ city, index, isLast }: CityCardProps) {
  const [expanded, setExpanded] = useState(true);
  const palette = cityColorPalettes[index % cityColorPalettes.length];

  return (
    <div className="flex gap-4">
      {/* Timeline */}
      <div className="flex flex-col items-center flex-shrink-0 w-12">
        <div
          className="w-11 h-11 rounded-full text-white flex items-center justify-center font-display font-bold text-lg z-10 shadow-lg"
          style={{ backgroundColor: palette.accentColor }}
          aria-label={`City ${index + 1}`}
        >
          {index + 1}
        </div>
        {!isLast && <div className="flex-1 w-0.5 bg-gradient-to-b from-gray-300 to-gray-200 my-2" />}
      </div>

      {/* City content */}
      <div className="flex-1 min-w-0 pb-4">
        <div className="bg-white rounded-2xl shadow-md border border-gray-100/60 overflow-hidden hover:shadow-lg hover:-translate-y-0.5 transition-all duration-300">
          {/* Header */}
          <div 
            className="p-4"
            style={{ backgroundColor: palette.bgColor }}
          >
            <div className="flex items-center justify-between">
              <div className="flex-1">
                <div className="flex items-center gap-2">
                  <MapPin className="h-4 w-4" style={{ color: palette.textColor }} />
                  <h3 className="text-lg font-display font-bold text-gray-900 truncate">
                    {city.name}, {city.country}
                  </h3>
                </div>
                <div className="flex items-center gap-4 mt-1 text-sm text-gray-600">
                  <span className="flex items-center gap-1">
                    <Calendar className="h-3.5 w-3.5" />
                    {city.days} {city.days === 1 ? 'day' : 'days'}
                  </span>
                  {city.best_time_to_visit && (
                    <span className="flex items-center gap-1">
                      <Clock className="h-3.5 w-3.5" />
                      {city.best_time_to_visit}
                    </span>
                  )}
                </div>
              </div>
              <button
                onClick={() => setExpanded(!expanded)}
                className="p-2 hover:bg-gray-100/80 rounded-xl transition-colors"
                aria-expanded={expanded}
                aria-label={expanded ? 'Collapse city details' : 'Expand city details'}
              >
                {expanded ? (
                  <ChevronUp className="h-5 w-5 text-gray-400" />
                ) : (
                  <ChevronDown className="h-5 w-5 text-gray-400" />
                )}
              </button>
            </div>

            {/* Why visit */}
            {city.why_visit && (
              <p className="mt-3 text-sm text-gray-600">{city.why_visit}</p>
            )}
          </div>

          {/* Highlights */}
          {expanded && city.highlights && city.highlights.length > 0 && (
            <div className="p-4 border-t border-gray-100/60">
              <h4 className="text-sm font-display font-semibold text-gray-700 mb-3 flex items-center gap-2">
                <Star className="h-4 w-4 text-amber-500" />
                Top Highlights
              </h4>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3" role="list">
                {city.highlights.map((highlight, idx) => {
                  const highlightStyle = categoryStyles[highlight.category?.toLowerCase()] || categoryStyles.default;
                  return (
                    <div
                      key={idx}
                      className="bg-gray-50/80 border border-gray-100/60 rounded-xl p-3 hover:shadow-sm transition-all duration-200"
                      role="listitem"
                    >
                      <div className="flex items-start justify-between">
                        <div className="flex-1">
                          <h5 className="font-display font-medium text-gray-900 text-sm">{highlight.name}</h5>
                          <span
                            className="inline-flex items-center gap-1 mt-1 px-2 py-0.5 rounded-full text-xs capitalize font-medium"
                            style={{ 
                              backgroundColor: highlightStyle.bg,
                              color: highlightStyle.text,
                              border: `1px solid ${highlightStyle.border}`
                            }}
                          >
                            {getCategoryIcon(highlight.category)}
                            {highlight.category}
                          </span>
                        </div>
                        {highlight.suggested_duration_hours && (
                          <span className="text-xs text-gray-400 flex items-center gap-1">
                            <Clock className="h-3 w-3" />
                            {highlight.suggested_duration_hours}h
                          </span>
                        )}
                      </div>
                      <p className="mt-2 text-xs text-gray-600">{highlight.description}</p>
                    </div>
                  );
                })}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
});
