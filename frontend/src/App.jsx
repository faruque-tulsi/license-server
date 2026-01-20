import { useState, useEffect } from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import Login from './pages/Login';
import Dashboard from './pages/Dashboard';
import './App.css';

const API_BASE = '';

function App() {
    const [isAuthenticated, setIsAuthenticated] = useState(false);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        // Check for existing token
        const token = localStorage.getItem('admin_token');
        if (token) {
            setIsAuthenticated(true);
        }
        setLoading(false);
    }, []);

    const handleLogin = (token) => {
        localStorage.setItem('admin_token', token);
        setIsAuthenticated(true);
    };

    const handleLogout = () => {
        localStorage.removeItem('admin_token');
        setIsAuthenticated(false);
    };

    if (loading) {
        return <div className="loading">Loading...</div>;
    }

    return (
        <Router>
            <Routes>
                <Route
                    path="/login"
                    element={
                        isAuthenticated ?
                            <Navigate to="/" /> :
                            <Login onLogin={handleLogin} />
                    }
                />
                <Route
                    path="/*"
                    element={
                        isAuthenticated ?
                            <Dashboard onLogout={handleLogout} /> :
                            <Navigate to="/login" />
                    }
                />
            </Routes>
        </Router>
    );
}

export default App;
