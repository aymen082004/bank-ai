import React from 'react';
import { useAuth } from '../context/AuthContext';
import { Navigate } from 'react-router-dom';

const Dashboard = () => {
  const { user } = useAuth();

  if (!user) {
    return <Navigate to="/login" replace />;
  }

  return (
    <div className="min-h-screen bg-gray-50 flex flex-col p-8 items-center pt-24 font-sans">
      <div className="bg-white shadow-xl rounded-xl p-8 max-w-4xl w-full border-t-4 border-[#1c2951]">
        <h1 className="text-3xl font-extrabold text-[#1c2951] mb-2">
          Tableau de bord
        </h1>
        <p className="text-gray-600 mb-8 border-b pb-4">
          Bienvenue sur votre espace, {user.name} ! Connecté en tant que: <span className="font-semibold text-[#c8102e]">{user.role}</span>
        </p>

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

      </div>
    </div>
  );
};

export default Dashboard;
