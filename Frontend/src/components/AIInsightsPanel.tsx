import { useQuery } from '@tanstack/react-query';
import { api } from '../services/api';
import { Sparkles, RefreshCw, ArrowRight } from 'lucide-react';
import { CategoryStockChart } from './CategoryStockChart';

interface AIInsightsProps {
  token?: string;
  onSelectProduct?: (id: number) => void;
}

export function AIInsightsPanel({ token, onSelectProduct }: AIInsightsProps) {
  const { data, isLoading, isFetching, error, refetch } = useQuery({
    queryKey: ['ai-insights'],
    queryFn: () => api.getInsights(token),
    staleTime: 1000 * 60 * 2, // Fresh for 2 minutes
  });

  const analysis = data?.analysis;
  const metrics = data?.metrics;

  const isHighRisk = analysis?.risk_level === 'HIGH';

  return (
    <div className="bg-gradient-to-br from-indigo-900 via-slate-900 to-slate-950 text-white rounded-2xl p-6 shadow-xl border border-indigo-500/20 flex flex-col space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between border-b border-indigo-500/20 pb-4">
        <div className="flex items-center space-x-2.5">
          <div className="p-2 rounded-xl bg-indigo-500/20 text-indigo-400 border border-indigo-500/30">
            <Sparkles className="w-5 h-5 animate-pulse" />
          </div>
          <div>
            <h2 className="font-bold text-sm tracking-wide flex items-center space-x-2">
              <span>AI Inventory Risk Insights</span>
              {analysis && (
                <span className={`text-[10px] uppercase font-bold px-2 py-0.5 rounded-full border ${
                  isHighRisk 
                    ? 'bg-rose-500/20 border-rose-500/40 text-rose-300' 
                    : 'bg-emerald-500/20 border-emerald-500/40 text-emerald-300'
                }`}>
                  {analysis.risk_level} RISK
                </span>
              )}
            </h2>
            <p className="text-xs text-slate-400">Grounded analysis based on live stock metrics</p>
          </div>
        </div>

        <button
          onClick={() => refetch()}
          disabled={isFetching}
          className="p-1.5 rounded-lg bg-slate-800/80 hover:bg-slate-700 text-slate-300 hover:text-white transition disabled:opacity-50 text-xs flex items-center space-x-1"
          title="Refresh Analysis"
        >
          <RefreshCw className={`w-3.5 h-3.5 ${isFetching ? 'animate-spin text-indigo-400' : ''}`} />
          <span className="hidden sm:inline">Re-analyze</span>
        </button>
      </div>

      {/* Content */}
      {isLoading ? (
        <div className="py-8 text-center text-xs text-slate-400 flex flex-col items-center justify-center space-y-2">
          <RefreshCw className="w-5 h-5 animate-spin text-indigo-400" />
          <span>Synthesizing database metrics...</span>
        </div>
      ) : error ? (
        <div className="p-4 rounded-xl bg-rose-500/10 border border-rose-500/30 text-rose-300 text-xs">
          ⚠️ Unable to load insights: {(error as Error).message}
        </div>
      ) : (
        <div className="space-y-4">
          {/* Executive Summary */}
          <div className="p-3.5 rounded-xl bg-slate-800/60 border border-slate-700/60 text-xs text-slate-200 leading-relaxed">
            {analysis?.summary}
          </div>

          {/* Quick Metrics Cards */}
          <div className="grid grid-cols-3 gap-3 text-center">
            <div className="p-2.5 rounded-xl bg-slate-800/40 border border-slate-700/40">
              <span className="text-[10px] text-slate-400 uppercase tracking-wider block">Catalog</span>
              <span className="text-base font-bold text-white">{metrics?.total_products}</span>
            </div>
            <div className="p-2.5 rounded-xl bg-slate-800/40 border border-slate-700/40">
              <span className="text-[10px] text-slate-400 uppercase tracking-wider block">Units on Hand</span>
              <span className="text-base font-bold text-indigo-300">{metrics?.total_units_in_stock}</span>
            </div>
            <div className="p-2.5 rounded-xl bg-slate-800/40 border border-slate-700/40">
              <span className="text-[10px] text-slate-400 uppercase tracking-wider block">At Risk</span>
              <span className={`text-base font-bold ${metrics?.low_stock_count > 0 ? 'text-rose-400' : 'text-emerald-400'}`}>
                {metrics?.low_stock_count}
              </span>
            </div>
          </div>

          {/* Category Distribution Chart */}
          <div className="p-3.5 rounded-xl bg-slate-800/40 border border-slate-700/40 space-y-1">
            <div className="flex items-center justify-between">
              <span className="text-[11px] font-semibold text-slate-300 uppercase tracking-wider">
                Category Stock Breakdown
              </span>
              <span className="text-[10px] text-amber-400 font-medium">
                Dashed Line: Safety Benchmark
              </span>
            </div>
            
            {/* Automatically renders the ReferenceLine watermark */}
            <CategoryStockChart data={metrics?.categories} safetyThreshold={15} />
          </div>

          {/* Actionable Recommendations */}
          {analysis?.recommendations?.length > 0 && (
            <div className="space-y-2">
              <span className="text-[11px] font-semibold text-slate-300 uppercase tracking-wider block">
                Recommended Actions:
              </span>
              <div className="space-y-2 max-h-48 overflow-y-auto pr-1">
                {analysis.recommendations.map((rec: any, idx: number) => (
                  <div
                    key={idx}
                    className="p-3 rounded-xl bg-slate-800/80 border border-slate-700/80 flex items-start justify-between space-x-3 text-xs hover:border-indigo-500/40 transition cursor-pointer"
                    onClick={() => onSelectProduct && onSelectProduct(rec.product_id)}
                  >
                    <div className="space-y-0.5">
                      <div className="flex items-center space-x-2">
                        <span className="font-semibold text-indigo-300">{rec.sku}</span>
                        <span className="text-[9px] px-1.5 py-0.2 rounded bg-rose-500/20 text-rose-300 border border-rose-500/30">
                          {rec.urgency} URGENCY
                        </span>
                      </div>
                      <p className="text-slate-300 text-[11px] leading-snug">{rec.suggested_action}</p>
                    </div>
                    <ArrowRight className="w-3.5 h-3.5 text-slate-400 flex-shrink-0 mt-1" />
                  </div>
                ))}
              </div>
            </div>
          )}

          <div className="text-[10px] text-slate-500 text-right">
            Provider: {analysis?.provider_used} • Recommendations are advisory
          </div>
        </div>
      )}
    </div>
  );
}