import React, { useState, useEffect, useRef } from 'react';
import axios from 'axios';
import { useAuth } from '../context/AuthContext';
import { Send, User, Bot, Loader2, AlertCircle } from 'lucide-react';
import ReactMarkdown from 'react-markdown';

interface Message {
  id: string;
  text: string;
  sender: 'user' | 'agent';
  timestamp: Date;
}

const ComplaintChat = () => {
  const { user, token } = useAuth();
  const customerId = (user as any)?.customer_id || user?.id;
  const [messages, setMessages] = useState<Message[]>([
    {
      id: '1',
      text: `Bonjour ${user?.name || 'cher client'}, je suis votre assistant dédié aux réclamations. Comment puis-je vous aider aujourd'hui ?`,
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
      console.log('Sending message to agent:', input);
      const response = await axios.post(
        `${import.meta.env.VITE_API_URL}/agents/complaint/`,
        { message: input, customer_id: customerId },
        { headers: { Authorization: `Bearer ${token}` } }
      );
      console.log('Agent response:', response.data);

      const agentMessage: Message = {
        id: (Date.now() + 1).toString(),
        text: response.data.reply || "Désolé, je n'ai pas pu traiter votre demande pour le moment.",
        sender: 'agent',
        timestamp: new Date(),
      };

      setMessages((prev) => [...prev, agentMessage]);
    } catch (err: any) {
      console.error('Chat error:', err);
      setError("Une erreur est survenue lors de la communication avec l'agent.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex flex-col h-[calc(100vh-64px)] w-full bg-gray-50 overflow-hidden">
      {/* Header - Agent name on top left */}
      <div className="bg-[#1c2951] px-6 py-3 flex items-center gap-3 shadow-md">
        <div className="bg-[#c8102e] p-1.5 rounded-full">
          <Bot className="text-white w-5 h-5" />
        </div>
        <div>
          <h2 className="text-white font-semibold text-base">Agent de Réclamation</h2>
          <div className="flex items-center gap-1.5">
            <span className="w-1.5 h-1.5 bg-green-400 rounded-full animate-pulse"></span>
            <span className="text-gray-400 text-xs">En ligne</span>
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
                className={`p-4 rounded-2xl shadow-sm ${
                  msg.sender === 'user'
                    ? 'bg-[#1c2951] text-white rounded-tr-none'
                    : 'bg-white text-gray-800 border border-gray-100 rounded-tl-none'
                }`}
              >
                {msg.sender === 'agent' ? (
                  <div className="text-sm leading-relaxed prose prose-sm max-w-none prose-headings:text-[#1c2951] prose-strong:text-[#1c2951] prose-li:text-gray-700">
                  <ReactMarkdown>
                    {msg.text}
                  </ReactMarkdown>
                </div>
                ) : (
                  <span className="text-sm">{msg.text}</span>
                )}
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
              <span className="text-sm text-gray-500 italic">L'agent analyse votre demande...</span>
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
            placeholder="Décrivez votre problème ici..."
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

export default ComplaintChat;
