import { useState } from 'react';
import './GenerateLicense.css';

function GenerateLicense({ token }) {
    const [formData, setFormData] = useState({
        customer_name: '',
        company_name: '',
        email: '',
        phone: '',
        expires_at: '',
        max_activations: 1,
        restricted_fingerprint: '',
        notes: ''
    });
    const [loading, setLoading] = useState(false);
    const [result, setResult] = useState(null);
    const [error, setError] = useState('');

    const handleChange = (e) => {
        setFormData({ ...formData, [e.target.name]: e.target.value });
    };

    const handleSubmit = async (e) => {
        e.preventDefault();
        setLoading(true);
        setError('');
        setResult(null);

        try {
            const res = await fetch('/admin/generate', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${token}`
                },
                body: JSON.stringify(formData)
            });

            if (!res.ok) throw new Error('Failed to generate license');

            const data = await res.json();
            setResult(data);

            // Reset form
            setFormData({
                customer_name: '',
                company_name: '',
                email: '',
                phone: '',
                expires_at: '',
                max_activations: 1,
                restricted_fingerprint: '',
                notes: ''
            });
        } catch (err) {
            setError(err.message);
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="generate-license">
            <div className="page-header">
                <h2>Generate New License</h2>
            </div>

            {result && (
                <div className="success-card">
                    <h3>✅ License Generated Successfully!</h3>
                    <div className="license-key-display">
                        <label>License Key:</label>
                        <div className="license-key">{result.license_key}</div>
                        <button
                            onClick={() => navigator.clipboard.writeText(result.license_key)}
                            className="copy-btn"
                        >
                            📋 Copy
                        </button>
                    </div>
                    <p className="success-note">Save this license key and share it with the customer.</p>
                </div>
            )}

            {error && <div className="error-message">{error}</div>}

            <form onSubmit={handleSubmit} className="license-form">
                <div className="form-grid">
                    <div className="form-group">
                        <label>Customer Name *</label>
                        <input
                            type="text"
                            name="customer_name"
                            value={formData.customer_name}
                            onChange={handleChange}
                            required
                            placeholder="Enter customer name"
                        />
                    </div>

                    <div className="form-group">
                        <label>Company Name</label>
                        <input
                            type="text"
                            name="company_name"
                            value={formData.company_name}
                            onChange={handleChange}
                            placeholder="Enter company name (optional)"
                        />
                    </div>

                    <div className="form-group">
                        <label>Email</label>
                        <input
                            type="email"
                            name="email"
                            value={formData.email}
                            onChange={handleChange}
                            placeholder="customer@example.com"
                        />
                    </div>

                    <div className="form-group">
                        <label>Phone</label>
                        <input
                            type="tel"
                            name="phone"
                            value={formData.phone}
                            onChange={handleChange}
                            placeholder="+91 1234567890"
                        />
                    </div>

                    <div className="form-group">
                        <label>Expiry Date *</label>
                        <input
                            type="date"
                            name="expires_at"
                            value={formData.expires_at}
                            onChange={handleChange}
                            required
                            min={new Date().toISOString().split('T')[0]}
                        />
                    </div>

                    <div className="form-group">
                        <label>Max Activations *</label>
                        <input
                            type="number"
                            name="max_activations"
                            value={formData.max_activations}
                            onChange={handleChange}
                            required
                            min="1"
                            max="10"
                        />
                        <small>Maximum number of devices that can use this license</small>
                    </div>

                    <div className="form-group">
                        <label>Hardware Fingerprint *</label>
                        <input
                            type="text"
                            name="restricted_fingerprint"
                            value={formData.restricted_fingerprint}
                            onChange={handleChange}
                            required
                            placeholder="Paste the machine fingerprint here"
                        />
                        <small>Strictly bound: ONLY this machine will be able to activate this key</small>
                    </div>
                </div>

                <div className="form-group">
                    <label>Notes</label>
                    <textarea
                        name="notes"
                        value={formData.notes}
                        onChange={handleChange}
                        rows="3"
                        placeholder="Additional notes (optional)"
                    />
                </div>

                <button type="submit" className="submit-btn" disabled={loading}>
                    {loading ? 'Generating...' : '🔑 Generate & Bind License'}
                </button>
            </form>
        </div>
    );
}

export default GenerateLicense;
