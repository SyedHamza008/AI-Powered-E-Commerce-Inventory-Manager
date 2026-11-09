import React, { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api } from '../services/api';
import { 
  X, 
  Plus, 
  AlertCircle, 
  Building2, 
  Mail, 
  Phone, 
  MapPin, 
  Check, 
  UserPlus 
} from 'lucide-react';
import { toast } from 'sonner';

interface Category {
  id: number;
  name: string;
}

interface Supplier {
  id: number;
  name: string;
  contact_email: string;
  phone?: string;
  address?: string;
}

interface CreateProductDialogProps {
  isOpen: boolean;
  onClose: () => void;
}

export function CreateProductDialog({ isOpen, onClose }: CreateProductDialogProps) {
  const queryClient = useQueryClient();

  // Primary Product Form State
  const [sku, setSku] = useState('');
  const [name, setName] = useState('');
  const [description, setDescription] = useState('');
  const [categoryId, setCategoryId] = useState<number | ''>('');
  const [unitPrice, setUnitPrice] = useState<number | ''>('');
  const [quantity, setQuantity] = useState<number | ''>(0);
  const [safetyThreshold, setSafetyThreshold] = useState<number | ''>(5);
  const [selectedSuppliers, setSelectedSuppliers] = useState<number[]>([]);
  const [formError, setFormError] = useState<string | null>(null);

  // Quick Supplier Sub-Modal State
  const [isAddingSupplier, setIsAddingSupplier] = useState(false);
  const [newSupName, setNewSupName] = useState('');
  const [newSupEmail, setNewSupEmail] = useState('');
  const [newSupPhone, setNewSupPhone] = useState('');
  const [newSupAddress, setNewSupAddress] = useState('');
  const [supFormError, setSupFormError] = useState<string | null>(null);

  // Queries
  const { data: categories = [] } = useQuery<Category[]>({
    queryKey: ['categories'],
    queryFn: () => api.getCategories(),
    enabled: isOpen,
  });

  const { data: suppliers = [] } = useQuery<Supplier[]>({
    queryKey: ['suppliers'],
    queryFn: () => api.getSuppliers(),
    enabled: isOpen,
  });

  // Product Creation Mutation
  const createProductMutation = useMutation({
    mutationFn: api.createProduct,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['products'] });
      resetProductForm();
      onClose();
    },
  });

  // Inline Supplier Quick-Registration Mutation
  const registerSupplierMutation = useMutation({
    mutationFn: api.createSupplier,
    onSuccess: (newSupplier: Supplier) => {
      queryClient.invalidateQueries({ queryKey: ['suppliers'] });
      // Automatically select the newly registered supplier
      setSelectedSuppliers((prev) => [...prev, newSupplier.id]);
      toast.success(`Supplier "${newSupplier.name}" registered and assigned! 🚚`);
      resetSupplierForm();
      setIsAddingSupplier(false);
    },
    onError: (err: Error) => {
      setSupFormError(err.message);
    },
  });

  const resetProductForm = () => {
    setSku('');
    setName('');
    setDescription('');
    setCategoryId('');
    setUnitPrice('');
    setQuantity(0);
    setSafetyThreshold(5);
    setSelectedSuppliers([]);
    setFormError(null);
  };

  const resetSupplierForm = () => {
    setNewSupName('');
    setNewSupEmail('');
    setNewSupPhone('');
    setNewSupAddress('');
    setSupFormError(null);
  };

  const toggleSupplier = (id: number) => {
    setSelectedSuppliers((prev) =>
      prev.includes(id) ? prev.filter((sId) => sId !== id) : [...prev, id]
    );
  };

  const handleProductSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setFormError(null);

    if (!sku.trim()) {
      setFormError('Product SKU code is required.');
      return;
    }
    if (!name.trim()) {
      setFormError('Product Name is required.');
      return;
    }
    if (!categoryId) {
      setFormError('Please select a Category.');
      return;
    }
    if (unitPrice === '' || Number(unitPrice) < 0) {
      setFormError('Price must be a valid non-negative number.');
      return;
    }

    const payload = {
      sku: sku.trim().toUpperCase(),
      name: name.trim(),
      description: description.trim() || undefined,
      category_id: Number(categoryId),
      unit_price: Number(unitPrice),
      quantity: Number(quantity) || 0,
      safety_stock_threshold: Number(safetyThreshold) || 5,
      supplier_ids: selectedSuppliers,
    };

    const promise = createProductMutation.mutateAsync(payload);
    toast.promise(promise, {
      loading: 'Registering product in inventory...',
      success: (data: any) => ({
        message: 'Product Created Successfully! 🎉',
        description: `${data.name} (${data.sku}) added to catalog.`,
      }),
      error: (err: Error) => ({
        message: 'Failed to Create Product',
        description: err.message,
      }),
    });
  };

  const handleQuickSupplierSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setSupFormError(null);

    if (!newSupName.trim() || !newSupEmail.trim()) {
      setSupFormError('Supplier Name and Contact Email are required.');
      return;
    }

    registerSupplierMutation.mutate({
      name: newSupName.trim(),
      contact_email: newSupEmail.trim().toLowerCase(),
      phone: newSupPhone.trim() || undefined,
      address: newSupAddress.trim() || undefined,
    });
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/60 backdrop-blur-sm animate-in fade-in duration-200">
      <div 
        className="bg-white rounded-2xl shadow-2xl border border-slate-200 w-full max-w-2xl overflow-hidden flex flex-col max-h-[92vh]"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Modal Header */}
        <div className="px-6 py-4 border-b border-slate-100 flex items-center justify-between bg-slate-50/70">
          <div>
            <h2 className="text-base font-bold text-slate-900">Add New Catalog Product</h2>
            <p className="text-xs text-slate-500">Configure item details, pricing, safety levels, and vendor sourcing</p>
          </div>
          <button 
            onClick={onClose}
            className="p-1.5 rounded-lg text-slate-400 hover:text-slate-600 hover:bg-slate-100 transition"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Modal Body */}
        <form onSubmit={handleProductSubmit} className="p-6 overflow-y-auto space-y-4">
          {formError && (
            <div className="p-3 rounded-lg bg-rose-50 border border-rose-200 text-rose-700 text-xs flex items-center space-x-2">
              <AlertCircle className="w-4 h-4 flex-shrink-0" />
              <span>{formError}</span>
            </div>
          )}

          {/* SKU and Category */}
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1">SKU Code *</label>
              <input
                type="text"
                placeholder="e.g. ELEC-KEY-01"
                value={sku}
                onChange={(e) => setSku(e.target.value)}
                className="w-full px-3 py-2 text-sm rounded-lg border border-slate-200 focus:outline-none focus:ring-2 focus:ring-indigo-500 uppercase"
              />
            </div>
            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1">Category *</label>
              <select
                value={categoryId}
                onChange={(e) => setCategoryId(Number(e.target.value) || '')}
                className="w-full px-3 py-2 text-sm rounded-lg border border-slate-200 focus:outline-none focus:ring-2 focus:ring-indigo-500 bg-white"
              >
                <option value="">Select Category...</option>
                {categories.map((c) => (
                  <option key={c.id} value={c.id}>
                    {c.name}
                  </option>
                ))}
              </select>
            </div>
          </div>

          {/* Product Name */}
          <div>
            <label className="block text-xs font-semibold text-slate-700 mb-1">Product Title *</label>
            <input
              type="text"
              placeholder="e.g. Logitech MX Master 3S Wireless Mouse"
              value={name}
              onChange={(e) => setName(e.target.value)}
              className="w-full px-3 py-2 text-sm rounded-lg border border-slate-200 focus:outline-none focus:ring-2 focus:ring-indigo-500"
            />
          </div>

          {/* Description */}
          <div>
            <label className="block text-xs font-semibold text-slate-700 mb-1">Description (Optional)</label>
            <textarea
              rows={2}
              placeholder="Technical specs, warranty notes, packaging info..."
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              className="w-full px-3 py-2 text-sm rounded-lg border border-slate-200 focus:outline-none focus:ring-2 focus:ring-indigo-500"
            />
          </div>

          {/* Metrics */}
          <div className="grid grid-cols-3 gap-3">
            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1">Unit Price ($) *</label>
              <input
                type="number"
                step="0.01"
                min="0"
                placeholder="0.00"
                value={unitPrice}
                onChange={(e) => setUnitPrice(e.target.value === '' ? '' : Number(e.target.value))}
                className="w-full px-3 py-2 text-sm rounded-lg border border-slate-200 focus:outline-none focus:ring-2 focus:ring-indigo-500"
              />
            </div>
            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1">Starting Stock *</label>
              <input
                type="number"
                min="0"
                placeholder="0"
                value={quantity}
                onChange={(e) => setQuantity(e.target.value === '' ? '' : Number(e.target.value))}
                className="w-full px-3 py-2 text-sm rounded-lg border border-slate-200 focus:outline-none focus:ring-2 focus:ring-indigo-500"
              />
            </div>
            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1">Safety Threshold</label>
              <input
                type="number"
                min="0"
                placeholder="5"
                value={safetyThreshold}
                onChange={(e) => setSafetyThreshold(e.target.value === '' ? '' : Number(e.target.value))}
                className="w-full px-3 py-2 text-sm rounded-lg border border-slate-200 focus:outline-none focus:ring-2 focus:ring-indigo-500"
              />
            </div>
          </div>

          {/* SUPPLIERS SECTION WITH INLINE REGISTRATION OPTION */}
          <div className="pt-2 border-t border-slate-100">
            <div className="flex items-center justify-between mb-2">
              <div>
                <label className="block text-xs font-bold text-slate-800">
                  Assigned Suppliers & Wholesale Partners
                </label>
                <p className="text-[11px] text-slate-400">
                  Select existing suppliers or register a new partner below
                </p>
              </div>
              <button
                type="button"
                onClick={() => setIsAddingSupplier(!isAddingSupplier)}
                className="inline-flex items-center space-x-1 text-xs font-semibold text-indigo-600 hover:text-indigo-800 transition"
              >
                <UserPlus className="w-3.5 h-3.5" />
                <span>{isAddingSupplier ? 'Close Partner Form' : '+ Register New Partner'}</span>
              </button>
            </div>

            {/* Embedded Inline Supplier Registration Form */}
            {isAddingSupplier && (
              <div className="p-4 rounded-xl bg-indigo-50/60 border border-indigo-200/80 mb-3 space-y-3 animate-in fade-in slide-in-from-top-2">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-bold text-indigo-900 flex items-center space-x-1.5">
                    <Building2 className="w-4 h-4 text-indigo-600" />
                    <span>Quick-Register Supply Partner</span>
                  </span>
                  <span className="text-[10px] text-indigo-600 font-medium">Adds partner directly to database</span>
                </div>

                {supFormError && (
                  <div className="p-2 rounded bg-rose-100 text-rose-700 text-xs flex items-center space-x-1">
                    <AlertCircle className="w-3.5 h-3.5" />
                    <span>{supFormError}</span>
                  </div>
                )}

                <div className="grid grid-cols-2 gap-2">
                  <input
                    type="text"
                    placeholder="Vendor Name * (e.g. Apex Tech)"
                    value={newSupName}
                    onChange={(e) => setNewSupName(e.target.value)}
                    className="px-2.5 py-1.5 text-xs rounded-lg border border-indigo-200 focus:outline-none focus:ring-2 focus:ring-indigo-500 bg-white"
                  />
                  <input
                    type="email"
                    placeholder="Contact Email * (e.g. sales@apex.com)"
                    value={newSupEmail}
                    onChange={(e) => setNewSupEmail(e.target.value)}
                    className="px-2.5 py-1.5 text-xs rounded-lg border border-indigo-200 focus:outline-none focus:ring-2 focus:ring-indigo-500 bg-white"
                  />
                </div>

                <div className="grid grid-cols-2 gap-2">
                  <input
                    type="text"
                    placeholder="Phone (e.g. +1 555-0199)"
                    value={newSupPhone}
                    onChange={(e) => setNewSupPhone(e.target.value)}
                    className="px-2.5 py-1.5 text-xs rounded-lg border border-indigo-200 focus:outline-none focus:ring-2 focus:ring-indigo-500 bg-white"
                  />
                  <input
                    type="text"
                    placeholder="Location / Warehouse (e.g. Chicago, IL)"
                    value={newSupAddress}
                    onChange={(e) => setNewSupAddress(e.target.value)}
                    className="px-2.5 py-1.5 text-xs rounded-lg border border-indigo-200 focus:outline-none focus:ring-2 focus:ring-indigo-500 bg-white"
                  />
                </div>

                <div className="flex justify-end space-x-2 pt-1">
                  <button
                    type="button"
                    onClick={() => {
                      resetSupplierForm();
                      setIsAddingSupplier(false);
                    }}
                    className="px-3 py-1 text-xs text-slate-600 hover:bg-slate-200/60 rounded-md transition"
                  >
                    Cancel
                  </button>
                  <button
                    type="button"
                    disabled={registerSupplierMutation.isPending}
                    onClick={handleQuickSupplierSubmit}
                    className="px-3 py-1 text-xs font-semibold text-white bg-indigo-600 hover:bg-indigo-700 rounded-md transition flex items-center space-x-1"
                  >
                    <Plus className="w-3.5 h-3.5" />
                    <span>{registerSupplierMutation.isPending ? 'Saving...' : 'Save & Select Partner'}</span>
                  </button>
                </div>
              </div>
            )}

            {/* Detailed Supplier List Selector Cards */}
            {suppliers.length === 0 ? (
              <div className="p-4 rounded-xl border border-dashed border-slate-200 text-center text-xs text-slate-400">
                No registered suppliers yet. Click "+ Register New Partner" above to add your first supplier.
              </div>
            ) : (
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 max-h-48 overflow-y-auto pr-1">
                {suppliers.map((sup) => {
                  const isSelected = selectedSuppliers.includes(sup.id);
                  return (
                    <div
                      key={sup.id}
                      onClick={() => toggleSupplier(sup.id)}
                      className={`p-2.5 rounded-xl border text-xs cursor-pointer transition flex items-start justify-between ${
                        isSelected
                          ? 'bg-indigo-50/70 border-indigo-500 text-slate-900 shadow-sm'
                          : 'bg-white border-slate-200 text-slate-600 hover:border-slate-300'
                      }`}
                    >
                      <div className="space-y-0.5 overflow-hidden pr-2">
                        <div className="font-semibold text-slate-900 truncate flex items-center space-x-1">
                          <Building2 className="w-3.5 h-3.5 text-indigo-600 flex-shrink-0" />
                          <span className="truncate">{sup.name}</span>
                        </div>
                        <div className="flex items-center space-x-1 text-[11px] text-slate-500 truncate">
                          <Mail className="w-3 h-3 text-slate-400 flex-shrink-0" />
                          <span className="truncate">{sup.contact_email}</span>
                        </div>
                        {(sup.phone || sup.address) && (
                          <div className="flex items-center space-x-2 text-[10px] text-slate-400 pt-0.5">
                            {sup.phone && (
                              <span className="flex items-center space-x-0.5">
                                <Phone className="w-2.5 h-2.5" />
                                <span>{sup.phone}</span>
                              </span>
                            )}
                            {sup.address && (
                              <span className="flex items-center space-x-0.5 truncate">
                                <MapPin className="w-2.5 h-2.5" />
                                <span className="truncate">{sup.address}</span>
                              </span>
                            )}
                          </div>
                        )}
                      </div>

                      <div className={`w-4 h-4 rounded-md border flex items-center justify-center flex-shrink-0 mt-0.5 ${
                        isSelected 
                          ? 'bg-indigo-600 border-indigo-600 text-white' 
                          : 'border-slate-300 bg-white'
                      }`}>
                        {isSelected && <Check className="w-3 h-3 stroke-[3]" />}
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </div>

          {/* Form Actions */}
          <div className="pt-4 border-t border-slate-100 flex items-center justify-end space-x-3">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 text-xs font-medium text-slate-600 hover:bg-slate-100 rounded-lg transition"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={createProductMutation.isPending}
              className="px-5 py-2 text-xs font-semibold text-white bg-indigo-600 hover:bg-indigo-700 rounded-lg shadow-sm disabled:opacity-50 flex items-center space-x-1.5 transition"
            >
              <Plus className="w-4 h-4" />
              <span>{createProductMutation.isPending ? 'Registering...' : 'Save Product'}</span>
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}