/**
 * ItineraryView Styles
 * 
 * Re-exports from central design system + component-specific utilities
 */

// Re-export everything from central design system
export {
  colorPalettes as dayColorPalettes,
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
  type ColorPalette as DayColorPalette,
} from '@/styles';

export { getCategoryIcon } from '@/styles/icons';

// Re-export shared utilities
export { formatDuration } from '@/components/shared/utils';

/** Get quality grade color based on semantic colors */
export const getGradeColor = (grade?: string): { bg: string; text: string; border: string } => {
  switch (grade?.toUpperCase()) {
    case 'A+':
    case 'A':
      return { bg: '#ecfdf5', text: '#059669', border: '#a7f3d0' };
    case 'A-':
    case 'B+':
      return { bg: '#f0fdf4', text: '#16a34a', border: '#bbf7d0' };
    case 'B':
    case 'B-':
      return { bg: '#fef9c3', text: '#ca8a04', border: '#fde047' };
    case 'C+':
    case 'C':
      return { bg: '#fff7ed', text: '#ea580c', border: '#fed7aa' };
    default:
      return { bg: '#f9fafb', text: '#6b7280', border: '#e5e7eb' };
  }
};
