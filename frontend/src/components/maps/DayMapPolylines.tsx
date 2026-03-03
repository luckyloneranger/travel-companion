import { useMap, useMapsLibrary } from '@vis.gl/react-google-maps';
import { useEffect } from 'react';

interface DayMapPolylinesProps {
  paths: { lat: number; lng: number }[][];
}

export function DayMapPolylines({ paths }: DayMapPolylinesProps) {
  const map = useMap();
  const mapsLib = useMapsLibrary('maps');

  useEffect(() => {
    if (!map || !mapsLib) return;

    const polylines = paths.map(path => {
      const polyline = new mapsLib.Polyline({
        path,
        strokeColor: '#6B5B95',
        strokeOpacity: 0.7,
        strokeWeight: 3,
        map,
      });
      return polyline;
    });

    return () => {
      polylines.forEach(p => p.setMap(null));
    };
  }, [map, mapsLib, paths]);

  return null;
}
