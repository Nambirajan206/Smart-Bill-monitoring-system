import React from 'react';

const BillTable = ({ bills }) => {
    return (
        <div className="card" style={{ padding: 0, overflowX: 'auto' }}>
            <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left' }}>
                <thead style={{ backgroundColor: '#f1f5f9' }}>
                    <tr>
                        <th style={thStyle}>House ID</th>
                        <th style={thStyle}>Owner Name</th>
                        <th style={thStyle}>Month</th>
                        <th style={thStyle}>Units</th>
                        <th style={thStyle}>Amount</th>
                    </tr>
                </thead>
                <tbody>
                    {bills.map((bill, index) => (
                        <tr key={index} style={{ borderBottom: '1px solid #e2e8f0' }}>
                            <td style={tdStyle}>{bill.House_ID}</td>
                            <td style={tdStyle}>{bill.Owner_Name}</td>
                            <td style={tdStyle}>{bill.Month}</td>
                            <td style={tdStyle}>{bill.Units_Consumed}</td>
                            <td style={{ ...tdStyle, color: '#dc2626', fontWeight: 'bold' }}>₹{bill.Bill_Amount}</td>
                        </tr>
                    ))}
                </tbody>
            </table>
        </div>
    );
};

const thStyle = { padding: '12px', fontSize: '0.85rem', color: '#475569' };
const tdStyle = { padding: '12px', fontSize: '0.9rem' };

export default BillTable;