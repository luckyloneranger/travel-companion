import { useCallback, useEffect, useMemo, useState } from 'react';
import { Map, AdvancedMarker, InfoWindow, useMap, useMapsLibrary } from '@vis.gl/react-google-maps';
import { DayMapPolylines } from './DayMapPolylines';
import type { DayPlan, Activity, Location } from '@/types';

interface DayMapProps {
  dayPlan: DayPlan;
  mapInstanceId?: string;
}

const MAP_ID = 'DEMO_MAP_ID';

/** Day-level map showing numbered activity markers and route polylines. */
export function DayMap({ dayPlan, mapInstanceId = 'day-map' }: DayMapProps) {
  const map = useMap(mapInstanceId);
  const coreLib = useMapsLibrary('core');
  const [selectedActivity, setSelectedActivity] = useState<{ activity: Activity; index: number } | null>(null);

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
      id={mapInstanceId}
      mapId={MAP_ID}
      defaultCenter={defaultCenter}
      defaultZoom={13}
      gestureHandling="greedy"
      disableDefaultUI={false}
      fullscreenControl={false}
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
          onClick={() => setSelectedActivity({ activity, index: idx })}
        >
          <div className="flex flex-col items-center cursor-pointer">
            <span className="mb-1 max-w-[140px] truncate rounded bg-white/90 px-1.5 py-0.5 text-xs font-medium text-gray-800 shadow whitespace-nowrap">
              {activity.place.name}
            </span>
            <div className="flex h-6 w-6 items-center justify-center rounded-full border-2 border-white bg-indigo-600 text-xs font-bold text-white shadow-md">
              {idx + 1}
            </div>
          </div>
        </AdvancedMarker>
      ))}

      {/* Activity info window */}
      {selectedActivity && selectedActivity.activity.place?.location && (
        <InfoWindow
          position={{
            lat: selectedActivity.activity.place.location.lat,
            lng: selectedActivity.activity.place.location.lng,
          }}
          onCloseClick={() => setSelectedActivity(null)}
          pixelOffset={[0, -35]}
        >
          <div className="p-1 min-w-[180px] max-w-[260px]">
            <h3 className="font-semibold text-sm text-gray-900">{selectedActivity.activity.place.name}</h3>
            <div className="flex flex-wrap items-center gap-2 mt-1 text-xs text-gray-500">
              {selectedActivity.activity.time_start && (
                <span>🕐 {selectedActivity.activity.time_start}{selectedActivity.activity.time_end ? ` – ${selectedActivity.activity.time_end}` : ''}</span>
              )}
              {selectedActivity.activity.duration_minutes && selectedActivity.activity.duration_minutes > 0 && (
                <span>{selectedActivity.activity.duration_minutes} min</span>
              )}
            </div>
            {selectedActivity.activity.place.category && (
              <span className="inline-block mt-1 rounded bg-gray-100 px-1.5 py-0.5 text-xs text-gray-600 capitalize">
                {selectedActivity.activity.place.category}
              </span>
            )}
            {selectedActivity.activity.estimated_cost_usd != null && selectedActivity.activity.estimated_cost_usd > 0 && (
              <p className="text-xs text-gray-500 mt-1">💰 ~${selectedActivity.activity.estimated_cost_usd}</p>
            )}
            {selectedActivity.activity.place.rating && (
              <p className="text-xs text-gray-500 mt-0.5">⭐ {selectedActivity.activity.place.rating.toFixed(1)}</p>
            )}
          </div>
        </InfoWindow>
      )}

      {/* Route polylines between activities */}
      <DayMapPolylines activities={activitiesWithLocation} />
    </Map>
  );
}

/** Day map route legend. */
export function DayMapLegend() {
  return (
    <div className="flex items-center gap-4 px-3 py-2 text-xs text-text-muted">
      <span className="flex items-center gap-1.5">
        <span className="w-4 border-t-2 border-green-600" />
        Walk
      </span>
      <span className="flex items-center gap-1.5">
        <span className="w-4 border-t-2 border-blue-600" />
        Drive
      </span>
      <span className="flex items-center gap-1.5">
        <span className="w-4 border-t-2 border-purple-600" />
        Transit
      </span>
    </div>
  );
}

export default DayMap;
