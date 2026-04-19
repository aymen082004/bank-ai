import React from 'react';
import { Routes, Route, useLocation } from 'react-router-dom';
import Header from './components/Header';
import Footer from './components/Footer';
import Home from './pages/Home';
import Login from './pages/Login';
import Register from './pages/Register';
import Dashboard from './pages/Dashboard';
import ComplaintChat from './pages/ComplaintChat';
import StreamlitPage from './pages/Dashboard';
import CreditAgent from './pages/CreditAgent';
<<<<<<< HEAD
import BankAgent from './pages/BankAgent';
=======
>>>>>>> 68aa2a1b8a9eb571cdbc9054624cba1fb727a7e2


function App() {
  const location = useLocation();
  const isComplaintPage = location.pathname === '/complaint-agent';

  return (
    <div className="min-h-screen bg-white font-sans">
      <Header />
      <Routes>
        <Route path="/" element={<Home />} />
        <Route path="/login" element={<Login />} />
        <Route path="/register" element={<Register />} />
        <Route path="/dashboard" element={<Dashboard />} />
        <Route path="/complaint-agent" element={<ComplaintChat />} />
        <Route path="/credit-agent" element={<CreditAgent />} />
<<<<<<< HEAD
        <Route path="/bank-agent" element={<BankAgent />} />
=======
>>>>>>> 68aa2a1b8a9eb571cdbc9054624cba1fb727a7e2
        <Route path="/reporting" element={<StreamlitPage />} />
      </Routes>
      {!isComplaintPage && <Footer />}
    </div>
  );
}

export default App;
