import { useState, useEffect } from 'react';
import { Routes, Route, Link, useLocation } from 'react-router-dom';
import Overview from './Overview';
import GenerateLicense from './GenerateLicense';
import Licenses from './Licenses';
import Activations from './Activations';
import './Dashboard.css';

function Dashboard({ onLogout }) {
    const location = useLocation();
    const token = localStorage.getItem('admin_token');

    const navItems = [
        { path: '/', label: '📊 Overview', component: Overview },
        { path: '/generate', label: '➕ Generate License', component: GenerateLicense },
        { path: '/licenses', label: '📜 All Licenses', component: Licenses },
        { path: '/activations', label: '💻 Activations', component: Activations },
    ];

    const isActive = (path) => {
        if (path === '/') return location.pathname === '/';
        return location.pathname.startsWith(path);
    };

    return (
        <div className="dashboard">
            <div className="dashboard-header">
                <div className="header-left">
                    <h1>🔑 License Admin Panel</h1>
                </div>
                <button onClick={onLogout} className="logout-btn">Logout</button>
            </div>

            <div className="dashboard-nav">
                {navItems.map((item) => (
                    <Link
                        key={item.path}
                        to={item.path}
                        className={`nav-item ${isActive(item.path) ? 'active' : ''}`}
                    >
                        {item.label}
                    </Link>
                ))}
            </div>

            <div className="dashboard-content">
                <Routes>
                    <Route path="/" element={<Overview token={token} />} />
                    <Route path="/generate" element={<GenerateLicense token={token} />} />
                    <Route path="/licenses" element={<Licenses token={token} />} />
                    <Route path="/activations" element={<Activations token={token} />} />
                </Routes>
            </div>
        </div>
    );
}

export default Dashboard;
