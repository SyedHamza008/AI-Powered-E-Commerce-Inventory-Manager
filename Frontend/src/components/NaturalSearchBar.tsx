import React, { useState } from 'react';
import { useMutation } from '@tanstack/react-query';
import { api } from '../services/api';
import { Sparkles, Search, X, Filter } from 'lucide-react';
import { toast } from 'sonner';

interface NaturalSearchBarProps {
  onResultsFound: (results: any) => void;
  onClear: () => void;
  token?: string;
}

export function NaturalSearchBar({ onResultsFound, onClear, token }: NaturalSearchBarProps) {
  const [query, setQuery] = useState('');
  const [appliedExplanation, setAppliedExplanation] = useState<string | null>(null);
  const [appliedFilters, setAppliedFilters] = useState<Record<string, any> | null>(null);

  const searchMutation = useMutation({
    mutationFn: (searchPhrase: string) => api.naturalSearch(searchPhrase, token),
    onSuccess: (data) => {
      setAppliedExplanation(data.explanation);
      setAppliedFilters(data.applied_filters);
      onResultsFound(data);
      toast.success(`Found ${data.count} matching item(s)`, {
        description: data.explanation,
      });
    },
    onError: (err: Error) => {
      toast.error('Natural Search Failed', {
        description: err.message,
      });
    },
  });

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    if (!query.trim()) return;
    searchMutation.mutate(query.trim());
  };

  const handleClear = () => {
    setQuery('');
    setAppliedExplanation(null);
    setAppliedFilters(null);
    onClear();
  };

  return (
    <div className="w-full space-y-2">
      <form onSubmit={handleSearch} className="relative flex items-center">
        <div className="absolute left-3.5 text-indigo-500">
          <Sparkles className="w-4 h-4 animate-pulse" />
        </div>
        <input
          type="text"
          placeholder="Ask in natural language: e.g. 'Show electronics with fewer than 10 in stock'..."
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          className="w-full pl-10 pr-24 py-2 text-sm bg-white rounded-xl border border-indigo-200/80 shadow-sm focus:outline-none focus:ring-2 focus:ring-indigo-500 placeholder:text-slate-400"
        />
        <div className="absolute right-2 flex items-center space-x-1">
          {query && (
            <button
              type="button"
              onClick={handleClear}
              className="p-1 rounded-lg text-slate-400 hover:text-slate-600 hover:bg-slate-100 transition"
            >
              <X className="w-4 h-4" />
            </button>
          )}
          <button
            type="submit"
            disabled={searchMutation.isPending || !query.trim()}
            className="px-3 py-1 bg-indigo-600 hover:bg-indigo-700 text-white rounded-lg text-xs font-semibold disabled:opacity-50 transition flex items-center space-x-1"
          >
            <Search className="w-3 h-3" />
            <span>{searchMutation.isPending ? 'Searching...' : 'Search'}</span>
          </button>
        </div>
      </form>

      {/* Applied Filters Feedback Tags */}
      {appliedFilters && (
        <div className="flex flex-wrap items-center gap-1.5 text-xs text-slate-600 pt-1">
          <span className="flex items-center text-indigo-600 font-semibold text-[11px] mr-1">
            <Filter className="w-3 h-3 mr-1" />
            Filters:
          </span>
          {Object.entries(appliedFilters).map(([k, v]) => (
            <span
              key={k}
              className="px-2 py-0.5 rounded-full bg-indigo-50 border border-indigo-200 text-indigo-700 text-[11px] font-medium"
            >
              {k}: <strong className="text-indigo-900">{String(v)}</strong>
            </span>
          ))}
          <button
            onClick={handleClear}
            className="text-[11px] text-slate-400 hover:text-rose-600 underline ml-2 transition"
          >
            Reset
          </button>
        </div>
      )}
    </div>
  );
}