/**
 * Category Icons
 * 
 * Centralized icon mapping for activity categories
 */
import {
  MapPin,
  Sparkles,
  Sun,
  Utensils,
  Star,
  Coffee,
  Moon,
  ShoppingBag,
  TreePine,
  Landmark,
  Palette,
  Camera,
  Building2,
  Waves,
  Mountain,
  Heart,
  Music,
  Church,
  Plane,
  Train,
  Bus,
  Car,
  Route,
} from 'lucide-react';
import type { ReactNode } from 'react';

/**
 * Icon size variants
 */
export const iconSizes = {
  xs: 'h-3 w-3',
  sm: 'h-3.5 w-3.5',
  md: 'h-4 w-4',
  lg: 'h-5 w-5',
  xl: 'h-6 w-6',
} as const;

/**
 * Get icon component for a category
 */
export const getCategoryIcon = (category: string, size: keyof typeof iconSizes = 'sm'): ReactNode => {
  const sizeClass = iconSizes[size];
  
  const icons: Record<string, ReactNode> = {
    // Food & Dining
    food: <Utensils className={sizeClass} />,
    breakfast: <Coffee className={sizeClass} />,
    lunch: <Utensils className={sizeClass} />,
    dinner: <Moon className={sizeClass} />,
    restaurant: <Utensils className={sizeClass} />,
    cafe: <Coffee className={sizeClass} />,
    
    // Nature & Outdoors
    nature: <TreePine className={sizeClass} />,
    park: <TreePine className={sizeClass} />,
    beach: <Waves className={sizeClass} />,
    adventure: <Mountain className={sizeClass} />,
    
    // Culture & Arts
    landmark: <Landmark className={sizeClass} />,
    museum: <Palette className={sizeClass} />,
    culture: <Star className={sizeClass} />,
    art: <Palette className={sizeClass} />,
    history: <Building2 className={sizeClass} />,
    architecture: <Building2 className={sizeClass} />,
    religious: <Church className={sizeClass} />,
    
    // Entertainment & Lifestyle
    shopping: <ShoppingBag className={sizeClass} />,
    nightlife: <Moon className={sizeClass} />,
    entertainment: <Music className={sizeClass} />,
    relaxation: <Heart className={sizeClass} />,
    
    // Special
    highlight: <Sparkles className={sizeClass} />,
    morning: <Sun className={sizeClass} />,
    photography: <Camera className={sizeClass} />,
  };
  
  return icons[category?.toLowerCase()] || <MapPin className={sizeClass} />;
};

/**
 * Transport mode icons
 */
export const getTransportIcon = (mode: string, size: keyof typeof iconSizes = 'md'): ReactNode => {
  const sizeClass = iconSizes[size];
  
  const icons: Record<string, ReactNode> = {
    flight: <Plane className={sizeClass} />,
    train: <Train className={sizeClass} />,
    bus: <Bus className={sizeClass} />,
    drive: <Car className={sizeClass} />,
    car: <Car className={sizeClass} />,
  };
  
  return icons[mode?.toLowerCase()] || <Route className={sizeClass} />;
};
