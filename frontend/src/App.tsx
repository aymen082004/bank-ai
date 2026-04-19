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
        <Route path="/reporting" element={<StreamlitPage />} />
      </Routes>
      {!isComplaintPage && <Footer />}
    </div>
  );
}

export default App;
