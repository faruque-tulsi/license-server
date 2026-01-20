import { useState, useEffect } from 'react';
import './Licenses.css';

function Licenses({ token }) {
    const [licenses, setLicenses] = useState([]);
    const [loading, setLoading] = useState(true);
    const [filter, setFilter] = useState('all');

    useEffect(() => {
        fetchLicenses();
    }, []);

    const fetchLicenses = async () => {
        setLoading(true);
        try {
            const res = await fetch('/admin/licenses', {
                headers: { 'Authorization': `Bearer ${token}` }
            });
            const data = await res.json();
            setLicenses(data.licenses);
        } catch (err) {
            console.error('Failed to fetch licenses:', err);
        } finally {
            setLoading(false);
        }
    };

    const handleBlock = async (licenseKey) => {
        if (!confirm('Block this license?')) return;

        try {
            await fetch('/admin/block', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${token}`
                },
                body: JSON.stringify({
                    license_key: licenseKey,
                    message: 'License blocked by administrator'
                })
            });
            fetchLicenses();
        } catch (err) {
            alert('Failed to block license');
        }
    };

    const handleUnblock = async (licenseKey) => {
        try {
            await fetch(`/admin/unblock?license_key=${licenseKey}`, {
                method: 'POST',
                headers: { 'Authorization': `Bearer ${token}` }
            });
            fetchLicenses();
        } catch (err) {
            alert('Failed to unblock license');
        }
    };

    const handleDelete = async (licenseKey) => {
        if (!confirm(`Are you sure you want to DELETE license ${licenseKey}? This action cannot be undone and will remove all activations.`)) {
            return;
        }

        try {
            const res = await fetch(`/admin/licenses/${licenseKey}`, {
                method: 'DELETE',
                headers: { 'Authorization': `Bearer ${token}` }
            });

            if (res.ok) {
                alert('License deleted successfully');
                fetchLicenses();
            } else {
                const error = await res.json();
                alert(`Failed to delete: ${error.detail || 'Unknown error'}`);
            }
        } catch (err) {
            alert('Failed to delete license');
        }
    };

    const getStatus = (license) => {
        if (license.is_blocked) return { label: 'Blocked', class: 'status-blocked' };
        if (new Date(license.expires_at) < new Date()) return { label: 'Expired', class: 'status-expired' };
        return { label: 'Active', class: 'status-active' };
    };

    const filteredLicenses = licenses.filter(license => {
        if (filter === 'active') return !license.is_blocked && new Date(license.expires_at) > new Date();
        if (filter === 'expired') return new Date(license.expires_at) < new Date();
        if (filter === 'blocked') return license.is_blocked;
        return true;
    });

    return (
        <div className="licenses">
            <div className="page-header">
                <h2>All Licenses</h2>
                <div className="filter-tabs">
                    <button className={filter === 'all' ? 'active' : ''} onClick={() => setFilter('all')}>
                        All ({licenses.length})
                    </button>
                    <button className={filter === 'active' ? 'active' : ''} onClick={() => setFilter('active')}>
                        Active
                    </button>
                    <button className={filter === 'expired' ? 'active' : ''} onClick={() => setFilter('expired')}>
                        Expired
                    </button>
                    <button className={filter === 'blocked' ? 'active' : ''} onClick={() => setFilter('blocked')}>
                        Blocked
                    </button>
                </div>
            </div>

            {loading ? (
                <div className="loading">Loading licenses...</div>
            ) : (
                <div className="licenses-table">
                    <table>
                        <thead>
                            <tr>
                                <th>License Key</th>
                                <th>Customer</th>
                                <th>Company</th>
                                <th>Expires</th>
                                <th>Activations</th>
                                <th>Status</th>
                                <th>Actions</th>
                            </tr>
                        </thead>
                        <tbody>
                            {filteredLicenses.map((license) => {
                                const status = getStatus(license);
                                return (
                                    <tr key={license.id}>
                                        <td className="license-key-cell">
                                            <code>{license.license_key}</code>
                                        </td>
                                        <td>{license.customer_name}</td>
                                        <td>{license.company_name || '-'}</td>
                                        <td>{new Date(license.expires_at).toLocaleDateString()}</td>
                                        <td>{license.activation_count || 0} / {license.max_activations}</td>
                                        <td>
                                            <span className={`status-badge ${status.class}`}>
                                                {status.label}
                                            </span>
                                        </td>
                                        <td>
                                            <div style={{ display: 'flex', gap: '8px' }}>
                                                {license.is_blocked ? (
                                                    <button onClick={() => handleUnblock(license.license_key)} className="action-btn btn-success">
                                                        Unblock
                                                    </button>
                                                ) : (
                                                    <button onClick={() => handleBlock(license.license_key)} className="action-btn btn-danger">
                                                        Block
                                                    </button>
                                                )}
                                                <button onClick={() => handleDelete(license.license_key)} className="action-btn btn-danger">
                                                    Delete
                                                </button>
                                            </div>
                                        </td>
                                    </tr>
                                );
                            })}
                        </tbody>
                    </table>
                </div>
            )}
        </div>
    );
}

export default Licenses;
