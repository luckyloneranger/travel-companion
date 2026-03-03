import { useCallback, useEffect, useMemo } from 'react';
import { Map, AdvancedMarker, useMap, useMapsLibrary } from '@vis.gl/react-google-maps';
import type { JourneyPlan, CityStop, Location } from '@/types';

interface TripMapProps {
  journey: JourneyPlan;
}

const MAP_ID = 'DEMO_MAP_ID';

/** Journey-level map showing all cities, hotels, and travel connections. */
export function TripMap({ journey }: TripMapProps) {
  const map = useMap();
  const coreLib = useMapsLibrary('core');

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
        >
          <div className="flex flex-col items-center">
            <span className="mb-1 rounded-full bg-indigo-600 px-2 py-0.5 text-xs font-semibold text-white shadow-md whitespace-nowrap">
              {city.name}
            </span>
            <div className="h-4 w-4 rounded-full border-2 border-white bg-indigo-500 shadow-md" />
          </div>
        </AdvancedMarker>
      ))}

      {/* Hotel / accommodation markers */}
      {citiesWithLocation.map((city, idx) => {
        const accom = city.accommodation;
        if (!accom?.location) return null;

        return (
          <AdvancedMarker
            key={`hotel-${idx}`}
            position={{ lat: accom.location.lat, lng: accom.location.lng }}
            title={accom.name}
          >
            <div className="flex flex-col items-center">
              <span className="mb-1 rounded bg-amber-500 px-1.5 py-0.5 text-[10px] font-medium text-white shadow whitespace-nowrap">
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
    </Map>
  );
}

export default TripMap;
