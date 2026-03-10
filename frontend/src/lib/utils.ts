import { clsx, type ClassValue } from "clsx"
import { twMerge } from "tailwind-merge"

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}

export function parseFareUsd(fareUsd: number | null | undefined, fareStr: string | null | undefined): number {
  if (fareUsd != null) return fareUsd;
  if (fareStr) {
    const match = fareStr.match(/[\d.]+/);
    if (match) return parseFloat(match[0]);
  }
  return 0;
}

export function formatDate(dateStr: string): string {
  try {
    const date = new Date(dateStr);
    return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
  } catch {
    return dateStr;
  }
}
