/**
 * V6JourneyPlanView Styles
 * 
 * Re-exports from central design system + component-specific utilities
 */
import { Plane, Train, Bus, Car, Route } from 'lucide-react';
import type { ReactNode } from 'react';

// Re-export everything from central design system
export {
  colorPalettes as cityColorPalettes,
  lightPalettes,
  getLightPalette,
  headerGradients,
  categoryStyles,
  shadows,
  cardStyles,
  buttonStyles,
  glass,
  transitions,
  buildGradient,
  gradientStyle,
  glassStyle,
  getCategoryStyle,
  isMealCategory as isMealActivity,
  type ColorPalette as CityColorPalette,
  type LightPalette,
} from '@/styles';

export { getCategoryIcon } from '@/styles/icons';

// ============================================================================
// TRANSPORT ICONS (Journey-specific)
// ============================================================================

export const transportIcons: Record<string, ReactNode> = {
  flight: <Plane className="h-4 w-4" />,
  train: <Train className="h-4 w-4" />,
  bus: <Bus className="h-4 w-4" />,
  drive: <Car className="h-4 w-4" />,
  car: <Car className="h-4 w-4" />,
  default: <Route className="h-4 w-4" />,
};

export const getTransportIcon = (mode: string): ReactNode =>
  transportIcons[mode?.toLowerCase()] || transportIcons.default;

// Re-export shared utilities
export { formatDuration } from '@/components/shared/utils';