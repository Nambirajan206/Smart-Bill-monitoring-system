import React, { useState, useEffect } from 'react';
import { fetchBills, fetchStats, triggerSync, clearAllData } from '../api';
import StatsCards from './StatsCards';
import BillTable from './BillTable';
import SyncControl from './SyncControl';
import FilterBar from './FilterBar';

const Dashboard = () => {
    const [bills, setBills] = useState([]);
    const [stats, setStats] = useState(null);
    const [searchTerm, setSearchTerm] = useState('');
    const [loading, setLoading] = useState(false);
    const [syncing, setSyncing] = useState(false);
    const [hasSynced, setHasSynced] = useState(false);

    const loadData = async () => {
        setLoading(true);
        try {
            const [billRes, statRes] = await Promise.all([fetchBills(), fetchStats()]);
            setBills(billRes.data.data || []); 
            setStats(statRes.data);
            setHasSynced(true);
        } catch (err) { 
            console.error("Fetch error:", err); 
        } finally { 
            setLoading(false); 
        }
    };

    const handleSync = async () => {
        setSyncing(true);
        try {
            await triggerSync();
            await loadData();
        } catch (err) { 
            alert("Sync failed. Check backend."); 
        } finally { 
            setSyncing(false); 
        }
    };

    const handleClear = async () => {
        if (window.confirm("Are you sure you want to clear all data?")) {
            try {
                await clearAllData();
                setBills([]);
                setStats(null);
                setHasSynced(false);
            } catch (err) {
                alert("Clear failed");
            }
        }
    };

    // FIX: Define filteredBills so ESLint doesn't complain
    const filteredBills = bills.filter(b => 
        b.House_ID.toLowerCase().includes(searchTerm.toLowerCase()) ||
        b.Owner_Name.toLowerCase().includes(searchTerm.toLowerCase())
    );

    return (
        <div className="container">
            <header style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '2rem' }}>
                <div>
                    <h1 style={{ margin: 0 }}>Electricity Dashboard</h1>
                    <p style={{ color: '#64748b' }}>Monitoring Abnormal Bills ( > ₹5000 )</p>
                </div>
                <div style={{ display: 'flex', gap: '10px', alignItems: 'center' }}>
                    {hasSynced && <FilterBar onSearch={setSearchTerm} />}
                    <SyncControl onSync={handleSync} syncing={syncing} />
                    {hasSynced && (
                        <button onClick={handleClear} style={{ backgroundColor: '#dc2626', color: 'white', border: 'none', padding: '10px', borderRadius: '6px', cursor: 'pointer' }}>
                            Clear Data
                        </button>
                    )}
                </div>
            </header>

            {hasSynced ? (
                <>
                    <StatsCards stats={stats} />
                    {loading ? <p>Loading...</p> : <BillTable bills={filteredBills} />}
                </>
            ) : (
                <div style={{ textAlign: 'center', padding: '50px', border: '2px dashed #ccc', borderRadius: '10px' }}>
                    <h2>Welcome</h2>
                    <p>Click "Sync GDrive Files" to fetch and display high-bill records.</p>
                </div>
            )}
        </div>
    );
};

export default Dashboard;