import { DollarSign, TrendingUp, TrendingDown, Utensils, Ticket, Hotel, Car } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import type { CostBreakdown } from '@/types';

interface BudgetSummaryProps {
  costBreakdown: CostBreakdown;
  totalDays: number;
}

export function BudgetSummary({ costBreakdown, totalDays }: BudgetSummaryProps) {
  if (!costBreakdown || costBreakdown.total_usd <= 0) return null;

  const dailyAvg = totalDays > 0 ? costBreakdown.total_usd / totalDays : costBreakdown.total_usd;
  const isOverBudget = costBreakdown.budget_remaining_usd != null && costBreakdown.budget_remaining_usd < 0;

  return (
    <Card className="border-border-default">
      <CardHeader className="pb-2">
        <CardTitle className="text-sm font-display font-semibold flex items-center gap-2">
          <DollarSign className="h-4 w-4 text-primary-600" />
          Budget Summary
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-3">
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
          {/* Total */}
          <div className="space-y-0.5">
            <p className="text-xs text-text-muted">Estimated Total</p>
            <p className="text-lg font-semibold text-text-primary">${costBreakdown.total_usd.toFixed(0)}</p>
          </div>

          {/* Daily Average */}
          <div className="space-y-0.5">
            <p className="text-xs text-text-muted">Per Day</p>
            <p className="text-lg font-semibold text-text-secondary">${dailyAvg.toFixed(0)}</p>
          </div>

          {/* Accommodation */}
          {costBreakdown.accommodation_usd > 0 && (
            <div className="space-y-0.5">
              <p className="text-xs text-text-muted flex items-center gap-1">
                <Hotel className="h-3 w-3" /> Accommodation
              </p>
              <p className="text-lg font-semibold text-text-secondary">${costBreakdown.accommodation_usd.toFixed(0)}</p>
            </div>
          )}

          {/* Transport */}
          {costBreakdown.transport_usd > 0 && (
            <div className="space-y-0.5">
              <p className="text-xs text-text-muted flex items-center gap-1">
                <Car className="h-3 w-3" /> Transport
              </p>
              <p className="text-lg font-semibold text-text-secondary">${costBreakdown.transport_usd.toFixed(0)}</p>
            </div>
          )}

          {/* Dining */}
          {costBreakdown.dining_usd > 0 && (
            <div className="space-y-0.5">
              <p className="text-xs text-text-muted flex items-center gap-1">
                <Utensils className="h-3 w-3" /> Dining
              </p>
              <p className="text-lg font-semibold text-text-secondary">${costBreakdown.dining_usd.toFixed(0)}</p>
            </div>
          )}

          {/* Activities */}
          {costBreakdown.activities_usd > 0 && (
            <div className="space-y-0.5">
              <p className="text-xs text-text-muted flex items-center gap-1">
                <Ticket className="h-3 w-3" /> Activities
              </p>
              <p className="text-lg font-semibold text-text-secondary">${costBreakdown.activities_usd.toFixed(0)}</p>
            </div>
          )}
        </div>

        {/* Budget comparison */}
        {costBreakdown.budget_usd != null && (
          <div className={`flex items-center justify-between rounded-md px-3 py-2 text-sm ${
            isOverBudget
              ? 'bg-red-50 dark:bg-red-950/30 text-red-700 dark:text-red-300'
              : 'bg-green-50 dark:bg-green-950/30 text-green-700 dark:text-green-300'
          }`}>
            <span className="flex items-center gap-1.5">
              {isOverBudget
                ? <TrendingUp className="h-4 w-4" />
                : <TrendingDown className="h-4 w-4" />
              }
              {isOverBudget ? 'Over budget' : 'Under budget'}
            </span>
            <span className="font-semibold">
              {isOverBudget ? '+' : ''}${Math.abs(costBreakdown.budget_remaining_usd!).toFixed(0)}
              <span className="text-xs font-normal ml-1">/ ${costBreakdown.budget_usd.toFixed(0)}</span>
            </span>
          </div>
        )}

        <p className="text-xs text-text-muted italic mt-2">
          * Estimates based on destination averages. Actual costs may vary.
        </p>
      </CardContent>
    </Card>
  );
}
