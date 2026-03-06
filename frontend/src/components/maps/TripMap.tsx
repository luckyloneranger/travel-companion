import { useCallback, useEffect, useMemo, useState } from 'react';
import { Map, AdvancedMarker, InfoWindow, useMap, useMapsLibrary } from '@vis.gl/react-google-maps';
import type { JourneyPlan, CityStop, Location } from '@/types';

interface TripMapProps {
  journey: JourneyPlan;
  onCityClick?: (cityName: string) => void;
}

const MAP_ID = 'DEMO_MAP_ID';

/** Journey-level map showing all cities, hotels, and travel connections. */
export function TripMap({ journey, onCityClick }: TripMapProps) {
  const map = useMap('trip-map');
  const coreLib = useMapsLibrary('core');
  const [selectedCity, setSelectedCity] = useState<CityStop | null>(null);
  const [selectedHotel, setSelectedHotel] = useState<{ name: string; rating?: number; price?: number; location: Location } | null>(null);

  // Filter cities that have valid locations
  const citiesWithLocation = useMemo(
    () => journey.cities.filter((c): c is CityStop & { location: Location } => c.location !== null),
    [journey.cities],
  );

  // Fit bounds to all city locations
  const fitBounds = useCallback(() => {
    if (!map || !coreLib || citiesWithLocation.length === 0) return;

    const bounds = new coreLib.LatLngBounds();
    for (const city of citiesWithLocation) {
      bounds.extend({ lat: city.location.lat, lng: city.location.lng });
    }
    map.fitBounds(bounds, { top: 50, right: 50, bottom: 50, left: 50 });
  }, [map, coreLib, citiesWithLocation]);

  useEffect(() => {
    fitBounds();
  }, [fitBounds]);

  // Dashed lines between consecutive cities
  const mapsLib = useMapsLibrary('maps');
  useEffect(() => {
    if (!map || !mapsLib || citiesWithLocation.length < 2) return;

    const polylines: google.maps.Polyline[] = [];
    for (let i = 0; i < citiesWithLocation.length - 1; i++) {
      const from = citiesWithLocation[i].location;
      const to = citiesWithLocation[i + 1].location;

      const line = new mapsLib.Polyline({
        path: [
          { lat: from.lat, lng: from.lng },
          { lat: to.lat, lng: to.lng },
        ],
        geodesic: true,
        strokeColor: '#6366f1',
        strokeOpacity: 0,
        strokeWeight: 2,
        icons: [
          {
            icon: {
              path: 'M 0,-1 0,1',
              strokeOpacity: 0.6,
              strokeColor: '#6366f1',
              scale: 3,
            },
            offset: '0',
            repeat: '16px',
          },
        ],
        map,
      });
      polylines.push(line);
    }

    return () => {
      for (const p of polylines) p.setMap(null);
    };
  }, [map, mapsLib, citiesWithLocation]);

  // Default center fallback
  const defaultCenter = citiesWithLocation.length > 0
    ? { lat: citiesWithLocation[0].location.lat, lng: citiesWithLocation[0].location.lng }
    : { lat: 20, lng: 0 };

  return (
    <Map
      id="trip-map"
      mapId={MAP_ID}
      defaultCenter={defaultCenter}
      defaultZoom={4}
      gestureHandling="greedy"
      disableDefaultUI={false}
      style={{ width: '100%', height: '100%' }}
    >
      {/* City markers */}
      {citiesWithLocation.map((city, idx) => (
        <AdvancedMarker
          key={`city-${idx}`}
          position={{ lat: city.location.lat, lng: city.location.lng }}
          title={city.name}
          onClick={() => { setSelectedCity(city); setSelectedHotel(null); }}
        >
          <div className="flex flex-col items-center cursor-pointer">
            <span className="mb-1 rounded-full bg-indigo-600 px-2 py-0.5 text-xs font-semibold text-white shadow-md whitespace-nowrap max-w-[160px] truncate">
              {city.name}
            </span>
            <div className="h-4 w-4 rounded-full border-2 border-white bg-indigo-500 shadow-md" />
          </div>
        </AdvancedMarker>
      ))}

      {/* City info window */}
      {selectedCity?.location && (
        <InfoWindow
          position={{ lat: selectedCity.location.lat, lng: selectedCity.location.lng }}
          onCloseClick={() => setSelectedCity(null)}
          pixelOffset={[0, -30]}
        >
          <div className="p-1 min-w-[180px] max-w-[240px]">
            <h3 className="font-semibold text-sm" style={{ color: 'var(--theme-text-primary, #111827)' }}>{selectedCity.name}, {selectedCity.country}</h3>
            <p className="text-xs mt-0.5" style={{ color: 'var(--theme-text-muted, #6b7280)' }}>{selectedCity.days} {selectedCity.days === 1 ? 'day' : 'days'}</p>
            {selectedCity.why_visit && (
              <p className="text-xs mt-1 line-clamp-2" style={{ color: 'var(--theme-text-muted, #4b5563)' }}>{selectedCity.why_visit}</p>
            )}
            {selectedCity.accommodation && (
              <p className="text-xs mt-1" style={{ color: 'var(--theme-text-muted, #6b7280)' }}>&#x1F3E8; {selectedCity.accommodation.name}</p>
            )}
            {onCityClick && (
              <button
                onClick={() => { onCityClick(selectedCity.name); setSelectedCity(null); }}
                className="mt-2 text-xs font-medium"
                style={{ color: 'var(--theme-text-primary, #4f46e5)' }}
              >
                View itinerary &rarr;
              </button>
            )}
          </div>
        </InfoWindow>
      )}

      {/* Hotel / accommodation markers */}
      {citiesWithLocation.map((city, idx) => {
        const accom = city.accommodation;
        if (!accom?.location) return null;

        return (
          <AdvancedMarker
            key={`hotel-${idx}`}
            position={{ lat: accom.location.lat, lng: accom.location.lng }}
            title={accom.name}
            onClick={() => { setSelectedHotel({ name: accom.name, rating: accom.rating ?? undefined, price: accom.estimated_nightly_usd ?? undefined, location: accom.location! }); setSelectedCity(null); }}
          >
            <div className="flex flex-col items-center cursor-pointer">
              <span className="mb-1 rounded bg-amber-500 px-1.5 py-0.5 text-xs font-medium text-white shadow whitespace-nowrap max-w-[160px] truncate">
                {accom.name}
              </span>
              <div className="flex h-5 w-5 items-center justify-center rounded-full border-2 border-white bg-amber-500 shadow-md">
                <svg
                  xmlns="http://www.w3.org/2000/svg"
                  viewBox="0 0 20 20"
                  fill="currentColor"
                  className="h-3 w-3 text-white"
                >
                  <path d="M1 11.5v3a.5.5 0 00.5.5h17a.5.5 0 00.5-.5v-3H1zM18 7H9v3h10V7.5A.5.5 0 0018 7zM2 10h5V7.5A2.5 2.5 0 004.5 5 2.5 2.5 0 002 7.5V10z" />
                </svg>
              </div>
            </div>
          </AdvancedMarker>
        );
      })}

      {/* Hotel info window */}
      {selectedHotel && (
        <InfoWindow
          position={{ lat: selectedHotel.location.lat, lng: selectedHotel.location.lng }}
          onCloseClick={() => setSelectedHotel(null)}
          pixelOffset={[0, -30]}
        >
          <div className="p-1 min-w-[160px]">
            <h3 className="font-semibold text-sm" style={{ color: 'var(--theme-text-primary, #111827)' }}>{selectedHotel.name}</h3>
            <div className="flex items-center gap-2 mt-1 text-xs" style={{ color: 'var(--theme-text-muted, #6b7280)' }}>
              {selectedHotel.rating && <span>&#x2B50; {selectedHotel.rating.toFixed(1)}</span>}
              {selectedHotel.price && <span>${selectedHotel.price}/night</span>}
            </div>
          </div>
        </InfoWindow>
      )}
    </Map>
  );
}

/** Map legend overlay. */
export function TripMapLegend() {
  return (
    <div className="flex flex-wrap items-center gap-4 px-3 py-2 text-xs text-text-muted">
      <span className="flex items-center gap-1.5">
        <span className="h-3 w-3 rounded-full bg-indigo-500 border border-white shadow-sm" />
        City
      </span>
      <span className="flex items-center gap-1.5">
        <span className="h-3 w-3 rounded-full bg-amber-500 border border-white shadow-sm" />
        Hotel
      </span>
      <span className="flex items-center gap-1.5">
        <span className="w-4 border-t-2 border-dashed border-indigo-400" />
        Route
      </span>
    </div>
  );
}

export default TripMap;
