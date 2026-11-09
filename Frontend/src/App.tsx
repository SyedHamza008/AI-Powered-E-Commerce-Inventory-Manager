import { useState, useEffect } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api, setAuthToken, getAuthToken } from './services/api';
import { 
  Package, 
  AlertTriangle, 
  Layers, 
  Users, 
  RefreshCw, 
  Search, 
  ArrowUpRight, 
  ArrowDownRight,
  History,
  Plus,
  MessageSquare,
  UserCheck,
  LogOut,
  LogIn
} from 'lucide-react';
import { toast } from 'sonner';
import { CreateProductDialog } from './components/CreateProductDialog';
import { AIInsightsPanel } from './components/AIInsightsPanel';
import { NaturalSearchBar } from './components/NaturalSearchBar';
import { AdminChatDrawer } from './components/AdminChatDrawer';
import { AuthModal } from './components/AuthModal';
import { CategoryDashboard } from './components/CategoryDashboard';
import { SupplierDashboard } from './components/SupplierDashboard';

// Type definitions...
interface Product {
  id: number;
  sku: string;
  name: string;
  unit_price: number;
  quantity: number;
  safety_stock_threshold: number;
  is_low_stock: boolean;
  category_name?: string;
}

interface ProductsResponse {
  items: Product[];
  pagination: any;
}

interface StockAdjustmentResponse {
  product_id: number;
  sku: string;
  previous_quantity: number;
  new_quantity: number;
  quantity_changed: number;
  reason: string;
  user_id: string;
}

