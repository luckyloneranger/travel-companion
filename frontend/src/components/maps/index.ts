import { lazy } from 'react';

export const TripMap = lazy(() =>
  import('./TripMap').then(m => ({ default: m.TripMap })),
);

export const DayMap = lazy(() =>
  import('./DayMap').then(m => ({ default: m.DayMap })),
);
