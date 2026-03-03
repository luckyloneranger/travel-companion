import { useMemo } from 'react';
import { Map, AdvancedMarker } from '@vis.gl/react-google-maps';
import { Hotel } from 'lucide-react';
import type { V6Activity } from '@/types';
import { categoryStyles } from '@/styles/design-system';
import { decodePolyline } from '@/utils/polyline';
import { DayMapPolylines } from './DayMapPolylines';

interface DayMapProps {
  activities: V6Activity[];
}

export function DayMap({ activities }: DayMapProps) {
  // Calculate bounds from all activity locations
  const { bounds, center } = useMemo(() => {
    const coords = activities.map(a => a.place.location);
    if (coords.length === 0) return { bounds: null, center: { lat: 0, lng: 0 } };

    const lats = coords.map(c => c.lat);
    const lngs = coords.map(c => c.lng);

    const b = {
      north: Math.max(...lats) + 0.005,
      south: Math.min(...lats) - 0.005,
      east: Math.max(...lngs) + 0.005,
      west: Math.min(...lngs) - 0.005,
    };

    return {
      bounds: b,
      center: { lat: (b.north + b.south) / 2, lng: (b.east + b.west) / 2 },
    };
  }, [activities]);

  // Decode polylines for routes
  const routePaths = useMemo(() => {
    return activities
      .filter(a => a.route_to_next?.polyline)
      .map(a => decodePolyline(a.route_to_next!.polyline!));
  }, [activities]);

  if (!bounds || activities.length === 0) return null;

  return (
    <div className="rounded-xl overflow-hidden border border-gray-200" style={{ height: 350 }}>
      <Map
        defaultCenter={center}
        defaultZoom={13}
        defaultBounds={bounds}
        gestureHandling="cooperative"
        disableDefaultUI={false}
        mapId="day-map"
      >
        {/* Activity markers */}
        {activities.map((activity, idx) => {
          const category = activity.place.category?.toLowerCase() || 'default';
          const isAccommodation = category === 'accommodation';
          const style = categoryStyles[category] || categoryStyles.default;

          return (
            <AdvancedMarker
              key={idx}
              position={activity.place.location}
              title={activity.place.name}
            >
              {isAccommodation ? (
                <div className="w-8 h-8 rounded-full bg-purple-600 text-white flex items-center justify-center shadow-lg">
                  <Hotel className="h-4 w-4" />
                </div>
              ) : (
                <div
                  className="w-7 h-7 rounded-full text-white flex items-center justify-center text-xs font-bold shadow-lg"
                  style={{ background: style.gradient }}
                >
                  {idx + 1}
                </div>
              )}
            </AdvancedMarker>
          );
        })}

        {/* Route polylines */}
        <DayMapPolylines paths={routePaths} />
      </Map>
    </div>
  );
}
