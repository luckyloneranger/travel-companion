import { Gauge } from "lucide-react";

interface Variant {
  id: string;
  pace: string;
  budget: string;
  day_count: number;
  quality_score: number | null;
  status: string;
}

interface VariantPickerProps {
  variants: Variant[];
  onSelect: (variant: Variant) => void;
}

const PACES = ["relaxed", "moderate", "packed"] as const;
const BUDGETS = ["budget", "moderate", "luxury"] as const;

export default function VariantPicker({ variants, onSelect }: VariantPickerProps) {
  const lookup = new Map<string, Variant>();
  for (const v of variants) {
    lookup.set(`${v.pace}:${v.budget}`, v);
  }

  return (
    <div className="overflow-x-auto">
      <table className="w-full border-collapse text-sm">
        <thead>
          <tr>
            <th className="p-3 text-left text-xs font-semibold uppercase tracking-wider text-gray-500 dark:text-gray-400">
              Pace / Budget
            </th>
            {BUDGETS.map((b) => (
              <th
                key={b}
                className="p-3 text-center text-xs font-semibold uppercase tracking-wider text-gray-500 dark:text-gray-400"
              >
                {b}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {PACES.map((pace) => (
            <tr key={pace} className="border-t border-gray-200 dark:border-gray-700">
              <td className="p-3 font-medium capitalize text-gray-700 dark:text-gray-300">
                {pace}
              </td>
              {BUDGETS.map((budget) => {
                const v = lookup.get(`${pace}:${budget}`);
                return (
                  <td key={budget} className="p-3 text-center">
                    {v ? (
                      <button
                        onClick={() => onSelect(v)}
                        className="inline-flex flex-col items-center gap-1 rounded-lg border border-gray-200 bg-white px-4 py-2.5 shadow-sm transition-colors hover:border-indigo-400 hover:shadow-md dark:border-gray-600 dark:bg-gray-800 dark:hover:border-indigo-500"
                      >
                        <span className="text-sm font-semibold text-gray-900 dark:text-white">
                          {v.day_count}d
                        </span>
                        {v.quality_score != null && (
                          <span className="flex items-center gap-1 text-xs text-indigo-600 dark:text-indigo-400">
                            <Gauge className="h-3 w-3" />
                            {v.quality_score}
                          </span>
                        )}
                      </button>
                    ) : (
                      <span className="text-gray-300 dark:text-gray-600">&mdash;</span>
                    )}
                  </td>
                );
              })}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
