import React from 'react';
import { useAuth } from '../context/AuthContext';
import { Navigate } from 'react-router-dom';

const Dashboard = () => {
  const { user } = useAuth();

  if (!user) {
    return <Navigate to="/login" replace />;
  }

  const isChefAgency = user.role === 'chef of agency';
  const isCustomer = user.role === 'customer';

  return (
    <div className="min-h-screen bg-gray-50 flex flex-col p-8 items-center pt-24 font-sans">
      <div className="bg-white shadow-xl rounded-xl p-8 max-w-4xl w-full border-t-4 border-[#1c2951]">
        <h1 className="text-3xl font-extrabold text-[#1c2951] mb-2">
          {isChefAgency ? 'Tableau de bord - Chef d\'agence' : 'Tableau de bord'}
        </h1>
        <p className="text-gray-600 mb-8 border-b pb-4">
          Bienvenue, {user.name} ! Connecté en tant que: <span className="font-semibold text-[#c8102e]">{user.role}</span>
        </p>

        {isChefAgency ? (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            <div className="p-6 border border-gray-100 rounded-xl bg-blue-50 flex flex-col items-center justify-center text-center">
              <div className="w-16 h-16 bg-blue-100 rounded-full shadow flex items-center justify-center mb-4">
                <span className="text-2xl">📊</span>
              </div>
              <h3 className="font-bold text-lg mb-2">Statistiques</h3>
              <p className="text-sm text-gray-500">Vue d'ensemble des performances</p>
            </div>
            <div className="p-6 border border-gray-100 rounded-xl bg-red-50 flex flex-col items-center justify-center text-center">
              <div className="w-16 h-16 bg-red-100 rounded-full shadow flex items-center justify-center mb-4">
                <span className="text-2xl">📝</span>
              </div>
              <h3 className="font-bold text-lg mb-2">Réclamations</h3>
              <p className="text-sm text-gray-500">Gérer les réclamations clients</p>
            </div>
            <div className="p-6 border border-gray-100 rounded-xl bg-green-50 flex flex-col items-center justify-center text-center">
              <div className="w-16 h-16 bg-green-100 rounded-full shadow flex items-center justify-center mb-4">
                <span className="text-2xl">👥</span>
              </div>
              <h3 className="font-bold text-lg mb-2">Suivi des agents</h3>
              <p className="text-sm text-gray-500">Voir la performance des agents</p>
            </div>
            <div className="p-6 border border-gray-100 rounded-xl bg-purple-50 flex flex-col items-center justify-center text-center">
              <div className="w-16 h-16 bg-purple-100 rounded-full shadow flex items-center justify-center mb-4">
                <span className="text-2xl">📅</span>
              </div>
              <h3 className="font-bold text-lg mb-2">rdv Clients</h3>
              <p className="text-sm text-gray-500">Gestion des rendez-vous</p>
            </div>
            <div className="p-6 border border-gray-100 rounded-xl bg-yellow-50 flex flex-col items-center justify-center text-center">
              <div className="w-16 h-16 bg-yellow-100 rounded-full shadow flex items-center justify-center mb-4">
                <span className="text-2xl">📈</span>
              </div>
              <h3 className="font-bold text-lg mb-2">Rapports</h3>
              <p className="text-sm text-gray-500">Générer des rapports</p>
            </div>
            <div className="p-6 border border-gray-100 rounded-xl bg-gray-50 flex flex-col items-center justify-center text-center">
              <div className="w-16 h-16 bg-gray-100 rounded-full shadow flex items-center justify-center mb-4">
                <span className="text-2xl">⚙️</span>
              </div>
              <h3 className="font-bold text-lg mb-2">Paramètres</h3>
              <p className="text-sm text-gray-500">Configuration du système</p>
            </div>
          </div>
        ) : isCustomer ? (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div className="p-6 border border-gray-100 rounded-xl bg-gray-50 flex flex-col items-center justify-center text-center">
              <div className="w-16 h-16 bg-white rounded-full shadow flex items-center justify-center mb-4">
                <span className="text-2xl">🤖</span>
              </div>
              <h3 className="font-bold text-lg mb-2">Agent de la Banque</h3>
              <p className="text-sm text-gray-500 mb-4 px-4">
                Communiquez avec notre agent intelligent pour vos requêtes.
              </p>
              <button className="px-6 py-2 bg-[#1c2951] text-white text-sm font-semibold rounded-full hover:bg-[#263766] transition">
                Démarrer
              </button>
            </div>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div className="p-6 border border-gray-100 rounded-xl bg-red-50 flex flex-col items-center justify-center text-center">
              <div className="w-16 h-16 bg-white rounded-full shadow flex items-center justify-center mb-4">
                <span className="text-2xl">🛡️</span>
              </div>
              <h3 className="font-bold text-lg mb-2">Détection de Fraude</h3>
              <p className="text-sm text-gray-500">Analyser les transactions suspected</p>
            </div>
            <div className="p-6 border border-gray-100 rounded-xl bg-blue-50 flex flex-col items-center justify-center text-center">
              <div className="w-16 h-16 bg-white rounded-full shadow flex items-center justify-center mb-4">
                <span className="text-2xl">📊</span>
              </div>
              <h3 className="font-bold text-lg mb-2">Analyse & Reporting</h3>
              <p className="text-sm text-gray-500">Rapports financiers détaillés</p>
            </div>
          </div>
        )}

      </div>
    </div>
  );
};

export default Dashboard;
