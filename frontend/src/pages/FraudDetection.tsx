import React, { useState, useEffect, useRef } from 'react';
import axios from 'axios';
import { useAuth } from '../context/AuthContext';
import { Send, User, Bot, Loader2, AlertCircle, Shield, Search } from 'lucide-react';

interface Message {
  id: string;
  text: string;
  sender: 'user' | 'agent';
  timestamp: Date;
}

const FraudDetection = () => {
  const { user, token } = useAuth();
  const [messages, setMessages] = useState<Message[]>([
    {
      id: '1',
      text: `Bonjour ${user?.name || 'cher agent'}, je suis votre assistant de détection de fraude. Veuillez entrer un ID client (ex: client181) pour commencer l'analyse.`,
      sender: 'agent',
      timestamp: new Date(),
    },
  ]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const handleSend = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim() || loading) return;

    const userMessage: Message = {
      id: Date.now().toString(),
      text: input,
      sender: 'user',
      timestamp: new Date(),
    };

    setMessages((prev) => [...prev, userMessage]);
    setInput('');
    setLoading(true);
    setError(null);

    try {
      console.log('Sending fraud analysis request:', input);
      const response = await axios.post(
        `${import.meta.env.VITE_API_URL}/agents/fraud/`,
        { message: input },
        { headers: { Authorization: `Bearer ${token}` } }
      );
      console.log('Fraud agent response:', response.data);

      const agentMessage: Message = {
        id: (Date.now() + 1).toString(),
        text: response.data.reply || "Désolé, je n'ai pas pu analyser ce client pour le moment.",
        sender: 'agent',
        timestamp: new Date(),
      };

      setMessages((prev) => [...prev, agentMessage]);
    } catch (err: any) {
      console.error('Fraud analysis error:', err);
      setError("Une erreur est survenue lors de l'analyse de fraude.");
    } finally {
      setLoading(false);
    }
  };

  const quickQueries = [
    'client181',
    'client962',
    'client100',
    'client250',
  ];

  const handleQuickQuery = (clientId: string) => {
    setInput(`Analyser ${clientId}`);
  };

  return (
    <div className="flex flex-col h-[calc(100vh-64px)] w-full bg-gray-50 overflow-hidden">
      {/* Header - Agent name on top left */}
      <div className="bg-[#1c2951] px-6 py-3 flex items-center gap-3 shadow-md">
        <div className="bg-[#c8102e] p-1.5 rounded-full">
          <Shield className="text-white w-5 h-5" />
        </div>
        <div>
          <h2 className="text-white font-semibold text-base">Agent de Détection de Fraude</h2>
          <div className="flex items-center gap-1.5">
            <span className="w-1.5 h-1.5 bg-green-400 rounded-full animate-pulse"></span>
            <span className="text-gray-400 text-xs">En ligne - Prêt à analyser</span>
          </div>
        </div>
      </div>

      {/* Quick query buttons */}
      <div className="bg-white border-b border-gray-200 px-4 py-2">
        <div className="max-w-3xl mx-auto flex items-center gap-2">
          <span className="text-xs text-gray-500 flex items-center gap-1">
            <Search className="w-3 h-3" />
            Requêtes rapides:
          </span>
          <div className="flex gap-2">
            {quickQueries.map((clientId) => (
              <button
                key={clientId}
                onClick={() => handleQuickQuery(clientId)}
                className="px-3 py-1 text-xs bg-gray-100 hover:bg-[#1c2951] hover:text-white text-gray-700 rounded-full transition-colors"
              >
                {clientId}
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto p-4">
        <div className="max-w-3xl mx-auto space-y-4">
        {messages.map((msg) => (
          <div
            key={msg.id}
            className={`flex ${msg.sender === 'user' ? 'justify-end' : 'justify-start'}`}
          >
            <div
              className={`max-w-[80%] flex items-start gap-2 ${
                msg.sender === 'user' ? 'flex-row-reverse' : 'flex-row'
              }`}
            >
              <div
                className={`p-2 rounded-full shadow-sm flex-shrink-0 ${
                  msg.sender === 'user' ? 'bg-[#1c2951]' : 'bg-white border border-gray-200'
                }`}
              >
                {msg.sender === 'user' ? (
                  <User className="w-4 h-4 text-white" />
                ) : (
                  <Bot className="w-4 h-4 text-[#c8102e]" />
                )}
              </div>
              <div
                className={`p-4 rounded-2xl shadow-sm text-sm leading-relaxed whitespace-pre-wrap ${
                  msg.sender === 'user'
                    ? 'bg-[#1c2951] text-white rounded-tr-none'
                    : 'bg-white text-gray-800 border border-gray-100 rounded-tl-none'
                }`}
              >
                {msg.text}
                <div
                  className={`text-[10px] mt-2 ${
                    msg.sender === 'user' ? 'text-gray-300' : 'text-gray-400'
                  }`}
                >
                  {msg.timestamp.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                </div>
              </div>
            </div>
          </div>
        ))}
        {loading && (
          <div className="flex justify-start">
            <div className="bg-white border border-gray-200 p-4 rounded-2xl shadow-sm rounded-tl-none flex items-center gap-3">
              <Loader2 className="w-4 h-4 text-[#c8102e] animate-spin" />
              <span className="text-sm text-gray-500 italic">L'agent analyse les transactions...</span>
            </div>
          </div>
        )}
        {error && (
          <div className="flex justify-center my-2">
            <div className="bg-red-50 text-red-600 px-4 py-2 rounded-lg text-sm border border-red-100 flex items-center gap-2">
              <AlertCircle className="w-4 h-4" />
              {error}
            </div>
          </div>
        )}
        <div ref={messagesEndRef} />
        </div>
      </div>

      {/* Input */}
      <div className="bg-white border-t border-gray-200 p-4">
        <form onSubmit={handleSend} className="max-w-3xl mx-auto flex gap-3">
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Entrez un ID client (ex: client181) ou une requête..."
            disabled={loading}
            className="flex-1 px-4 py-2.5 bg-gray-100 border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-[#c8102e]/20 focus:border-[#c8102e] transition-all text-sm"
          />
          <button
            type="submit"
            disabled={loading || !input.trim()}
            className={`px-4 py-2.5 rounded-lg transition-all ${
              loading || !input.trim()
                ? 'bg-gray-200 cursor-not-allowed opacity-50'
                : 'bg-[#c8102e] hover:bg-red-700 text-white'
            }`}
          >
            <Send className="w-5 h-5" />
          </button>
        </form>
      </div>
    </div>
  );
};

export default FraudDetection;
