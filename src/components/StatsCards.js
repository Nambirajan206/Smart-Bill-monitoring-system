import React from 'react';

const StatsCards = ({ stats }) => {
    if (!stats) return null;

    const items = [
        { label: 'Total High Bills', value: stats.total_records, color: '#dc2626' },
        { label: 'Avg Bill Amount', value: `₹${stats.overall?.average_bill_amount.toFixed(2)}`, color: '#2563eb' },
        { label: 'Total Units', value: stats.overall?.total_units_consumed, color: '#16a34a' },
        { label: 'Max Bill Found', value: `₹${stats.overall?.max_bill_amount}`, color: '#ea580c' }
    ];

    return (
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '1rem', marginBottom: '2rem' }}>
            {items.map((item, i) => (
                <div key={i} className="card" style={{ borderLeft: `5px solid ${item.color}` }}>
                    <p style={{ fontSize: '0.8rem', color: '#64748b', margin: '0 0 0.5rem 0' }}>{item.label}</p>
                    <h3 style={{ margin: 0, fontSize: '1.5rem' }}>{item.value}</h3>
                </div>
            ))}
        </div>
    );
};

export default StatsCards;