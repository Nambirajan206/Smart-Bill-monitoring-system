import React from 'react';

const SyncControl = ({ onSync, syncing }) => {
    return (
        <button 
            onClick={onSync} 
            disabled={syncing}
            style={{
                backgroundColor: syncing ? '#94a3b8' : '#2563eb',
                color: 'white',
                padding: '10px 20px',
                border: 'none',
                borderRadius: '6px',
                cursor: syncing ? 'not-allowed' : 'pointer',
                fontWeight: 'bold'
            }}
        >
            {syncing ? '⌛ Syncing Folder...' : '🔄 Sync GDrive Files'}
        </button>
    );
};

export default SyncControl;