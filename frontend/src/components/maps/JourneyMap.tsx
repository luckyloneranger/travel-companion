import { useMemo } from 'react';
import { Map, AdvancedMarker } from '@vis.gl/react-google-maps';
import { MapPin, Hotel } from 'lucide-react';
import type { V6CityStop, V6TravelLeg } from '@/types';
import { cityColorPalettes } from '@/components/V6JourneyPlanView/styles';

interface JourneyMapProps {
  cities: V6CityStop[];
  travelLegs: V6TravelLeg[];
  origin?: string;
}

export function JourneyMap({ cities }: JourneyMapProps) {
  // Calculate bounds to fit all cities
  const bounds = useMemo(() => {
    const coords = cities
      .filter(c => c.latitude != null && c.longitude != null)
      .map(c => ({ lat: c.latitude!, lng: c.longitude! }));

    // Add accommodation coords
    cities.forEach(c => {
      if (c.accommodation?.latitude && c.accommodation?.longitude) {
        coords.push({ lat: c.accommodation.latitude, lng: c.accommodation.longitude });
      }
    });

    if (coords.length === 0) return null;

    const lats = coords.map(c => c.lat);
    const lngs = coords.map(c => c.lng);

    return {
      north: Math.max(...lats) + 0.5,
      south: Math.min(...lats) - 0.5,
      east: Math.max(...lngs) + 0.5,
      west: Math.min(...lngs) - 0.5,
    };
  }, [cities]);

  if (!bounds) return null;

  const center = {
    lat: (bounds.north + bounds.south) / 2,
    lng: (bounds.east + bounds.west) / 2,
  };

  return (
    <div className="rounded-xl overflow-hidden border border-gray-200" style={{ height: 400 }}>
      <Map
        defaultCenter={center}
        defaultZoom={5}
        defaultBounds={bounds}
        gestureHandling="cooperative"
        disableDefaultUI={false}
        mapId="journey-map"
      >
        {/* City markers */}
        {cities.map((city, idx) => {
          if (city.latitude == null || city.longitude == null) return null;
          const palette = cityColorPalettes[idx % cityColorPalettes.length];
          return (
            <AdvancedMarker
              key={`city-${idx}`}
              position={{ lat: city.latitude, lng: city.longitude }}
              title={`${city.name} (${city.days} days)`}
            >
              <div
                className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-full text-white text-xs font-bold shadow-lg"
                style={{ backgroundColor: palette.accentColor }}
              >
                <MapPin className="h-3.5 w-3.5" />
                {city.name}
              </div>
            </AdvancedMarker>
          );
        })}

        {/* Hotel markers */}
        {cities.map((city, idx) => {
          const acc = city.accommodation;
          if (!acc?.latitude || !acc?.longitude) return null;
          return (
            <AdvancedMarker
              key={`hotel-${idx}`}
              position={{ lat: acc.latitude, lng: acc.longitude }}
              title={acc.name}
            >
              <div className="flex items-center gap-1 px-2 py-1 bg-purple-600 text-white text-xs font-semibold rounded-full shadow-lg">
                <Hotel className="h-3 w-3" />
                <span className="max-w-[80px] truncate">{acc.name}</span>
              </div>
            </AdvancedMarker>
          );
        })}
      </Map>
    </div>
  );
}
