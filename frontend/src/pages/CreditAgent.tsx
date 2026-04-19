import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { useAuth } from '../context/AuthContext';
import { Info, AlertCircle, Upload, CheckCircle2, FileText, ChevronDown, CheckCircle, BrainCircuit, ShieldCheck, ChevronRight, AlertTriangle } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';

export default function CreditAgent() {
  const { user } = useAuth();
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<any>(null);
  const [error, setError] = useState<string | null>(null);
  const [bankParams, setBankParams] = useState<any>(null);
  const [activeTab, setActiveTab] = useState<'supervisor' | 'finance' | 'risk' | 'decision'>('supervisor');

  // Form State
  const [typeCredit, setTypeCredit] = useState('Crédit consommation');
  const [montant, setMontant] = useState(1000);
  const [duree, setDuree] = useState(12);
  const [fichePaie, setFichePaie] = useState<File | null>(null);

  // Auto specific
  const [chevaux, setChevaux] = useState(4);
  const [etatVehicule, setEtatVehicule] = useState('Neuf');

  useEffect(() => {
    axios.get('http://localhost:5000/bank_params')
      .then(res => setBankParams(res.data))
      .catch(err => console.error("Could not fetch bank params", err));
  }, []);

  const getTauxAdditionnel = () => {
    if (!bankParams) return 0.05;
    if (typeCredit === 'Crédit consommation') return bankParams.marge_additionnelle_consommation;
    if (typeCredit === 'Crédit aménagement') return bankParams.marge_additionnelle_amenagement;
    if (typeCredit === 'Crédit BH auto') return bankParams.marge_additionnelle_voiture;
    return 0.05;
  };

  const tmmValue = bankParams ? bankParams.tmm : 0.0699;
  const margeValue = getTauxAdditionnel();
  const tauxTotal = tmmValue + margeValue;
  const formatPct = (val: number) => (val * 100).toFixed(2) + '%';

  const formatReportText = (text: string, isDark: boolean = false) => {
    if (!text) return null;
    
    const lines = text.split('\n');
    const elements: React.ReactNode[] = [];
    let currentCardGroup: React.ReactNode[] = [];

    const flushCardGroup = () => {
      if (currentCardGroup.length > 0) {
        elements.push(
          <div key={`group-${elements.length}`} className={`mb-5 p-5 md:p-6 rounded-2xl break-inside-avoid shadow-sm border ${isDark ? 'bg-white/5 border-white/10' : 'bg-white border-gray-100/60 transition-shadow hover:shadow-md'}`}>
            <div className="space-y-4">
              {currentCardGroup}
            </div>
          </div>
        );
        currentCardGroup = [];
      }
    };

    lines.forEach((line, index) => {
      let content = line.trim();
      if (!content) {
        flushCardGroup();
        elements.push(<div key={`blank-${index}`} className="h-2"></div>);
        return;
      }

      let isHeader = false;
      
      // Clean up markdown headers
      if (content.startsWith('### ')) {
        isHeader = true;
        content = content.substring(4).trim();
      } else if (content.startsWith('## ')) {
        isHeader = true;
        content = content.substring(3).trim();
      } else if (content.startsWith('# ')) {
        isHeader = true;
        content = content.substring(2).trim();
      }

      // Handle Numbered statements ("1. Document:") and Key-Value pairs ("Taux d'intérêt : 11.99 %")
      let isCardItem = false;
      const numMatch = content.match(/^(\d+\.\s+[^:]+:)(.*)$/);
      
      if (numMatch && !content.includes('**')) {
        content = `**${numMatch[1].trim()}** ${numMatch[2].trim()}`;
        isCardItem = true;
      } else if (/^\d+\.\s/.test(content)) {
        isCardItem = true;
      } else if (!isHeader) {
        const kvMatch = content.match(/^([^:]+?)\s*:\s*(.+)$/);
        // Ensure the label part isn't too long (avoiding full sentences that just happen to have a colon)
        if (kvMatch && kvMatch[1].length < 40 && !kvMatch[1].includes('http')) {
          if (!content.includes('**')) {
             content = `**${kvMatch[1].trim()}** : ${kvMatch[2].trim()}`;
          }
          isCardItem = true;
        } else if (content.startsWith('Le total estimé')) {
          content = content.replace("Le total estimé de votre demande s'élève à", "**Le total estimé de votre demande s'élève à**");
          isCardItem = true;
        } else if (content.startsWith('(*) Potentiel Credit')) {
          content = content.replace("(*) Potentiel Credit", "**(*) Potentiel Credit**");
          isCardItem = true;
        } else if (content.startsWith('Statut :')) {
          isCardItem = true;
        }
      }
      
      const isBullet = content.startsWith('* ') || content.startsWith('- ');

      // Handle **bold** text
      const parts = content.split(/(\*\*.*?\*\*)/g);
      const formattedLine = parts.map((part, i) => {
        if (part.startsWith('**') && part.endsWith('**')) {
          const innerText = part.substring(2, part.length - 2).replace(/###/g, '').trim();
          return (
            <strong key={`bold-${index}-${i}`} className={`font-bold ${isDark ? 'text-white' : 'text-[#1c2951]'}`}>
              {innerText}
            </strong>
          );
        }
        return <span key={`text-${index}-${i}`}>{part}</span>;
      });

      if (isHeader) {
        flushCardGroup();
        elements.push(
          <h4 key={`header-${index}`} className={`text-xl md:text-2xl font-black mt-8 mb-5 break-inside-avoid flex items-center gap-3 ${isDark ? 'text-white' : 'text-[#1c2951]'}`}>
            {formattedLine}
          </h4>
        );
        return;
      }

      if (isCardItem) {
        currentCardGroup.push(
          <div key={`item-${index}`} className={`flex items-start gap-4 ${isDark ? 'text-gray-200' : 'text-gray-700'}`}>
            <div className={`mt-1.5 w-2 h-2 rounded-full shrink-0 shadow-sm ${isDark ? 'bg-white' : 'bg-[#c8102e]'}`} />
            <div className="leading-relaxed text-sm md:text-base">
              {formattedLine}
            </div>
          </div>
        );
        return;
      }

      if (isBullet) {
        flushCardGroup();
        elements.push(
          <div key={`bullet-${index}`} className={`mb-3 pl-4 relative break-inside-avoid flex items-start gap-3 ${isDark ? 'text-gray-300' : 'text-gray-600'}`}>
            <div className={`mt-2.5 w-1.5 h-1.5 rounded-full shrink-0 ${isDark ? 'bg-gray-400' : 'bg-gray-400'}`} />
            <div className="leading-relaxed text-sm md:text-base">
              {formattedLine}
            </div>
          </div>
        );
        return;
      }

      flushCardGroup();
      elements.push(
        <div key={`para-${index}`} className={`mb-4 leading-relaxed text-sm md:text-base break-inside-avoid ${isDark ? 'text-gray-300 font-light' : 'text-gray-600'}`}>
          {formattedLine}
        </div>
      );
    });

    flushCardGroup();
    return elements;
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      setFichePaie(e.target.files[0]);
    }
  };

  const handleCalculate = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!fichePaie) {
      setError("Veuillez télécharger votre fiche de paie (PDF).");
      return;
    }
    setError(null);
    setLoading(true);

    const formData = new FormData();
    // In actual production, we'd use user._id or user.id
    formData.append('client_id', user?.id || 'API_Client');
    formData.append('type_credit', typeCredit);
    formData.append('amount', montant.toString());
    formData.append('repayment_period', duree.toString());
    formData.append('fiche_paie', fichePaie);

    // Build details_json
    const details: any = {};

    if (typeCredit === 'Crédit BH auto') {
      details['chevaux'] = chevaux;
      details['etat_vehicule'] = etatVehicule;
    }

    formData.append('details_json', JSON.stringify(details));

    try {
      // Connect to the Flask backend running on port 5000 (credit_agent)
      const res = await axios.post('http://localhost:5000/process_credit', formData, {
        headers: {
          'Content-Type': 'multipart/form-data'
        }
      });
      setResult(res.data);
      if (res.data.final_decision) {
        setActiveTab('decision');
      } else {
        setActiveTab('supervisor');
      }
    } catch (err: any) {
      console.error(err);
      setError(err.response?.data?.message || err.message || "Erreur de traitement.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-gray-50 pb-20">
      {/* Header Banner */}
      <div className="bg-[#1c2951] text-white py-12 px-4 shadow-md">
        <div className="max-w-4xl mx-auto flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-bold flex items-center gap-3">
              <BrainCircuit className="w-8 h-8 text-[#c8102e]" /> Agent de Crédit
            </h1>
            <p className="mt-2 text-gray-300">Système expert pour l'analyse des capacités et la simulation des offres  de crédit</p>
          </div>
          <div className="hidden md:flex bg-white/10 p-3 rounded-lg border border-white/20 items-center justify-center">
            <div className="text-center">
              <p className="text-xs text-gray-400 font-semibold mb-1 uppercase tracking-wider">TMM Actuel</p>
              <p className="text-2xl font-bold text-[#c8102e]">{formatPct(tmmValue)}</p>
            </div>
          </div>
        </div>
      </div>

      <div className="max-w-4xl mx-auto px-4 mt-8">

        {/* Alerts */}
        {error && (
          <div className="mb-6 bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-xl flex items-start gap-3">
            <AlertCircle className="w-5 h-5 mt-0.5" />
            <p className="text-sm">{error}</p>
          </div>
        )}

        <form onSubmit={handleCalculate} className="bg-white rounded-2xl shadow-sm border border-gray-100 p-8">

          <div className="grid grid-cols-1 md:grid-cols-2 gap-8 mb-8">
            {/* Type de financement */}
            <div>
              <label className="block text-[#1c2951] font-semibold text-sm mb-2">Choisir le type de financement</label>
              <div className="relative">
                <select
                  value={typeCredit}
                  onChange={(e) => setTypeCredit(e.target.value)}
                  className="w-full appearance-none border border-gray-300 rounded-md py-3 px-4 text-gray-700 leading-tight focus:outline-none focus:ring-2 focus:ring-[#c8102e]/20 focus:border-[#c8102e]"
                >
                  <option>Crédit consommation</option>
                  <option>Crédit aménagement</option>
                  <option>Crédit BH auto</option>
                </select>
                <ChevronDown className="absolute right-3 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-400 pointer-events-none" />
              </div>
            </div>
          </div>

          {/* Info Banner TMM */}
          <div className="bg-gray-50 border border-gray-100 rounded-lg py-4 flex items-center justify-center gap-3 text-sm text-[#1c2951] mb-8 font-medium">
            <Info className="w-4 h-4 text-[#c8102e]" />
            <span>TMM <strong className="font-bold">{formatPct(tmmValue)}</strong></span>
            <span className="text-gray-300">|</span>
            <span>Taux {typeCredit.toLowerCase()} (%) <strong className="font-bold">{formatPct(tauxTotal)}</strong></span>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-8 mb-8 pb-8 border-b border-gray-100">
            {/* Montant crédit */}
            <div>
              <label className="block text-[#1c2951] font-semibold text-sm mb-2">Montant souhaité</label>
              <div className="flex rounded-md shadow-sm border border-gray-300 focus-within:border-[#c8102e] focus-within:ring-2 focus-within:ring-[#c8102e]/20 overflow-hidden">
                <input
                  type="number"
                  value={montant}
                  onChange={(e) => setMontant(parseInt(e.target.value) || 0)}
                  className="flex-1 py-3 px-4 text-gray-700 focus:outline-none"
                  step="1000"
                />
                <span className="inline-flex items-center px-4 rounded-r-md border-l border-gray-300 bg-gray-50 text-gray-500 text-sm">
                  TND
                </span>
              </div>
            </div>

            {/* Durée */}
            <div>
              <label className="block text-[#1c2951] font-semibold text-sm mb-2">Durée de remboursement</label>
              <div className="flex rounded-md shadow-sm border border-gray-300 focus-within:border-[#c8102e] focus-within:ring-2 focus-within:ring-[#c8102e]/20 overflow-hidden">
                <input
                  type="number"
                  value={duree}
                  onChange={(e) => setDuree(parseInt(e.target.value) || 0)}
                  className="flex-1 py-3 px-4 text-gray-700 focus:outline-none"
                  step="12"
                />
                <span className="inline-flex items-center px-4 rounded-r-md border-l border-gray-300 bg-gray-50 text-gray-500 text-sm">
                  MOIS
                </span>
              </div>
            </div>
          </div>

          {/* --- AUTO EXTRA FIELDS --- */}
          {typeCredit === 'Crédit BH auto' && (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-8 mb-8 pb-8 border-b border-gray-100 bg-blue-50/50 p-6 rounded-xl">
              <div>
                <label className="block text-[#1c2951] font-semibold text-sm mb-2">Puissance fiscale (Chevaux)</label>
                <input
                  type="number" value={chevaux} min="4" step="1"
                  onChange={(e) => setChevaux(parseInt(e.target.value))}
                  className="w-full border border-gray-300 rounded-md py-3 px-4 text-gray-700 focus:ring-2 focus:ring-[#c8102e]/20 focus:outline-none"
                />
              </div>
              <div>
                <label className="block text-[#1c2951] font-semibold text-sm mb-2">État du véhicule</label>
                <select
                  value={etatVehicule} onChange={(e) => setEtatVehicule(e.target.value)}
                  className="w-full appearance-none border border-gray-300 rounded-md py-3 px-4 text-gray-700 focus:ring-2 focus:ring-[#c8102e]/20 focus:outline-none"
                >
                  <option value="Neuf">Neuf</option>
                  <option value="Occasion">Occasion</option>
                </select>
              </div>
            </div>
          )}

          {/* File Uploader */}
          <div className="mb-8">
            <label className="block text-[#1c2951] font-semibold text-sm mb-2">Fiche de paie (Format PDF) *</label>
            <label
              htmlFor="fiche-upload"
              className={`flex flex-col items-center justify-center w-full h-32 border-2 border-dashed rounded-lg cursor-pointer transition-colors ${fichePaie ? 'border-green-400 bg-green-50' : 'border-blue-200 hover:bg-gray-50'}`}
            >
              <div className="flex flex-col items-center justify-center pt-5 pb-6">
                {fichePaie ? (
                  <>
                    <CheckCircle className="w-8 h-8 text-green-500 mb-2" />
                    <p className="text-sm font-semibold text-green-700">{fichePaie.name}</p>
                  </>
                ) : (
                  <>
                    <Upload className="w-8 h-8 text-blue-300 mb-2" />
                    <p className="text-sm text-gray-500 font-semibold mb-1">Cliquer pour télécharger</p>
                    <p className="text-xs text-gray-400">PDF uniquement</p>
                  </>
                )}
              </div>
              <input id="fiche-upload" type="file" accept=".pdf" className="hidden" onChange={handleFileChange} />
            </label>
          </div>

          {/* Submit */}
          <div className="flex justify-end">
            <button
              type="submit"
              disabled={loading}
              className="bg-[#101e40] text-white px-10 py-3.5 rounded-full font-bold uppercase tracking-wide hover:bg-[#c8102e] hover:-translate-y-1 hover:shadow-lg transition-all disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
            >
              {loading ? <span className="animate-spin w-5 h-5 border-2 border-white/30 border-t-white rounded-full"></span> : null}
              Calculer
            </button>
          </div>
        </form>

        {/* Loading State Overlay */}
        {loading && (
          <div className="mt-8 bg-blue-50 border border-blue-100 rounded-xl p-8 flex flex-col items-center justify-center text-center animate-pulse">
            <BrainCircuit className="w-12 h-12 text-[#c8102e] mb-4 animate-bounce" />
            <h3 className="text-xl font-bold text-[#1c2951] mb-2">Analyse Multi-Agent en cours...</h3>
            <p className="text-gray-500 max-w-md">L'Agent Superviseur, l'Agent Financier et l'Agent de Risque analysent actuellement votre dossier (extraction OCR, vérification DB, calcul capacité).</p>
          </div>
        )}
      </div> {/* Close the constrained max-w-4xl wrapper form here */}

      {/* Results with Expanded Horizontal Tabbed Layout */}
      {result && !loading && (
        <div className="max-w-[95%] xl:max-w-[1400px] mx-auto px-4 mt-12 mb-12">
          <div className="bg-white rounded-3xl shadow-2xl border border-gray-100 overflow-hidden flex flex-col md:flex-row min-h-[750px] lg:min-h-[850px]">
            {/* Sidebar Navigation */}
            <div className="md:w-[320px] shrink-0 bg-slate-50 border-r border-gray-100 p-6 lg:p-8 flex flex-col relative z-20">
              <h2 className="text-xl font-bold text-[#1c2951] mb-6 px-2">Parcours d'Analyse</h2>
              
              <div className="space-y-4 flex-grow mt-4">
                {/* Supervisor Tab */}
                <button 
                  onClick={() => setActiveTab('supervisor')}
                  className={`group w-full text-left px-5 py-5 rounded-2xl transition-all duration-300 flex items-center gap-5 ${
                    activeTab === 'supervisor' 
                    ? 'bg-white shadow-lg border border-gray-100 ring-1 ring-green-500/20 scale-[1.02]' 
                    : 'bg-white/40 hover:bg-white hover:shadow-md border border-transparent hover:border-gray-100'
                  }`}
                >
                  <div className={`p-3.5 rounded-xl transition-all duration-300 ${
                    activeTab === 'supervisor' 
                    ? 'bg-green-100 text-green-600 scale-110 shadow-sm' 
                    : 'bg-gray-100 text-gray-400 group-hover:bg-green-50 group-hover:text-green-500'
                  }`}>
                    <CheckCircle2 className="w-6 h-6" />
                  </div>
                  <div className="flex-1 transition-transform duration-300 group-hover:translate-x-1">
                    <span className={`block font-extrabold text-xs tracking-widest uppercase mb-1 ${activeTab === 'supervisor' ? 'text-green-600' : 'text-gray-400 group-hover:text-green-500'}`}>Étape 1</span>
                    <span className={`block text-lg font-bold ${activeTab === 'supervisor' ? 'text-[#1c2951]' : 'text-gray-600'}`}>Rapport Superviseur</span>
                  </div>
                  {activeTab === 'supervisor' && (
                    <div className="ml-auto w-3 h-3 rounded-full bg-green-500 shadow-[0_0_8px_rgba(34,197,94,0.6)]"></div>
                  )}
                </button>

                {/* Finance Tab */}
                {result.finance_report && (
                  <button 
                    onClick={() => setActiveTab('finance')}
                    className={`group w-full text-left px-5 py-5 rounded-2xl transition-all duration-300 flex items-center gap-5 ${
                      activeTab === 'finance' 
                      ? 'bg-white shadow-lg border border-gray-100 ring-1 ring-blue-500/20 scale-[1.02]' 
                      : 'bg-white/40 hover:bg-white hover:shadow-md border border-transparent hover:border-gray-100'
                    }`}
                  >
                    <div className={`p-3.5 rounded-xl transition-all duration-300 ${
                      activeTab === 'finance' 
                      ? 'bg-blue-100 text-blue-600 scale-110 shadow-sm' 
                      : 'bg-gray-100 text-gray-400 group-hover:bg-blue-50 group-hover:text-blue-500'
                    }`}>
                      <FileText className="w-6 h-6" />
                    </div>
                    <div className="flex-1 transition-transform duration-300 group-hover:translate-x-1">
                      <span className={`block font-extrabold text-xs tracking-widest uppercase mb-1 ${activeTab === 'finance' ? 'text-blue-600' : 'text-gray-400 group-hover:text-blue-500'}`}>Étape 2</span>
                      <span className={`block text-lg font-bold ${activeTab === 'finance' ? 'text-[#1c2951]' : 'text-gray-600'}`}>Analyse Financière</span>
                    </div>
                    {activeTab === 'finance' && (
                      <div className="ml-auto w-3 h-3 rounded-full bg-blue-500 shadow-[0_0_8px_rgba(59,130,246,0.6)]"></div>
                    )}
                  </button>
                )}

                {/* Risk Tab */}
                {result.risk_report && (
                  <button 
                    onClick={() => setActiveTab('risk')}
                    className={`group w-full text-left px-5 py-5 rounded-2xl transition-all duration-300 flex items-center gap-5 ${
                      activeTab === 'risk' 
                      ? 'bg-white shadow-lg border border-gray-100 ring-1 ring-orange-500/20 scale-[1.02]' 
                      : 'bg-white/40 hover:bg-white hover:shadow-md border border-transparent hover:border-gray-100'
                    }`}
                  >
                    <div className={`p-3.5 rounded-xl transition-all duration-300 ${
                      activeTab === 'risk' 
                      ? 'bg-orange-100 text-orange-600 scale-110 shadow-sm' 
                      : 'bg-gray-100 text-gray-400 group-hover:bg-orange-50 group-hover:text-orange-500'
                    }`}>
                      <AlertCircle className="w-6 h-6" />
                    </div>
                    <div className="flex-1 transition-transform duration-300 group-hover:translate-x-1">
                      <span className={`block font-extrabold text-xs tracking-widest uppercase mb-1 ${activeTab === 'risk' ? 'text-orange-600' : 'text-gray-400 group-hover:text-orange-500'}`}>Étape 3</span>
                      <span className={`block text-lg font-bold ${activeTab === 'risk' ? 'text-[#1c2951]' : 'text-gray-600'}`}>Analyse de Risque</span>
                    </div>
                    {activeTab === 'risk' && (
                      <div className="ml-auto w-3 h-3 rounded-full bg-orange-500 shadow-[0_0_8px_rgba(249,115,22,0.6)]"></div>
                    )}
                  </button>
                )}
                
                {/* Decision Tab */}
                {result.final_decision && (
                  <button 
                    onClick={() => setActiveTab('decision')}
                    className={`group w-full text-left px-5 py-6 rounded-2xl transition-all duration-300 flex items-center gap-5 mt-8 ${
                      activeTab === 'decision' 
                      ? 'bg-gradient-to-r from-[#1c2951] to-[#101e40] text-white shadow-xl shadow-[#1c2951]/20 scale-[1.02] border border-transparent' 
                      : 'bg-gray-200/50 hover:bg-[#1c2951] hover:text-white hover:shadow-lg border border-transparent'
                    }`}
                  >
                    <div className={`p-3.5 rounded-xl transition-all duration-300 ${
                      activeTab === 'decision' 
                      ? 'bg-white/20 text-white scale-110 shadow-inner' 
                      : 'bg-gray-300 text-gray-500 group-hover:bg-white/20 group-hover:text-white'
                    }`}>
                      <ShieldCheck className="w-6 h-6" />
                    </div>
                    <div className="flex-1 transition-transform duration-300 group-hover:translate-x-1">
                      <span className={`block font-extrabold text-xs tracking-widest uppercase mb-1 ${activeTab === 'decision' ? 'text-blue-200' : 'text-gray-500 group-hover:text-blue-200'}`}>Conclusion</span>
                      <span className={`block text-xl font-black ${activeTab === 'decision' ? 'text-white' : 'text-[#1c2951] group-hover:text-white'}`}>Décision Finale</span>
                    </div>
                    {activeTab === 'decision' && (
                      <div className="ml-auto text-[#c8102e] bg-white rounded-full p-1 shadow-sm">
                        <ChevronRight className="w-5 h-5" />
                      </div>
                    )}
                  </button>
                )}
              </div>
            </div>

            {/* Content Area */}
            <div className="flex-1 p-8 md:p-12 lg:p-16 bg-white relative flex flex-col">
              <AnimatePresence mode="wait">
                
                {/* Supervisor Content */}
                {activeTab === 'supervisor' && (
                  <motion.div
                    key="supervisor"
                    initial={{ opacity: 0, x: 20 }}
                    animate={{ opacity: 1, x: 0 }}
                    exit={{ opacity: 0, x: -20 }}
                    transition={{ duration: 0.3 }}
                    className="h-full flex flex-col"
                  >
                    <div className="flex items-center gap-4 mb-8 pb-6 border-b border-gray-100">
                      <div className="w-12 h-12 rounded-full bg-green-50 flex items-center justify-center">
                        <CheckCircle2 className="w-6 h-6 text-green-500" />
                      </div>
                      <div>
                        <h3 className="text-2xl font-bold text-[#1c2951]">Rapport du Superviseur</h3>
                        <p className="text-gray-500 text-sm">Vérification de l'identité et complétude du dossier</p>
                      </div>
                    </div>
                    
                    <div className="flex-grow overflow-y-auto pr-2 custom-scrollbar">
                      {result.validation_warnings?.length > 0 && (
                        <div className="mb-6 bg-red-50 border-l-4 border-[#c8102e] p-5 rounded-r-xl">
                          <h4 className="flex items-center gap-2 font-bold text-[#c8102e] mb-3">
                            <AlertTriangle className="w-5 h-5" /> Avertissements Bloquants
                          </h4>
                          <ul className="space-y-2 text-red-900 text-sm">
                            {result.validation_warnings.map((w: string, i: number) => (
                              <li key={i} className="flex gap-2">
                                <span className="text-[#c8102e]">•</span>
                                <span>{w}</span>
                              </li>
                            ))}
                          </ul>
                        </div>
                      )}
                      <div className="w-full text-sm">
                        {formatReportText(result.supervisor_info)}
                      </div>
                    </div>
                  </motion.div>
                )}

                {/* Finance Content */}
                {activeTab === 'finance' && result.finance_report && (
                  <motion.div
                    key="finance"
                    initial={{ opacity: 0, x: 20 }}
                    animate={{ opacity: 1, x: 0 }}
                    exit={{ opacity: 0, x: -20 }}
                    transition={{ duration: 0.3 }}
                    className="h-full flex flex-col"
                  >
                    <div className="flex items-center gap-4 mb-8 pb-6 border-b border-gray-100">
                      <div className="w-12 h-12 rounded-full bg-blue-50 flex items-center justify-center">
                        <FileText className="w-6 h-6 text-blue-600" />
                      </div>
                      <div>
                        <h3 className="text-2xl font-bold text-[#1c2951]">Évaluation Financière</h3>
                        <p className="text-gray-500 text-sm">Simulation des capacités de remboursement</p>
                      </div>
                    </div>
                    
                    <div className="flex-grow overflow-y-auto pr-2 custom-scrollbar">
                      <div className="bg-slate-50 p-6 rounded-2xl border border-gray-100 text-sm">
                        {formatReportText(result.finance_report.replace('### 📊 ANALYSE FINANCIÈRE:\n', ''))}
                      </div>
                    </div>
                  </motion.div>
                )}

                {/* Risk Content */}
                {activeTab === 'risk' && result.risk_report && (
                  <motion.div
                    key="risk"
                    initial={{ opacity: 0, x: 20 }}
                    animate={{ opacity: 1, x: 0 }}
                    exit={{ opacity: 0, x: -20 }}
                    transition={{ duration: 0.3 }}
                    className="h-full flex flex-col"
                  >
                    <div className="flex items-center gap-4 mb-8 pb-6 border-b border-gray-100">
                      <div className="w-12 h-12 rounded-full bg-orange-50 flex items-center justify-center">
                        <AlertCircle className="w-6 h-6 text-orange-500" />
                      </div>
                      <div>
                        <h3 className="text-2xl font-bold text-[#1c2951]">Analyse des Risques</h3>
                        <p className="text-gray-500 text-sm">Évaluation du profil de risque via Machine Learning</p>
                      </div>
                    </div>
                    
                    <div className="flex-grow overflow-y-auto pr-2 custom-scrollbar">
                      <div className="bg-orange-50/50 p-6 rounded-2xl border border-orange-100 text-sm">
                        {formatReportText(result.risk_report)}
                      </div>
                    </div>
                  </motion.div>
                )}

                {/* Decision Content */}
                {activeTab === 'decision' && result.final_decision && (
                  <motion.div
                    key="decision"
                    initial={{ opacity: 0, scale: 0.95 }}
                    animate={{ opacity: 1, scale: 1 }}
                    exit={{ opacity: 0, scale: 0.95 }}
                    transition={{ duration: 0.4, type: "spring" }}
                    className="h-full flex flex-col justify-center items-center text-center p-4 overflow-y-auto custom-scrollbar"
                  >
                    <div className="w-20 h-20 bg-[#c8102e]/10 rounded-full flex items-center justify-center mb-6 shrink-0">
                      <ShieldCheck className="w-10 h-10 text-[#c8102e]" />
                    </div>
                    
                    <h3 className="text-sm font-bold text-gray-400 uppercase tracking-[0.2em] mb-2 shrink-0">Verdict du Comité Virtuel</h3>
                    <h2 className="text-3xl font-black text-[#1c2951] mb-8 shrink-0">Décision Finale</h2>
                    
                    <div className="w-full max-w-4xl bg-gradient-to-br from-[#1c2951] to-[#101e40] text-white p-8 md:p-10 rounded-3xl shadow-2xl relative overflow-hidden">
                      {/* Decorative Background Elements */}
                      <div className="absolute top-0 right-0 -mr-8 -mt-8 w-32 h-32 rounded-full bg-white opacity-5 mix-blend-overlay"></div>
                      <div className="absolute bottom-0 left-0 -ml-8 -mb-8 w-24 h-24 rounded-full bg-[#c8102e] opacity-20 mix-blend-overlay"></div>
                      
                      <div className="relative z-10 text-left text-sm md:text-base font-medium opacity-95 columns-1 md:columns-2 gap-8 md:gap-12">
                        {formatReportText(result.final_decision, true)}
                      </div>
                    </div>
                  </motion.div>
                )}

              </AnimatePresence>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
