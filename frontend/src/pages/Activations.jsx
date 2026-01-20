import { useState, useEffect } from 'react';
import '../components/Cards.css';

function Activations({ token }) {
    const [activations, setActivations] = useState([]);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        fetchActivations();
    }, []);

    const fetchActivations = async () => {
        setLoading(true);
        try {
            const res = await fetch('/admin/activations', {
                headers: { 'Authorization': `Bearer ${token}` }
            });
            const data = await res.json();
            setActivations(data.activations);
        } catch (err) {
            console.error('Failed to fetch activations:', err);
        } finally {
            setLoading(false);
        }
    };

    const handleDeactivate = async (activationId) => {
        if (!confirm('Deactivate this device?')) return;

        try {
            await fetch(`/admin/activation/${activationId}`, {
                method: 'DELETE',
                headers: { 'Authorization': `Bearer ${token}` }
            });
            fetchActivations();
        } catch (err) {
            alert('Failed to deactivate device');
        }
    };

    return (
        <div className="activations">
            <div className="page-header">
                <h2>Device Activations</h2>
                <button onClick={fetchActivations} className="refresh-btn">🔄 Refresh</button>
            </div>

            {loading ? (
                <div className="loading">Loading activations...</div>
            ) : (
                <div className="licenses-table">
                    <table>
                        <thead>
                            <tr>
                                <th>License Key</th>
                                <th>Customer</th>
                                <th>Device Name</th>
                                <th>Hardware ID</th>
                                <th>Activated</th>
                                <th>Last Validation</th>
                                <th>Status</th>
                                <th>Actions</th>
                            </tr>
                        </thead>
                        <tbody>
                            {activations.map((activation) => (
                                <tr key={activation.id}>
                                    <td className="license-key-cell">
                                        <code>{activation.license_key}</code>
                                    </td>
                                    <td>{activation.customer_name}</td>
                                    <td>{activation.device_name || 'Unknown Device'}</td>
                                    <td>
                                        <code style={{ fontSize: '11px' }}>
                                            {activation.hardware_fingerprint.substring(0, 16)}...
                                        </code>
                                    </td>
                                    <td>{new Date(activation.activated_at).toLocaleDateString()}</td>
                                    <td>{new Date(activation.last_validated).toLocaleString()}</td>
                                    <td>
                                        <span className={`status-badge ${activation.is_active ? 'status-active' : 'status-expired'}`}>
                                            {activation.is_active ? 'Active' : 'Inactive'}
                                        </span>
                                    </td>
                                    <td>
                                        {activation.is_active && (
                                            <button
                                                onClick={() => handleDeactivate(activation.id)}
                                                className="action-btn btn-danger"
                                            >
                                                Deactivate
                                            </button>
                                        )}
                                    </td>
                                </tr>
                            ))}
                        </tbody>
                    </table>
                    {activations.length === 0 && (
                        <div style={{ padding: '40px', textAlign: 'center', color: '#999' }}>
                            No activations found
                        </div>
                    )}
                </div>
            )}
        </div>
    );
}

export default Activations;
