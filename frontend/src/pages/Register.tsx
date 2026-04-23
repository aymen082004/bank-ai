import React, { useState, useEffect } from 'react';
import { useNavigate, Link, useLocation } from 'react-router-dom';
import { useGoogleLogin } from '@react-oauth/google';
import axios from 'axios';
import { useAuth } from '../context/AuthContext';

const Register = () => {
  const [name, setName] = useState('');
  const [email, setEmail] = useState('');
  const [phone, setPhone] = useState('');
  const [cin, setCin] = useState('');
  const role = 'customer';
  const [password, setPassword] = useState('');
  const [googleToken, setGoogleToken] = useState<string | null>(null);
  
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  
  const navigate = useNavigate();
  const location = useLocation();
  const { loginState } = useAuth();
  
  useEffect(() => {
    if (location.state && location.state.googleToken) {
      setGoogleToken(location.state.googleToken);
      if (location.state.nameProfile) setName(location.state.nameProfile);
      if (location.state.emailProfile) setEmail(location.state.emailProfile);
    }
  }, [location]);

  const handleRegister = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError('');
    
    try {
      if (googleToken) {
        const response = await axios.post(`${import.meta.env.VITE_API_URL}/api/auth/google/`, {
          token: googleToken,
          role: role,
          phone: phone,
          email: email,
          cin: cin,
        });
        const { token, user } = response.data;
        loginState(user, token);
        navigate('/');
      } else {
        const response = await axios.post(`${import.meta.env.VITE_API_URL}/api/auth/register/`, {
          name,
          email,
          phone,
          cin,
          role,
          password,
        });
        const { token, user } = response.data;
        loginState(user, token);
        navigate('/');
      }
    } catch (err: any) {
      setError(err.response?.data?.error || "Une erreur est survenue lors de l'inscription.");
    } finally {
      setLoading(false);
    }
  };

  const loginWithGoogle = useGoogleLogin({
    onSuccess: async (tokenResponse) => {
      setGoogleToken(tokenResponse.access_token);
      try {
        setLoading(true);
        const res = await axios.post(`${import.meta.env.VITE_API_URL}/api/auth/google/`, {
          token: tokenResponse.access_token,
        });
        
        if (!res.data.requiresRole) {
           const { token, user } = res.data;
           loginState(user, token);
           navigate('/');
        } else {
           if (res.data.name) setName(res.data.name);
           if (res.data.email) setEmail(res.data.email);
           setError("Veuillez compléter votre rôle et numéro de téléphone pour terminer l'inscription.");
           setLoading(false);
        }
      } catch (err) {
        setLoading(false);
      }
    },
    onError: () => setError('Erreur de connexion avec Google.'),
    scope: "openid https://www.googleapis.com/auth/userinfo.email https://www.googleapis.com/auth/userinfo.profile https://www.googleapis.com/auth/calendar"
  });

  return (
    <div className="min-h-screen bg-gray-50 flex flex-col justify-center py-12 sm:px-6 lg:px-8 font-sans">
      <div className="sm:mx-auto sm:w-full sm:max-w-md">
        <h2 className="mt-6 text-center text-3xl font-extrabold text-gray-900">
          Créer un compte
        </h2>
        <p className="mt-2 text-center text-sm text-gray-600">
          Ou{' '}
          <Link to="/login" className="font-medium text-[#c8102e] hover:text-red-700">
            connectez-vous à un compte existant
          </Link>
        </p>
      </div>

      <div className="mt-8 sm:mx-auto sm:w-full sm:max-w-md">
        <div className="bg-white py-8 px-4 shadow sm:rounded-lg sm:px-10 border-t-4 border-[#c8102e]">
          
          {googleToken && (
             <div className="mb-4 bg-blue-50 border-l-4 border-blue-400 p-4">
               <p className="text-sm text-blue-700">
                 Identifié avec Google. Veuillez choisir votre rôle et fournir votre téléphone et CIN.
               </p>
             </div>
          )}

          <form className="space-y-6" onSubmit={handleRegister}>
            <div>
              <label htmlFor="name" className="block text-sm font-medium text-gray-700">
                Nom et prénom
              </label>
              <div className="mt-1">
                <input
                  id="name"
                  name="name"
                  type="text"
                  required
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  className="appearance-none block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm placeholder-gray-400 focus:outline-none focus:ring-[#c8102e] focus:border-[#c8102e] sm:text-sm"
                />
              </div>
            </div>

            <div>
              <label htmlFor="email" className="block text-sm font-medium text-gray-700">
                Adresse Email (optionnel)
              </label>
              <div className="mt-1">
                <input
                  id="email"
                  name="email"
                  type="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  className="appearance-none block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm placeholder-gray-400 focus:outline-none focus:ring-[#c8102e] focus:border-[#c8102e] sm:text-sm"
                />
              </div>
            </div>

            <div>
              <label htmlFor="phone" className="block text-sm font-medium text-gray-700">
                Téléphone mobile
              </label>
              <div className="mt-1">
                <input
                  id="phone"
                  name="phone"
                  type="tel"
                  required
                  value={phone}
                  onChange={(e) => setPhone(e.target.value)}
                  className="appearance-none block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm placeholder-gray-400 focus:outline-none focus:ring-[#c8102e] focus:border-[#c8102e] sm:text-sm"
                />
              </div>
            </div>

            <div>
              <label htmlFor="cin" className="block text-sm font-medium text-gray-700">
                N° Carte d'Identité Nationale (CIN)
              </label>
              <div className="mt-1">
                <input
                  id="cin"
                  name="cin"
                  type="text"
                  value={cin}
                  onChange={(e) => setCin(e.target.value)}
                  className="appearance-none block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm placeholder-gray-400 focus:outline-none focus:ring-[#c8102e] focus:border-[#c8102e] sm:text-sm"
                />
              </div>
            </div>



            {!googleToken && (
              <div>
                <label htmlFor="password" className="block text-sm font-medium text-gray-700">
                  Mot de passe
                </label>
                <div className="mt-1">
                  <input
                    id="password"
                    name="password"
                    type="password"
                    required={!googleToken}
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    className="appearance-none block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm placeholder-gray-400 focus:outline-none focus:ring-[#c8102e] focus:border-[#c8102e] sm:text-sm"
                  />
                </div>
              </div>
            )}

            {error && (
              <div className="text-red-600 text-sm bg-red-50 p-3 rounded-md border border-red-200">
                {error}
              </div>
            )}

            <div>
              <button
                type="submit"
                disabled={loading}
                className="w-full flex justify-center py-2.5 px-4 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-[#1c2951] hover:bg-[#263766] focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-[#1c2951] transition-colors"
               >
                {loading ? 'Inscription...' : 'S\'inscrire'}
              </button>
            </div>
          </form>

          {!googleToken && (
            <div className="mt-6">
              <div className="relative">
                <div className="absolute inset-0 flex items-center">
                  <div className="w-full border-t border-gray-300" />
                </div>
                <div className="relative flex justify-center text-sm">
                  <span className="px-2 bg-white text-gray-500">Ou s'inscrire avec</span>
                </div>
              </div>

              <div className="mt-6">
                <button
                  onClick={() => loginWithGoogle()}
                  className="w-full flex justify-center py-2.5 px-4 border border-gray-300 rounded-md shadow-sm bg-white text-sm font-medium text-gray-700 hover:bg-gray-50 transition-colors gap-2 items-center"
                >
                  <img src="https://www.svgrepo.com/show/475656/google-color.svg" alt="Google" className="w-5 h-5" />
                  Google
                </button>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default Register;
