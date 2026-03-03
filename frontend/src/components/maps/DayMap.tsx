import { useCallback, useEffect, useMemo } from 'react';
import { Map, AdvancedMarker, useMap, useMapsLibrary } from '@vis.gl/react-google-maps';
import { DayMapPolylines } from './DayMapPolylines';
import type { DayPlan, Activity, Location } from '@/types';

interface DayMapProps {
  dayPlan: DayPlan;
}

const MAP_ID = 'DEMO_MAP_ID';

/** Day-level map showing numbered activity markers and route polylines. */
export function DayMap({ dayPlan }: DayMapProps) {
  const map = useMap();
  const coreLib = useMapsLibrary('core');

  // Filter activities with valid place locations
  const activitiesWithLocation = useMemo(
    () =>
      dayPlan.activities.filter(
        (a): a is Activity & { place: { location: Location } & Activity['place'] } =>
          a.place?.location !== null && a.place?.location !== undefined,
      ),
    [dayPlan.activities],
  );

  // Fit bounds to all activity locations
  const fitBounds = useCallback(() => {
    if (!map || !coreLib || activitiesWithLocation.length === 0) return;

    const bounds = new coreLib.LatLngBounds();
    for (const activity of activitiesWithLocation) {
      bounds.extend({
        lat: activity.place.location.lat,
        lng: activity.place.location.lng,
      });
    }
    map.fitBounds(bounds, { top: 50, right: 50, bottom: 50, left: 50 });
  }, [map, coreLib, activitiesWithLocation]);

  useEffect(() => {
    fitBounds();
  }, [fitBounds]);

  // Default center from first activity
  const defaultCenter = activitiesWithLocation.length > 0
    ? {
        lat: activitiesWithLocation[0].place.location.lat,
        lng: activitiesWithLocation[0].place.location.lng,
      }
    : { lat: 20, lng: 0 };

  return (
    <Map
      mapId={MAP_ID}
      defaultCenter={defaultCenter}
      defaultZoom={13}
      gestureHandling="greedy"
      disableDefaultUI={false}
      style={{ width: '100%', height: '100%' }}
    >
      {/* Numbered activity markers */}
      {activitiesWithLocation.map((activity, idx) => (
        <AdvancedMarker
          key={activity.id}
          position={{
            lat: activity.place.location.lat,
            lng: activity.place.location.lng,
          }}
          title={activity.place.name}
        >
          <div className="flex flex-col items-center">
            <span className="mb-1 max-w-[140px] truncate rounded bg-white/90 px-1.5 py-0.5 text-[10px] font-medium text-gray-800 shadow whitespace-nowrap">
              {activity.place.name}
            </span>
            <div className="flex h-6 w-6 items-center justify-center rounded-full border-2 border-white bg-indigo-600 text-xs font-bold text-white shadow-md">
              {idx + 1}
            </div>
          </div>
        </AdvancedMarker>
      ))}

      {/* Route polylines between activities */}
      <DayMapPolylines activities={activitiesWithLocation} />
    </Map>
  );
}

export default DayMap;
