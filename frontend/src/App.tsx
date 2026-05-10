import React from 'react';
import { Routes, Route, useLocation, Navigate } from 'react-router-dom';
import Header from './components/Header';
import Footer from './components/Footer';
import Home from './pages/Home';
import Login from './pages/Login';
import Register from './pages/Register';
import Dashboard from './pages/Dashboard';
import ComplaintChat from './pages/ComplaintChat';
import BankAgent from './pages/BankAgent';
import CreditAgent from './pages/CreditAgent';
import FraudDetection from './pages/FraudDetection';
import InvestmentAgent from './pages/InvestmentAgent';
import { useAuth } from './context/AuthContext';

const ProtectedRoute = ({ children }: { children: React.ReactNode }) => {
  const { user, token } = useAuth();
  
  if (!user || !token) {
    return <Navigate to="/login" replace />;
  }
  
  return <>{children}</>;
};

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
        
        <Route path="/dashboard" element={
          <ProtectedRoute><Dashboard /></ProtectedRoute>
        } />
        <Route path="/complaint-agent" element={
          <ProtectedRoute><ComplaintChat /></ProtectedRoute>
        } />
        <Route path="/bank-agent" element={
          <ProtectedRoute><BankAgent /></ProtectedRoute>
        } />
        <Route path="/credit-agent" element={
          <ProtectedRoute><CreditAgent /></ProtectedRoute>
        } />
        <Route path="/fraud-agent" element={
          <ProtectedRoute><FraudDetection /></ProtectedRoute>
        } />
        <Route path="/investment-agent" element={
          <ProtectedRoute><InvestmentAgent /></ProtectedRoute>
        } />
      </Routes>
      {!isComplaintPage && <Footer />}
    </div>
  );
}

export default App;