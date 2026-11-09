import React from 'react';
import ReactDOM from 'react-dom/client';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { Toaster } from 'sonner';
import App from './App.jsx';
import './index.css';

// Create a query client with resilient default caching rules
const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 1000 * 30, // Data remains fresh for 30 seconds
      refetchOnWindowFocus: true, // Auto-sync when admin refocuses browser
      retry: 1,
    },
  },
});

// Fail fast if the mount point is missing from index.html
const rootElement = document.getElementById('root');
if (!rootElement) {
  throw new Error(
    "Root element not found. Make sure index.html contains <div id=\"root\"></div>"
  );
}

ReactDOM.createRoot(rootElement).render(
  <React.StrictMode>
    <QueryClientProvider client={queryClient}>
      <App />
      <Toaster position="top-right" richColors closeButton />
    </QueryClientProvider>
  </React.StrictMode>
);