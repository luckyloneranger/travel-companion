import { useEffect, useMemo } from 'react';
import { useMap, useMapsLibrary } from '@vis.gl/react-google-maps';
import { decodePolyline } from '@/utils/polyline';
import type { Activity } from '@/types';

interface DayMapPolylinesProps {
  activities: Activity[];
}

/** Travel mode to color mapping. */
const MODE_COLORS: Record<string, string> = {
  WALK: '#16a34a',    // green-600
  DRIVE: '#2563eb',   // blue-600
  TRANSIT: '#9333ea', // purple-600
};

/**
 * Renders decoded route polylines on the map for each activity
 * that has a route_to_next with a non-null polyline.
 */
export function DayMapPolylines({ activities }: DayMapPolylinesProps) {
  const map = useMap();
  const mapsLib = useMapsLibrary('maps');

  const segments = useMemo(() => {
    const result: { path: google.maps.LatLngLiteral[]; color: string }[] = [];

    for (const activity of activities) {
      const route = activity.route_to_next;
      if (!route?.polyline) continue;

      const decoded = decodePolyline(route.polyline);
      if (decoded.length < 2) continue;

      const color = MODE_COLORS[route.travel_mode] ?? '#6366f1';
      result.push({ path: decoded, color });
    }

    return result;
  }, [activities]);

  useEffect(() => {
    if (!map || !mapsLib || segments.length === 0) return;

    const polylines: google.maps.Polyline[] = [];

    for (const seg of segments) {
      const line = new mapsLib.Polyline({
        path: seg.path,
        geodesic: true,
        strokeColor: seg.color,
        strokeOpacity: 0.8,
        strokeWeight: 4,
        map,
      });
      polylines.push(line);
    }

    return () => {
      for (const p of polylines) p.setMap(null);
    };
  }, [map, mapsLib, segments]);

  // This component only draws on the map imperatively; it renders nothing.
  return null;
}

export default DayMapPolylines;
