import { useState, useEffect } from 'react';
import '../components/Cards.css';

function Overview({ token }) {
    const [stats, setStats] = useState(null);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        fetchStats();
    }, []);

    const fetchStats = async () => {
        try {
            const res = await fetch('/admin/stats', {
                headers: { 'Authorization': `Bearer ${token}` }
            });
            const data = await res.json();
            setStats(data);
        } catch (err) {
            console.error('Failed to fetch stats:', err);
        } finally {
            setLoading(false);
        }
    };

    if (loading) return <div className="loading">Loading stats...</div>;
    if (!stats) return <div className="error">Failed to load statistics</div>;

    const cards = [
        { label: 'Total Licenses', value: stats.total_licenses, icon: '📜', color: '#667eea' },
        { label: 'Active Licenses', value: stats.active_licenses, icon: '✅', color: '#48bb78' },
        { label: 'Expired Licenses', value: stats.expired_licenses, icon: '⏰', color: '#ed8936' },
        { label: 'Blocked Licenses', value: stats.blocked_licenses, icon: '🚫', color: '#f56565' },
        { label: 'Total Activations', value: stats.total_activations, icon: '💻', color: '#4299e1' },
    ];

    return (
        <div className="overview">
            <div className="page-header">
                <h2>Dashboard Overview</h2>
                <button onClick={fetchStats} className="refresh-btn">🔄 Refresh</button>
            </div>

            <div className="stats-grid">
                {cards.map((card, i) => (
                    <div key={i} className="stat-card" style={{ borderLeftColor: card.color }}>
                        <div className="stat-icon" style={{ background: `${card.color}20`, color: card.color }}>
                            {card.icon}
                        </div>
                        <div className="stat-info">
                            <div className="stat-label">{card.label}</div>
                            <div className="stat-value">{card.value}</div>
                        </div>
                    </div>
                ))}
            </div>

            <div className="info-section">
                <div className="info-card">
                    <h3>🎯 Quick Actions</h3>
                    <ul>
                        <li>Generate new license keys</li>
                        <li>View and manage all licenses</li>
                        <li>Monitor active device activations</li>
                        <li>Block/unblock licenses remotely</li>
                        <li>Extend expiry dates</li>
                    </ul>
                </div>
            </div>
        </div>
    );
}

export default Overview;
