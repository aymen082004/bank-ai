import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import { BrowserRouter } from 'react-router-dom';
import { GoogleOAuthProvider } from '@react-oauth/google';
import { AuthProvider } from './context/AuthContext';
import App from './App.tsx';
import './index.css';

const clientId = import.meta.env.VITE_GOOGLE_CLIENT_ID || '256261234818-f8ql0ln07f4t11fprj5cm81acae6bdtl.apps.googleusercontent.com';

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <BrowserRouter>
      <AuthProvider>
        <GoogleOAuthProvider clientId={clientId}>
          <App />
        </GoogleOAuthProvider>
      </AuthProvider>
    </BrowserRouter>
  </StrictMode>
);
