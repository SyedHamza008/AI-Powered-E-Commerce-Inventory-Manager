import React, { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api } from '../services/api';
import { 
  Users, 
  Plus, 
  Trash2, 
  X, 
  AlertCircle, 
  Mail, 
  Phone, 
  MapPin, 
  Truck, 
  Search, 
  Building2 
} from 'lucide-react';
import { toast } from 'sonner';

interface Supplier {
  id: number;
  name: string;
  contact_email: string;
  phone: string;
  address: string;
  product_count: number;
}

interface SupplierDashboardProps {
  currentUser: any;
}

export function SupplierDashboard({ currentUser }: SupplierDashboardProps) {
  const queryClient = useQueryClient();
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [searchFilter, setSearchFilter] = useState('');

  // Form State
  const [name, setName] = useState('');
  const [email, setEmail] = useState('');
  const [phone, setPhone] = useState('');
  const [address, setAddress] = useState('');
  const [formError, setFormError] = useState<string | null>(null);

  const { data: suppliers = [], isLoading } = useQuery<Supplier[]>({
    queryKey: ['suppliers'],
    queryFn: api.getSuppliers,
  });

  const createMutation = useMutation({
    mutationFn: api.createSupplier,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['suppliers'] });
      setIsModalOpen(false);
      resetForm();
    },
  });

  const deleteMutation = useMutation({
    mutationFn: api.deleteSupplier,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['suppliers'] });
    },
  });

  const resetForm = () => {
    setName('');
    setEmail('');
    setPhone('');
    setAddress('');
    setFormError(null);
  };

  const handleCreate = (e: React.FormEvent) => {
    e.preventDefault();
    if (!name.trim() || !email.trim()) {
      setFormError('Supplier Name and Contact Email are required.');
      return;
    }

    const promise = createMutation.mutateAsync({
      name: name.trim(),
      contact_email: email.trim().toLowerCase(),
      phone: phone.trim() || undefined,
      address: address.trim() || undefined,
    });

    toast.promise(promise, {
      loading: 'Registering supply partner...',
      success: 'Supplier registered successfully! 🚚',
      error: (err: Error) => err.message,
    });
  };

  const handleDelete = (sup: Supplier) => {
    if (!window.confirm(`Are you sure you want to remove supplier "${sup.name}"?`)) return;
    const promise = deleteMutation.mutateAsync(sup.id);
    toast.promise(promise, {
      loading: `Removing ${sup.name}...`,
      success: 'Supplier removed successfully! 🗑️',
      error: (err: Error) => err.message,
    });
  };

  const filteredSuppliers = suppliers.filter((s) => {
    const q = searchFilter.toLowerCase();
    return (
      s.name.toLowerCase().includes(q) ||
      s.contact_email.toLowerCase().includes(q) ||
      (s.address && s.address.toLowerCase().includes(q))
    );
  });

  const isAdmin = currentUser?.role === 'admin';

  return (
    <div className="space-y-6">
      {/* Top Banner & Actions */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h2 className="text-lg font-bold text-slate-900 flex items-center space-x-2">
            <Building2 className="w-5 h-5 text-indigo-600" />
            <span>Supply Chain Partners</span>
          </h2>
          <p className="text-xs text-slate-500">
            Registered wholesale vendors, fulfillment channels, and catalog allocations
          </p>
        </div>

        <div className="flex items-center space-x-3">
          <div className="relative">
            <Search className="w-3.5 h-3.5 absolute left-3 top-2.5 text-slate-400" />
            <input
              type="text"
              placeholder="Search partner, email, city..."
              value={searchFilter}
              onChange={(e) => setSearchFilter(e.target.value)}
              className="pl-8 pr-3 py-1.5 text-xs rounded-xl border border-slate-200 bg-white focus:outline-none focus:ring-2 focus:ring-indigo-500"
            />
          </div>

          {isAdmin && (
            <button
              onClick={() => setIsModalOpen(true)}
              className="flex items-center space-x-1.5 px-3.5 py-1.5 rounded-xl text-xs font-semibold bg-indigo-600 text-white hover:bg-indigo-700 shadow-sm transition"
            >
              <Plus className="w-4 h-4" />
              <span>Register Supplier</span>
            </button>
          )}
        </div>
      </div>

      {/* Directory Table */}
      <div className="bg-white rounded-2xl border border-slate-200 shadow-sm overflow-hidden">
        <table className="w-full text-left text-sm">
          <thead className="bg-slate-50 text-slate-500 text-xs uppercase tracking-wider border-b border-slate-100">
            <tr>
              <th className="px-6 py-3.5">Supplier Details</th>
              <th className="px-6 py-3.5">Contact Channels</th>
              <th className="px-6 py-3.5">Warehouse / Address</th>
              <th className="px-6 py-3.5 text-center">Active Catalog Lines</th>
              {isAdmin && <th className="px-6 py-3.5 text-right">Actions</th>}
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100">
            {isLoading ? (
              <tr>
                <td colSpan={5} className="p-8 text-center text-xs text-slate-400">Loading partners directory...</td>
              </tr>
            ) : filteredSuppliers.length === 0 ? (
              <tr>
                <td colSpan={5} className="p-8 text-center text-xs text-slate-400">
                  {searchFilter ? 'No suppliers match your search filter.' : 'No suppliers registered yet. Click "Register Supplier" to add one.'}
                </td>
              </tr>
            ) : (
              filteredSuppliers.map((sup) => (
                <tr key={sup.id} className="hover:bg-slate-50/60 transition">
                  {/* Supplier Name & ID */}
                  <td className="px-6 py-4">
                    <div className="font-semibold text-slate-900 flex items-center space-x-1.5">
                      <Building2 className="w-4 h-4 text-indigo-600" />
                      <span>{sup.name}</span>
                    </div>
                    <div className="text-[11px] text-slate-400 pl-5.5">Vendor ID: #{sup.id}</div>
                  </td>

                  {/* Contact Email & Phone */}
                  <td className="px-6 py-4 text-xs space-y-1">
                    <a
                      href={`mailto:${sup.contact_email}`}
                      className="flex items-center space-x-1.5 text-indigo-600 hover:text-indigo-800 transition"
                    >
                      <Mail className="w-3.5 h-3.5 flex-shrink-0" />
                      <span>{sup.contact_email}</span>
                    </a>
                    {sup.phone && (
                      <a
                        href={`tel:${sup.phone}`}
                        className="flex items-center space-x-1.5 text-slate-500 hover:text-slate-700 text-[11px] transition"
                      >
                        <Phone className="w-3 h-3 flex-shrink-0 text-slate-400" />
                        <span>{sup.phone}</span>
                      </a>
                    )}
                  </td>

                  {/* Location Address */}
                  <td className="px-6 py-4 text-xs text-slate-600">
                    {sup.address ? (
                      <div className="flex items-center space-x-1.5">
                        <MapPin className="w-3.5 h-3.5 text-slate-400 flex-shrink-0" />
                        <span className="truncate max-w-xs">{sup.address}</span>
                      </div>
                    ) : (
                      <span className="text-slate-300 italic">No address on file</span>
                    )}
                  </td>

                  {/* Assigned Products Count */}
                  <td className="px-6 py-4 text-center">
                    <span className="inline-flex items-center space-x-1.5 px-3 py-1 rounded-full text-xs font-semibold bg-indigo-50 text-indigo-700 border border-indigo-100">
                      <Truck className="w-3 h-3 text-indigo-500" />
                      <span>{sup.product_count} line(s)</span>
                    </span>
                  </td>

                  {/* Delete Action (Admins only) */}
                  {isAdmin && (
                    <td className="px-6 py-4 text-right">
                      <button
                        onClick={() => handleDelete(sup)}
                        disabled={deleteMutation.isPending}
                        className="p-1.5 rounded-lg text-slate-400 hover:text-rose-600 hover:bg-rose-50 transition"
                        title="Remove supplier"
                      >
                        <Trash2 className="w-4 h-4" />
                      </button>
                    </td>
                  )}
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      {/* Register Supplier Modal */}
      {isModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/60 backdrop-blur-sm animate-in fade-in duration-200">
          <div className="bg-white rounded-2xl shadow-2xl border border-slate-200 w-full max-w-md overflow-hidden">
            <div className="px-6 py-4 border-b border-slate-100 flex items-center justify-between bg-slate-50/70">
              <h3 className="text-sm font-bold text-slate-800 flex items-center space-x-2">
                <Building2 className="w-4 h-4 text-indigo-600" />
                <span>Register Supply Partner</span>
              </h3>
              <button 
                onClick={() => setIsModalOpen(false)} 
                className="p-1 rounded-lg text-slate-400 hover:text-slate-600"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            <form onSubmit={handleCreate} className="p-6 space-y-3.5">
              {formError && (
                <div className="p-2.5 rounded-lg bg-rose-50 border border-rose-200 text-rose-700 text-xs flex items-center space-x-1.5">
                  <AlertCircle className="w-4 h-4 flex-shrink-0" />
                  <span>{formError}</span>
                </div>
              )}

              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">Company / Vendor Name *</label>
                <input
                  type="text"
                  required
                  placeholder="e.g. Apex Global Supply"
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  className="w-full px-3 py-1.5 text-sm rounded-lg border border-slate-200 focus:outline-none focus:ring-2 focus:ring-indigo-500"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">Contact Email *</label>
                <input
                  type="email"
                  required
                  placeholder="orders@apexsupply.com"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  className="w-full px-3 py-1.5 text-sm rounded-lg border border-slate-200 focus:outline-none focus:ring-2 focus:ring-indigo-500"
                />
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-semibold text-slate-700 mb-1">Phone Number</label>
                  <input
                    type="text"
                    placeholder="+1 (555) 019-2834"
                    value={phone}
                    onChange={(e) => setPhone(e.target.value)}
                    className="w-full px-3 py-1.5 text-sm rounded-lg border border-slate-200 focus:outline-none focus:ring-2 focus:ring-indigo-500"
                  />
                </div>
                <div>
                  <label className="block text-xs font-semibold text-slate-700 mb-1">Location / Warehouse</label>
                  <input
                    type="text"
                    placeholder="Dallas, TX"
                    value={address}
                    onChange={(e) => setAddress(e.target.value)}
                    className="w-full px-3 py-1.5 text-sm rounded-lg border border-slate-200 focus:outline-none focus:ring-2 focus:ring-indigo-500"
                  />
                </div>
              </div>

              <div className="flex justify-end space-x-2 pt-2 border-t border-slate-100">
                <button
                  type="button"
                  onClick={() => setIsModalOpen(false)}
                  className="px-4 py-2 text-xs font-medium text-slate-600 hover:bg-slate-100 rounded-lg transition"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={createMutation.isPending}
                  className="px-4 py-2 text-xs font-semibold text-white bg-indigo-600 hover:bg-indigo-700 rounded-lg shadow-sm transition"
                >
                  {createMutation.isPending ? 'Registering...' : 'Register Partner'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}