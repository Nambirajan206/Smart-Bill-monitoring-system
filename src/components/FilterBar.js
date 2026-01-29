import React from 'react';

const FilterBar = ({ onSearch }) => {
    return (
        <input 
            type="text" 
            placeholder="Search by House ID or Owner..." 
            onChange={(e) => onSearch(e.target.value)}
            style={{
                width: '300px',
                padding: '10px',
                borderRadius: '6px',
                border: '1px solid #cbd5e1',
                outline: 'none'
            }}
        />
    );
};

export default FilterBar;