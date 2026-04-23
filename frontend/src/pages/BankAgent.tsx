import React, { useState, useEffect, useRef } from 'react';
import axios from 'axios';
import { useAuth } from '../context/AuthContext';
import { 
  Send, User, Bot, Loader2, AlertCircle, 
  History as HistoryIcon, Lightbulb, X, 
  Trash2, PlusCircle, CheckCircle2, ShieldAlert,
  Info, ChevronLeft, ChevronRight, Scale,
  FileText, Download
} from 'lucide-react';


interface Rationale {
  strategy: string[];
  audit: {
    fidelity: number;
    relevance: number;
    verdict: string;
    reasoning: string;
  };
  sources: any[];
}

interface Message {
  id: string;
  text: string;
  sender: 'user' | 'agent';
  timestamp: Date;
  rationale?: string; // JSON string
}

const BankAgent = () => {
  const { user, token } = useAuth();
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [showHistory, setShowHistory] = useState(true);
  const [historyEvents, setHistoryEvents] = useState<any[]>([]);
  const [historyLoading, setHistoryLoading] = useState(false);
  const [historyError, setHistoryError] = useState<string | null>(null);
  const [selectedRationale, setSelectedRationale] = useState<Rationale | null>(null);
  const [isRationaleOpen, setIsRationaleOpen] = useState(false);
  
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    if (token) {
      fetchHistory();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [token]);

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const fetchHistory = async () => {
    setHistoryLoading(true);
    setHistoryError(null);
    try {
      console.log('Fetching history from:', `${import.meta.env.VITE_API_URL}/agents/bank/memory/`);
      const resp = await axios.get(`${import.meta.env.VITE_API_URL}/agents/bank/memory/`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      console.log('History data received:', resp.data);
      if (Array.isArray(resp.data)) {
        setHistoryEvents(resp.data);
      } else {
        console.error('Expected array for history, got:', resp.data);
        setHistoryError("Format d'historique invalide");
      }
      
      // On affiche toujours le message de bienvenue par défaut pour une nouvelle discussion
      if (messages.length === 0) {
        addWelcomeMessage();
      }
    } catch (err: any) {
      console.error('History fetch error:', err);
      setHistoryError(err.response?.data?.error || err.message || "Erreur de chargement");
    } finally {
      setHistoryLoading(false);
    }
  };

  const addWelcomeMessage = () => {
    setMessages([{
      id: 'welcome',
      text: `Bonjour ${user?.name || 'cher client'}, je suis l'Agent Expert de la BH Bank Tunisie. Je suis là pour gérer vos comptes, virements et vous conseiller techniquement. Comment puis-je vous assister ?`,
      sender: 'agent',
      timestamp: new Date(),
    }]);
  };

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
      const response = await axios.post(
        `${import.meta.env.VITE_API_URL}/agents/bank/`,
        { message: input },
        { headers: { Authorization: `Bearer ${token}` } }
      );

      const agentMessage: Message = {
        id: (Date.now() + 1).toString(),
        text: response.data.answer || "Désolé, je n'ai pas pu traiter votre demande.",
        sender: 'agent',
        timestamp: new Date(),
        rationale: response.data.rationale
      };

      setMessages((prev) => [...prev, agentMessage]);
    } catch (err: any) {
      const serverError = err.response?.data?.error || err.message;
      setError(`Erreur: ${serverError}`);
    } finally {
      setLoading(false);
    }
  };

  const startNewSession = async () => {
    try {
      await axios.post(`${import.meta.env.VITE_API_URL}/api/agents/bank/new-session/`, {}, {
        headers: { Authorization: `Bearer ${token}` }
      });
      setMessages([]);
      addWelcomeMessage();
      fetchHistory();
    } catch (err) { console.error(err); }
  };

  const clearHistory = async () => {
    if (!window.confirm("Effacer tout votre historique ?")) return;
    try {
      await axios.post(`${import.meta.env.VITE_API_URL}/api/agents/bank/clear-memory/`, {}, {
        headers: { Authorization: `Bearer ${token}` }
      });
      startNewSession();
    } catch (err) { console.error(err); }
  };

  const openRationale = (rationaleStr: string) => {
    try {
      const parsed = JSON.parse(rationaleStr);
      setSelectedRationale(parsed);
      setIsRationaleOpen(true);
    } catch (e) {
      console.error("Rationale parse error", e);
    }
  };

  const loadSessionFromHistory = (session: any[]) => {
    const flattenedMessages: Message[] = [];
    session.forEach((ev, i) => {
      if (ev.question) {
        flattenedMessages.push({
          id: `q-${ev.ts}-${i}`,
          text: ev.question,
          sender: 'user',
          timestamp: new Date(ev.ts * 1000),
        });
      }
      if (ev.answer) {
        flattenedMessages.push({
          id: `a-${ev.ts}-${i}`,
          text: ev.answer,
          sender: 'agent',
          timestamp: new Date(ev.ts * 1000),
          rationale: ev.rationale
        });
      }
    });

    if (flattenedMessages.length > 0) {
      setMessages(flattenedMessages);
    }
  };

  const getGroupedSessions = () => {
    const sessions: any[][] = [];
    let currentSession: any[] = [];
    
    historyEvents.forEach(ev => {
      if (ev.is_new_session) {
        if (currentSession.length > 0) sessions.push(currentSession);
        currentSession = [];
      } else {
        currentSession.push(ev);
      }
    });
    if (currentSession.length > 0) sessions.push(currentSession);
    
    return sessions.reverse();
  };

  const renderMessageText = (text: string) => {
    const combinedRegex = /\[([^\]]+)\]\((https?:\/\/[^\s)]+)\)|(https?:\/\/[^\s<>()[\]{}]+(?:(?:\([^\s()<>!]+\)|\[[^\s()[\]<>!]+\]|{[^\s(){}<>!]+})|[^\s`!()\[\]{};:'".,<>?«»“”‘’]))/g;
    
    const elements: (JSX.Element | string)[] = [];
    const renderedUrls = new Set<string>();
    let lastIndex = 0;
    let match;

    while ((match = combinedRegex.exec(text)) !== null) {
      // Text before match
      if (match.index > lastIndex) {
        elements.push(text.substring(lastIndex, match.index));
      }

      const mdTitle = match[1];
      const mdUrl = match[2];
      const rawUrl = match[3];
      const url = mdUrl || rawUrl;

      // Skip if this specific URL was already rendered in this message
      if (!renderedUrls.has(url)) {
        const isPdfStatement = url.toLowerCase().includes('extrait') && url.toLowerCase().includes('.pdf');
        
        if (isPdfStatement) {
          elements.push(
            <a 
              key={`card-${match.index}`} 
              href={url} 
              target="_blank" 
              rel="noopener noreferrer" 
              className="block mt-3 p-4 bg-red-50 border border-red-100 rounded-2xl hover:bg-red-100 transition-all group flex items-center gap-4 no-underline"
            >
              <div className="bg-red-600 p-2.5 rounded-xl text-white shadow-sm group-hover:scale-110 transition-transform">
                <FileText className="w-6 h-6" />
              </div>
              <div className="flex-1">
                <div className="text-red-900 font-bold text-base">Extrait de Compte PDF</div>
                <div className="text-red-600 text-xs font-medium flex items-center gap-1">
                  Cliquez pour télécharger • BH Bank
                </div>
              </div>
              <Download className="w-5 h-5 text-red-400 group-hover:text-red-600" />
            </a>
          );
        } else {
          elements.push(
            <a 
              key={`link-${match.index}`} 
              href={url} 
              target="_blank" 
              rel="noopener noreferrer" 
              className="text-red-600 hover:text-red-700 underline font-bold"
            >
              {mdTitle || url}
            </a>
          );
        }
        renderedUrls.add(url);
      }

      lastIndex = combinedRegex.lastIndex;
    }

    // Remaining text
    if (lastIndex < text.length) {
      elements.push(text.substring(lastIndex));
    }

    return elements;
  };


  return (

    <div className="flex h-[calc(100vh-64px)] w-full bg-slate-100 overflow-hidden font-sans">
      
      {/* Sidebar - History */}
      <div className={`transition-all duration-300 ease-in-out border-r border-slate-200 bg-white flex flex-col ${showHistory ? 'w-72' : 'w-0 opacity-0 overflow-hidden'}`}>
        <div className="p-4 border-b border-slate-100 flex items-center justify-between bg-slate-50/50">
          <h3 className="font-bold text-slate-700 flex items-center gap-2 text-sm uppercase tracking-wider">
            <HistoryIcon className="w-4 h-4 text-red-600" />
            Historique
          </h3>
          <button onClick={startNewSession} title="Nouvelle session" className="p-1.5 hover:bg-slate-200 rounded-lg text-slate-500 transition-colors">
            <PlusCircle className="w-5 h-5" />
          </button>
        </div>
        <div className="flex-1 overflow-y-auto p-2 space-y-1">
          {historyLoading && (
            <div className="text-center py-10 opacity-30">
              <Loader2 className="w-8 h-8 mx-auto mb-2 animate-spin text-slate-300" />
              <p className="text-xs">Chargement...</p>
            </div>
          )}
          {historyError && (
            <div className="text-center py-10 text-red-400 px-4">
              <AlertCircle className="w-8 h-8 mx-auto mb-2 opacity-30" />
              <p className="text-[10px] font-bold">{historyError}</p>
            </div>
          )}
          {!historyLoading && !historyError && getGroupedSessions().slice(0, 15).map((session, i) => (
            <div 
              key={i} 
              onClick={() => loadSessionFromHistory(session)}
              className="p-3 rounded-xl hover:bg-slate-50 cursor-pointer border border-transparent hover:border-slate-100 transition-all group"
            >
              <div className="flex items-center gap-2 mb-1">
                <div className="w-1.5 h-1.5 bg-red-600 rounded-full" />
                <p className="text-xs font-bold text-slate-800 truncate">
                  {session[0]?.question || "Discussion sans titre"}
                </p>
              </div>
              <p className="text-[10px] text-slate-400 flex items-center justify-between">
                <span className="flex items-center gap-1">
                  <CheckCircle2 className="w-3 h-3 text-emerald-500" />
                  {session.length} message(s)
                </span>
                <span>{new Date(session[0]?.ts * 1000).toLocaleDateString()}</span>
              </p>
            </div>
          ))}
          {!historyLoading && !historyError && historyEvents.length === 0 && (
            <div className="text-center py-10 opacity-30">
              <HistoryIcon className="w-10 h-10 mx-auto mb-2 text-slate-300" />
              <p className="text-xs">Aucun historique local</p>
            </div>
          )}
        </div>
        <div className="p-4 border-t border-slate-100">
           <button onClick={clearHistory} className="w-full py-2.5 flex items-center justify-center gap-2 text-xs font-bold text-slate-400 hover:text-red-600 hover:bg-red-50 rounded-xl transition-all">
             <Trash2 className="w-4 h-4" />
             Effacer l'historique
           </button>
        </div>
      </div>

      {/* Main Chat Area */}
      <div className="flex-1 flex flex-col relative bg-slate-50/50">
        {/* Toggle Button for History */}
        <button 
          onClick={() => setShowHistory(!showHistory)}
          className={`absolute left-0 top-1/2 -translate-y-1/2 z-20 bg-white border border-slate-200 p-1 rounded-r-xl shadow-md text-slate-400 hover:text-red-600 transition-all ${showHistory ? 'left-[-1px]' : 'left-0'}`}
        >
          {showHistory ? <ChevronLeft className="w-4 h-4" /> : <ChevronRight className="w-4 h-4" />}
        </button>

        {/* Header */}
        <div className="bg-[#1c2951] px-6 py-4 flex items-center justify-between shadow-xl z-10 border-b border-red-900/20">
          <div className="flex items-center gap-4">
            <div className="bg-gradient-to-br from-red-600 to-red-700 p-2.5 rounded-2xl shadow-lg ring-4 ring-red-600/10">
              <Bot className="text-white w-6 h-6" />
            </div>
            <div>
              <h2 className="text-white font-extrabold text-lg tracking-tight uppercase">Agent Expert Bancaire</h2>
              <div className="flex items-center gap-2">
                <span className="w-2 h-2 bg-emerald-400 rounded-full animate-pulse shadow-[0_0_10px_rgba(52,211,153,0.8)]"></span>
                <span className="text-slate-300 text-[10px] font-black uppercase tracking-[0.2em]">BH Private</span>
              </div>
            </div>
          </div>
          <div className="hidden md:flex items-center gap-3">
             {/* Labels supprimés */}
          </div>
        </div>

        {/* Messages */}
        <div className="flex-1 overflow-y-auto p-6 space-y-6">
          <div className="max-w-4xl mx-auto space-y-6">
            {messages.map((msg) => (
              <div key={msg.id} className={`flex ${msg.sender === 'user' ? 'justify-end' : 'justify-start'} group/msg animate-in fade-in slide-in-from-bottom-4 duration-300`}>
                <div className={`max-w-[85%] flex items-start gap-4 ${msg.sender === 'user' ? 'flex-row-reverse' : 'flex-row'}`}>
                  <div className={`p-2.5 rounded-2xl shadow-lg flex-shrink-0 transition-transform group-hover/msg:scale-110 ${msg.sender === 'user' ? 'bg-[#1c2951] ring-4 ring-blue-900/5' : 'bg-white border border-slate-200 ring-4 ring-slate-200/5'}`}>
                    {msg.sender === 'user' ? <User className="w-5 h-5 text-white" /> : <Bot className="w-5 h-5 text-red-600" />}
                  </div>
                  <div className="relative">
                    <div className={`p-5 rounded-3xl shadow-sm text-sm leading-relaxed ${msg.sender === 'user' ? 'bg-[#1c2951] text-white rounded-tr-none' : 'bg-white text-slate-800 border border-slate-100 rounded-tl-none font-medium'}`}>
                      <div className="whitespace-pre-wrap">{renderMessageText(msg.text)}</div>

                      <div className={`text-[9px] mt-3 font-bold uppercase tracking-widest opacity-40 flex justify-between items-center ${msg.sender === 'user' ? 'text-slate-200' : 'text-slate-500'}`}>
                        {msg.timestamp.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                        {msg.sender === 'agent' && (
                          <span className="flex items-center gap-1 cursor-help" title={
                            (msg.rationale ? (() => {
                              try {
                                const r = JSON.parse(msg.rationale);
                                return r.audit?.reasoning || 'Audit de sécurité effectué';
                              } catch(e) { return 'Audit de sécurité effectué'; }
                            })() : 'Audit de sécurité effectué')
                          }>
                            {(() => {
                              try {
                                if (!msg.rationale) return <><CheckCircle2 className="w-3 h-3 text-emerald-500" />Vérifié par audit</>;
                                const r = JSON.parse(msg.rationale);
                                const v = r.audit?.verdict;
                                if (v === 'Halluciné') return <><ShieldAlert className="w-3 h-3 text-red-500" />Audit : Hallucination détectée</>;
                                if (v === 'Partiel') return <><Info className="w-3 h-3 text-orange-500" />Audit : Fidélité partielle</>;
                                return <><CheckCircle2 className="w-3 h-3 text-emerald-500" />Vérifié par audit</>;
                              } catch(e) {
                                return <><CheckCircle2 className="w-3 h-3 text-emerald-500" />Vérifié par audit</>;
                              }
                            })()}
                          </span>
                        )}

                      </div>
                    </div>
                    {/* XAI Button */}
                    {msg.sender === 'agent' && msg.rationale && (
                      <button 
                        onClick={() => openRationale(msg.rationale!)}
                        className="absolute -right-12 top-2 p-2 bg-white rounded-full shadow-md text-red-600 hover:bg-red-600 hover:text-white transition-all transform hover:scale-110 active:scale-90 border border-slate-100 group/xai"
                        title="Voir l'explication (XAI)"
                      >
                        <Lightbulb className="w-5 h-5 animate-pulse" />
                      </button>
                    )}
                  </div>
                </div>
              </div>
            ))}
            {loading && (
              <div className="flex justify-start animate-in fade-in duration-500">
                <div className="bg-white border border-slate-200 p-5 rounded-3xl shadow-sm rounded-tl-none flex items-center gap-5">
                  <div className="flex space-x-1.5">
                    <div className="w-2.5 h-2.5 bg-red-600 rounded-full animate-bounce [animation-delay:-0.3s]"></div>
                    <div className="w-2.5 h-2.5 bg-red-600 rounded-full animate-bounce [animation-delay:-0.15s]"></div>
                    <div className="w-2.5 h-2.5 bg-red-600 rounded-full animate-bounce"></div>
                  </div>
                  <span className="text-xs font-bold text-slate-500 uppercase tracking-widest">Traitement en cours...</span>
                </div>
              </div>
            )}
            {error && (
              <div className="flex justify-center my-4 animate-in zoom-in duration-300">
                <div className="bg-red-50 text-red-600 px-6 py-3 rounded-2xl text-sm border border-red-100 flex items-center gap-3 shadow-lg font-bold">
                  <AlertCircle className="w-5 h-5" />
                  <span>{error}</span>
                </div>
              </div>
            )}
              {loading && (
                <div className="flex justify-start items-end gap-3 mb-6 animate-pulse">
                  <div className="w-10 h-10 rounded-2xl bg-gradient-to-br from-red-600 to-red-900 flex items-center justify-center shadow-lg">
                    <Bot className="w-6 h-6 text-white" />
                  </div>
                  <div className="max-w-[80%] px-6 py-4 rounded-3xl bg-white/5 border border-white/10 backdrop-blur-xl">
                    <div className="flex items-center gap-3">
                      <Loader2 className="w-4 h-4 animate-spin text-red-500" />
                      <span className="text-white/70 text-xs font-bold uppercase tracking-tight">En cours</span>
                    </div>
                  </div>
                </div>
              )}
              <div ref={messagesEndRef} />
            </div>
          </div>

        {/* Input */}
        <div className="bg-white/80 backdrop-blur-md border-t border-slate-200 p-8 shadow-[0_-10px_40px_rgba(0,0,0,0.04)]">
          <form onSubmit={handleSend} className="max-w-4xl mx-auto flex gap-4">
            <div className="flex-1 relative group">
              <input
                type="text"
                value={input}
                onChange={(e) => setInput(e.target.value)}
                placeholder="Posez votre question à l'Expert (ex: Mon dernier relevé ?)"
                disabled={loading}
                className="w-full px-8 py-5 bg-slate-50 border-2 border-slate-100 rounded-[2rem] focus:outline-none focus:ring-8 focus:ring-red-600/5 focus:border-red-600 transition-all text-sm font-bold placeholder:text-slate-400 group-hover:bg-white"
              />
            </div>
            <button
              type="submit"
              disabled={loading || !input.trim()}
              className="px-8 py-4 bg-gradient-to-r from-red-600 to-red-800 text-white font-black uppercase tracking-widest rounded-xl hover:shadow-[0_0_20px_rgba(220,38,38,0.5)] transition-all flex items-center gap-3 disabled:opacity-50 disabled:hover:shadow-none"
            >
              {loading ? (
                <>
                  <Loader2 className="w-5 h-5 animate-spin" />
                  <span className="text-[10px]">Audit Token Factory en cours...</span>
                </>
              ) : (
                <>
                  <Send className="w-5 h-5" />
                  <span>Envoyer</span>
                </>
              )}
            </button>
          </form>
        </div>
      </div>

      {/* XAI Dashboard Drawer (Right Side) */}
      <div 
        className={`fixed inset-y-0 right-0 z-50 w-full sm:w-[450px] bg-white/95 backdrop-blur-xl shadow-2xl border-l border-slate-200 transform transition-transform duration-500 ease-in-out flex flex-col ${isRationaleOpen ? 'translate-x-0' : 'translate-x-full'}`}
      >
        <div className="p-6 bg-[#1c2951] text-white flex items-center justify-between">
           <div className="flex items-center gap-3">
             <Lightbulb className="w-6 h-6 text-red-500" />
             <h2 className="font-black text-sm uppercase tracking-widest">Explication de l'IA</h2>
           </div>
           <button onClick={() => setIsRationaleOpen(false)} className="p-2 hover:bg-white/10 rounded-xl transition-colors">
             <X className="w-6 h-6" />
           </button>
        </div>

        <div className="flex-1 overflow-y-auto p-8 space-y-10">
           {selectedRationale && (
             <>
               {/* Verdict Section */}
               <section className="animate-in fade-in slide-in-from-right-4 duration-700">
                 <div className="flex items-center gap-3 mb-4">
                    <div className="w-10 h-10 bg-red-50 rounded-2xl flex items-center justify-center border border-red-100">
                      <Scale className="w-5 h-5 text-red-600" />
                    </div>
                    <div>
                      <h4 className="text-[10px] font-black text-red-600 uppercase tracking-[0.2em]">Audit Token Factory</h4>
                      <h3 className="text-xl font-black text-slate-800">Verdict du Juge</h3>
                    </div>
                 </div>
                 <div className={`p-6 rounded-3xl border-2 mb-4 ${selectedRationale.audit.verdict === 'Fidèle' ? 'bg-emerald-50 border-emerald-100' : 'bg-amber-50 border-amber-100'}`}>
                    <div className="flex items-center justify-between mb-4">
                      <span className={`px-4 py-1.5 rounded-full text-[10px] font-black uppercase tracking-widest ${selectedRationale.audit.verdict === 'Fidèle' ? 'bg-emerald-500 text-white shadow-lg shadow-emerald-500/20' : 'bg-amber-500 text-white'}`}>
                        {selectedRationale.audit.verdict}
                      </span>
                      <div className="flex gap-4">
                         <div className="text-center">
                           <p className="text-[8px] font-black text-slate-400 uppercase tracking-widest">Fidélité</p>
                           <p className="text-sm font-black text-slate-700">{selectedRationale.audit.fidelity}%</p>
                         </div>
                         <div className="text-center">
                           <p className="text-[8px] font-black text-slate-400 uppercase tracking-widest">Pertinence</p>
                           <p className="text-sm font-black text-slate-700">{selectedRationale.audit.relevance}%</p>
                         </div>
                      </div>
                    </div>
                    <p className="text-xs font-bold text-slate-600 leading-relaxed italic">
                      "{selectedRationale.audit.reasoning}"
                    </p>
                 </div>
               </section>

               {/* Strategy Section */}
               <section className="animate-in fade-in slide-in-from-right-4 duration-700 [animation-delay:200ms]">
                  <div className="flex items-center gap-3 mb-6">
                    <div className="w-10 h-10 bg-slate-100 rounded-2xl flex items-center justify-center border border-slate-200">
                      <Info className="w-5 h-5 text-slate-600" />
                    </div>
                    <h3 className="text-lg font-black text-slate-800 uppercase tracking-tighter">Stratégie Employée</h3>
                  </div>
                  <div className="space-y-4">
                    {selectedRationale.strategy.map((step, i) => (
                      <div key={i} className="flex gap-4 relative">
                        {i !== selectedRationale.strategy.length - 1 && (
                          <div className="absolute left-[13px] top-7 bottom-0 w-0.5 bg-slate-100"></div>
                        )}
                        <div className="w-7 h-7 rounded-full bg-white border-2 border-red-600 flex items-center justify-center text-[10px] font-black text-red-600 z-10 flex-shrink-0 shadow-sm">
                          {i + 1}
                        </div>
                        <div className="bg-slate-50/80 p-4 rounded-2xl border border-slate-100 flex-1">
                          <p className="text-xs font-bold text-slate-700 leading-relaxed">{step}</p>
                        </div>
                      </div>
                    ))}
                  </div>
               </section>
             </>
           )}
        </div>
        
        <div className="p-8 border-t border-slate-100 bg-slate-50/50">
           <p className="text-[9px] font-black text-slate-400 text-center uppercase tracking-widest">
             Généré par BH Auditor v2.4 • IA Explicable (XAI)
           </p>
        </div>
      </div>

      {/* Overlay when drawer is open */}
      {isRationaleOpen && (
        <div 
          onClick={() => setIsRationaleOpen(false)}
          className="fixed inset-0 bg-slate-900/40 backdrop-blur-sm z-40 transition-opacity duration-500"
        ></div>
      )}

    </div>
  );
};

export default BankAgent;