function App() {
  const queryClient = useQueryClient();

  // Navigation State
  const [activeTab, setActiveTab] = useState<'products' | 'categories' | 'suppliers'>('products');

  // Search & Filter State
  const [searchTerm, setSearchTerm] = useState('');
  const [lowStockOnly, setLowStockOnly] = useState(false);
  const [selectedProductId, setSelectedProductId] = useState<number>(1);
  const [naturalSearchResults, setNaturalSearchResults] = useState<Product[] | null>(null);

  // Modals & Drawers
  const [isCreateOpen, setIsCreateOpen] = useState(false);
  const [isChatOpen, setIsChatOpen] = useState(false);
  const [isAuthOpen, setIsAuthOpen] = useState(false);
  const [currentUser, setCurrentUser] = useState<any>(null);

  useEffect(() => {
    if (getAuthToken()) {
      api.getMe()
        .then((user) => setCurrentUser(user))
        .catch(() => {
          setAuthToken(null);
          setCurrentUser(null);
        });
    }
  }, []);

  const handleLogout = () => {
    setAuthToken(null);
    setCurrentUser(null);
    toast.info('Logged out successfully.');
  };

  // Queries
  const { data: productsData, isLoading: loadingProducts, isFetching, error: productsError } = useQuery<ProductsResponse, Error>({
    queryKey: ['products', { search: searchTerm, low_stock: lowStockOnly }],
    queryFn: () => api.getProducts({ search: searchTerm, low_stock: lowStockOnly }),
  });

  const { data: historyData, isLoading: loadingHistory } = useQuery({
    queryKey: ['product-history', selectedProductId],
    queryFn: () => api.getProductHistory(selectedProductId),
    enabled: !!selectedProductId,
  });

  // Stock Mutation
  const stockMutation = useMutation<StockAdjustmentResponse, Error, { id: number; delta: number; reason: string }>({
    mutationFn: ({ id, delta, reason }) => api.adjustStock(id, { delta, reason }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['products'] });
      queryClient.invalidateQueries({ queryKey: ['product-history', selectedProductId] });
    },
  });

  const handleQuickAdjust = (id: number, delta: number, reason: string) => {
    const promise = stockMutation.mutateAsync({ id, delta, reason });
    toast.promise(promise, {
      loading: 'Updating stock ledger...',
      success: (data) => ({
        message: `Stock updated: ${data.quantity_changed > 0 ? '+' : ''}${data.quantity_changed} units`,
        description: `${data.sku} is now at ${data.new_quantity} (${data.reason})`,
      }),
      error: (err) => ({
        message: 'Adjustment Failed',
        description: err.message,
      }),
    });
  };

  const products = naturalSearchResults !== null ? naturalSearchResults : (productsData?.items || []);
  const isAdmin = currentUser?.role === 'admin';

  return (
    <div className="flex h-screen bg-slate-100 text-slate-800 font-sans antialiased">
      {/* Sidebar Navigation */}
      <aside className="w-64 bg-slate-900 text-slate-200 flex flex-col border-r border-slate-800">
        <div className="p-5 border-b border-slate-800 flex items-center space-x-3">
          <div className="p-2 bg-indigo-600 rounded-lg text-white">
            <Package className="w-5 h-5" />
          </div>
          <div>
            <h1 className="font-bold text-sm tracking-wide text-white">InvManager AI</h1>
            <p className="text-xs text-slate-400">Enterprise Control</p>
          </div>
        </div>

        {/* CLICKABLE NAVIGATION TABS */}
        <nav className="flex-1 p-4 space-y-1">
          <button
            onClick={() => setActiveTab('products')}
            className={`w-full flex items-center space-x-3 px-3 py-2.5 rounded-lg text-sm font-medium transition ${
              activeTab === 'products'
                ? 'bg-indigo-600 text-white shadow-sm'
                : 'text-slate-400 hover:bg-slate-800 hover:text-slate-200'
            }`}
          >
            <Package className="w-4 h-4" />
            <span>Products</span>
          </button>

          <button
            onClick={() => setActiveTab('categories')}
            className={`w-full flex items-center space-x-3 px-3 py-2.5 rounded-lg text-sm font-medium transition ${
              activeTab === 'categories'
                ? 'bg-indigo-600 text-white shadow-sm'
                : 'text-slate-400 hover:bg-slate-800 hover:text-slate-200'
            }`}
          >
            <Layers className="w-4 h-4" />
            <span>Categories</span>
          </button>

          <button
            onClick={() => setActiveTab('suppliers')}
            className={`w-full flex items-center space-x-3 px-3 py-2.5 rounded-lg text-sm font-medium transition ${
              activeTab === 'suppliers'
                ? 'bg-indigo-600 text-white shadow-sm'
                : 'text-slate-400 hover:bg-slate-800 hover:text-slate-200'
            }`}
          >
            <Users className="w-4 h-4" />
            <span>Suppliers</span>
          </button>

          <div className="pt-4 border-t border-slate-800">
            <button
              onClick={() => setIsChatOpen(true)}
              className="w-full flex items-center space-x-3 px-3 py-2.5 rounded-lg text-slate-400 hover:bg-slate-800 hover:text-slate-200 text-sm transition"
            >
              <MessageSquare className="w-4 h-4 text-indigo-400" />
              <span>AI Copilot</span>
            </button>
          </div>
        </nav>

        <div className="p-4 border-t border-slate-800 text-xs text-slate-500">
          Connected to Flask REST API
        </div>
      </aside>

      {/* Main Content Area */}
      <main className="flex-1 flex flex-col overflow-hidden">
        {/* Top Header */}
        <header className="h-16 bg-white border-b border-slate-200 px-6 flex items-center justify-between">
          <div className="flex items-center space-x-3">
            <span className="text-sm font-bold text-slate-900 capitalize">{activeTab} Management</span>
            {isFetching && (
              <span className="flex items-center space-x-1 text-xs text-indigo-600">
                <RefreshCw className="w-3 h-3 animate-spin" />
                <span>Syncing...</span>
              </span>
            )}
          </div>

          <div className="flex items-center space-x-3">
            {activeTab === 'products' && isAdmin && (
              <button
                onClick={() => setIsCreateOpen(true)}
                className="flex items-center space-x-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold bg-indigo-600 text-white hover:bg-indigo-700 shadow-sm transition"
              >
                <Plus className="w-3.5 h-3.5" />
                <span>New Product</span>
              </button>
            )}

            {/* User Session Status */}
            {currentUser ? (
              <div className="flex items-center space-x-2 bg-slate-100 py-1 px-2.5 rounded-lg border border-slate-200 text-xs">
                <UserCheck className="w-3.5 h-3.5 text-indigo-600" />
                <span className="font-semibold text-slate-800">{currentUser.username}</span>
                <span className="uppercase text-[9px] px-1.5 py-0.2 rounded bg-indigo-600 text-white font-bold">
                  {currentUser.role}
                </span>
                <button onClick={handleLogout} className="text-slate-400 hover:text-rose-600 ml-1" title="Logout">
                  <LogOut className="w-3.5 h-3.5" />
                </button>
              </div>
            ) : (
              <button
                onClick={() => setIsAuthOpen(true)}
                className="flex items-center space-x-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold bg-slate-800 text-white hover:bg-slate-900 transition"
              >
                <LogIn className="w-3.5 h-3.5" />
                <span>Sign In</span>
              </button>
            )}
          </div>
        </header>

        {/* VIEW ROUTING */}
        <div className="flex-1 overflow-y-auto p-6">
          {activeTab === 'products' && (
            <div className="space-y-6">
              {/* AI Insights & Recharts Banner */}
              <AIInsightsPanel onSelectProduct={(id) => setSelectedProductId(id)} />

              <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
                {/* Catalog Table */}
                <div className="lg:col-span-2 bg-white rounded-2xl border border-slate-200 shadow-sm flex flex-col overflow-hidden">
                  <div className="p-4 border-b border-slate-100 flex flex-col space-y-3">
                    <NaturalSearchBar 
                      onResultsFound={(data) => setNaturalSearchResults(data.items)}
                      onClear={() => setNaturalSearchResults(null)}
                    />
                    <div className="flex items-center justify-between">
                      <div className="relative flex-1 max-w-xs">
                        <Search className="w-3.5 h-3.5 absolute left-3 top-2.5 text-slate-400" />
                        <input
                          type="text"
                          placeholder="Filter SKU or name..."
                          value={searchTerm}
                          onChange={(e) => setSearchTerm(e.target.value)}
                          className="w-full pl-8 pr-3 py-1 text-xs rounded-lg border border-slate-200 focus:outline-none focus:ring-2 focus:ring-indigo-500"
                        />
                      </div>
                      <button
                        onClick={() => setLowStockOnly(!lowStockOnly)}
                        className={`flex items-center space-x-1.5 px-2.5 py-1 rounded-lg text-xs font-medium border transition ${
                          lowStockOnly ? 'bg-rose-50 border-rose-300 text-rose-700 font-semibold' : 'bg-white border-slate-200 text-slate-600'
                        }`}
                      >
                        <AlertTriangle className="w-3 h-3" />
                        <span>Low Stock</span>
                      </button>
                    </div>
                  </div>

                  <div className="overflow-x-auto flex-1">
                    {loadingProducts ? (
                      <div className="p-8 text-center text-xs text-slate-400">Loading catalog...</div>
                    ) : productsError ? (
                      <div className="p-8 text-center text-xs text-rose-600">Error: {productsError.message}</div>
                    ) : products.length === 0 ? (
                      <div className="p-8 text-center text-xs text-slate-400">No matching products found.</div>
                    ) : (
                      <table className="w-full text-left text-sm">
                        <thead className="bg-slate-50 text-slate-500 text-xs uppercase tracking-wider border-b border-slate-100">
                          <tr>
                            <th className="px-4 py-3">Product</th>
                            <th className="px-4 py-3">Category</th>
                            <th className="px-4 py-3 text-right">Price</th>
                            <th className="px-4 py-3 text-center">Stock</th>
                            <th className="px-4 py-3 text-right">Quick Adjust</th>
                          </tr>
                        </thead>
                        <tbody className="divide-y divide-slate-100">
                          {products.map((item) => (
                            <tr
                              key={item.id}
                              onClick={() => setSelectedProductId(item.id)}
                              className={`hover:bg-indigo-50/40 cursor-pointer transition ${
                                selectedProductId === item.id ? 'bg-indigo-50/60 font-medium' : ''
                              }`}
                            >
                              <td className="px-4 py-3">
                                <div className="font-medium text-slate-900">{item.name}</div>
                                <div className="text-xs text-slate-400">{item.sku}</div>
                              </td>
                              <td className="px-4 py-3 text-xs text-slate-600">{item.category_name}</td>
                              <td className="px-4 py-3 text-right text-slate-800">${item.unit_price.toFixed(2)}</td>
                              <td className="px-4 py-3 text-center">
                                <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-semibold ${
                                  item.is_low_stock ? 'bg-rose-100 text-rose-700' : 'bg-emerald-100 text-emerald-700'
                                }`}>
                                  {item.quantity} in stock
                                </span>
                              </td>
                              <td className="px-4 py-3 text-right" onClick={(e) => e.stopPropagation()}>
                                <div className="inline-flex space-x-1">
                                  <button
                                    disabled={stockMutation.isPending || item.quantity <= 0}
                                    onClick={() => handleQuickAdjust(item.id, -1, 'Quick dash decrement (-1)')}
                                    className="px-2 py-1 rounded bg-slate-100 hover:bg-rose-100 hover:text-rose-700 text-xs font-semibold disabled:opacity-40 transition"
                                    title="Decrease stock by 1"
                                  >
                                    -1
                                  </button>
                                  <button
                                    disabled={stockMutation.isPending}
                                    onClick={() => handleQuickAdjust(item.id, 1, 'Quick dash restock (+1)')}
                                    className="px-2 py-1 rounded bg-slate-100 hover:bg-emerald-100 hover:text-emerald-700 text-xs font-semibold disabled:opacity-40 transition"
                                    title="Increase stock by 1"
                                  >
                                    +1
                                  </button>
                                </div>
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    )}
                  </div>
                </div>

                {/* Audit History Timeline */}
                <div className="bg-white rounded-2xl border border-slate-200 shadow-sm flex flex-col">
                  <div className="p-4 border-b border-slate-100 flex items-center space-x-2">
                    <History className="w-4 h-4 text-indigo-600" />
                    <h3 className="font-semibold text-slate-800 text-sm">Audit History</h3>
                    <span className="text-xs text-slate-400">({historyData?.sku || 'Product'})</span>
                  </div>

                  <div className="p-4 flex-1 overflow-y-auto space-y-3">
                    {loadingHistory ? (
                      <p className="text-xs text-slate-400 text-center">Loading audit events...</p>
                    ) : !historyData?.items?.length ? (
                      <p className="text-xs text-slate-400 text-center">No audit records for this item yet.</p>
                    ) : (
                      historyData.items.map((event: any) => (
                        <div key={event.id} className="p-3 rounded-xl bg-slate-50 border border-slate-100 text-xs space-y-1">
                          <div className="flex items-center justify-between">
                            <span className={`font-semibold flex items-center ${
                              event.quantity_change > 0 ? 'text-emerald-600' : 'text-rose-600'
                            }`}>
                              {event.quantity_change > 0 ? <ArrowUpRight className="w-3.5 h-3.5 mr-0.5" /> : <ArrowDownRight className="w-3.5 h-3.5 mr-0.5" />}
                              {event.quantity_change > 0 ? `+${event.quantity_change}` : event.quantity_change} Units
                            </span>
                            <span className="text-slate-400 text-[10px]">{new Date(event.created_at).toLocaleTimeString()}</span>
                          </div>
                          <p className="text-slate-600 italic">"{event.reason}"</p>
                          <div className="text-[10px] text-slate-400 flex justify-between pt-1 border-t border-slate-200">
                            <span>By: {event.user_id}</span>
                            <span>Balance: {event.previous_quantity} → {event.new_quantity}</span>
                          </div>
                        </div>
                      ))
                    )}
                  </div>
                </div>
              </div>
            </div>
          )}

          {activeTab === 'categories' && <CategoryDashboard currentUser={currentUser} />}
          {activeTab === 'suppliers' && <SupplierDashboard currentUser={currentUser} />}
        </div>

        {/* Global Dialogs */}
        <CreateProductDialog isOpen={isCreateOpen} onClose={() => setIsCreateOpen(false)} />
        <AdminChatDrawer isOpen={isChatOpen} onClose={() => setIsChatOpen(false)} />
        <AuthModal isOpen={isAuthOpen} onClose={() => setIsAuthOpen(false)} onAuthSuccess={(user) => setCurrentUser(user)} />
      </main>
    </div>
  );
}

export default App;