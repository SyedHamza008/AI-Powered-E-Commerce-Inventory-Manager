import React, { useState, useRef, useEffect } from 'react';
import { useMutation } from '@tanstack/react-query';
import { api } from '../services/api';
import { X, Send, Bot, User, Database, Sparkles } from 'lucide-react';

interface ChatMessage {
  role: 'user' | 'assistant';
  content: string;
  toolsUsed?: string[];
}

interface AdminChatDrawerProps {
  isOpen: boolean;
  onClose: () => void;
  token?: string;
}

export function AdminChatDrawer({ isOpen, onClose, token }: AdminChatDrawerProps) {
  const [messages, setMessages] = useState<ChatMessage[]>([
    {
      role: 'assistant',
      content:
        'Hello! I am your AI inventory assistant. Ask me anything about stock balances, low-stock warnings, supplier details, or audit history.',
    },
  ]);
  const [input, setInput] = useState('');
  const scrollRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  // Auto-scroll whenever messages change or loading state toggles
  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages]);

  // Focus input on drawer open & handle Escape key navigation
  useEffect(() => {
    if (!isOpen) return;

    inputRef.current?.focus();

    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose();
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [isOpen, onClose]);

  const chatMutation = useMutation({
    mutationFn: (allMessages: { role: string; content: string }[]) =>
      api.chat(allMessages, token),
    onSuccess: (data) => {
      setMessages((prev) => [
        ...prev,
        {
          role: 'assistant',
          content: data.reply,
          toolsUsed: data.tools_used,
        },
      ]);
    },
    onError: (err: Error) => {
      setMessages((prev) => [
        ...prev,
        {
          role: 'assistant',
          content: `⚠️ Error: ${err.message || 'Failed to communicate with AI service'}`,
        },
      ]);
    },
  });

  const handleSend = (e: React.FormEvent) => {
    e.preventDefault();
    const trimmed = input.trim();
    if (!trimmed || chatMutation.isPending) return;

    const userMsg: ChatMessage = { role: 'user', content: trimmed };
    const nextHistory = [...messages, userMsg];
    setMessages(nextHistory);
    setInput('');

    // Send full conversation history payload
    chatMutation.mutate(
      nextHistory.map((m) => ({ role: m.role, content: m.content }))
    );
  };

  if (!isOpen) return null;

  return (
    <div
      className="fixed inset-0 z-50 flex justify-end bg-slate-900/40 backdrop-blur-sm animate-in fade-in duration-200"
      onClick={onClose}
    >
      <div
        className="w-full max-w-md bg-white h-full shadow-2xl flex flex-col border-l border-slate-200"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="p-4 border-b border-slate-100 flex items-center justify-between bg-slate-50/80">
          <div className="flex items-center space-x-2.5">
            <div className="p-2 bg-indigo-600 rounded-xl text-white shadow-sm">
              <Bot className="w-4 h-4" />
            </div>
            <div>
              <h2 className="text-sm font-bold text-slate-800">Inventory Copilot</h2>
              <p className="text-[11px] text-slate-400">Read-only tool calling assistant</p>
            </div>
          </div>
          <button
            onClick={onClose}
            aria-label="Close drawer"
            className="p-1.5 rounded-lg text-slate-400 hover:text-slate-600 hover:bg-slate-100 transition"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Message Log */}
        <div ref={scrollRef} className="flex-1 p-4 overflow-y-auto space-y-3.5">
          {messages.map((m, idx) => (
            <div
              key={idx}
              className={`flex items-start space-x-2.5 text-xs ${
                m.role === 'user' ? 'flex-row-reverse space-x-reverse' : ''
              }`}
            >
              <div
                className={`p-1.5 rounded-lg flex-shrink-0 ${
                  m.role === 'user' ? 'bg-indigo-600 text-white' : 'bg-slate-100 text-slate-600'
                }`}
              >
                {m.role === 'user' ? <User className="w-3.5 h-3.5" /> : <Bot className="w-3.5 h-3.5" />}
              </div>
              <div
                className={`p-3 rounded-2xl max-w-[80%] leading-relaxed ${
                  m.role === 'user'
                    ? 'bg-indigo-600 text-white rounded-tr-none'
                    : 'bg-slate-100 text-slate-800 rounded-tl-none border border-slate-200/60'
                }`}
              >
                <p className="whitespace-pre-wrap">{m.content}</p>
                {m.toolsUsed && m.toolsUsed.length > 0 && (
                  <div className="mt-2 pt-2 border-t border-slate-200/80 flex flex-wrap gap-1">
                    {m.toolsUsed.map((tool, tIdx) => (
                      <span
                        key={tIdx}
                        className="inline-flex items-center space-x-1 text-[10px] px-1.5 py-0.5 rounded bg-white text-indigo-700 border border-slate-200 font-mono shadow-xs"
                      >
                        <Database className="w-2.5 h-2.5" />
                        <span>{tool}</span>
                      </span>
                    ))}
                  </div>
                )}
              </div>
            </div>
          ))}

          {chatMutation.isPending && (
            <div className="flex items-center space-x-2 text-xs text-indigo-600 italic animate-pulse">
              <Sparkles className="w-3.5 h-3.5 animate-spin" />
              <span>Querying inventory database tools...</span>
            </div>
          )}
        </div>

        {/* Footer Input */}
        <form onSubmit={handleSend} className="p-3.5 border-t border-slate-100 bg-slate-50/50 flex space-x-2">
          <input
            ref={inputRef}
            type="text"
            placeholder="Ask about products, stock levels, or suppliers..."
            value={input}
            onChange={(e) => setInput(e.target.value)}
            disabled={chatMutation.isPending}
            className="flex-1 px-3.5 py-2 text-xs rounded-xl border border-slate-200 bg-white focus:outline-none focus:ring-2 focus:ring-indigo-500 placeholder:text-slate-400 disabled:bg-slate-50"
          />
          <button
            type="submit"
            disabled={!input.trim() || chatMutation.isPending}
            className="p-2 bg-indigo-600 text-white rounded-xl hover:bg-indigo-700 disabled:opacity-50 transition cursor-pointer disabled:cursor-not-allowed"
          >
            <Send className="w-4 h-4" />
          </button>
        </form>
      </div>
    </div>
  );
}