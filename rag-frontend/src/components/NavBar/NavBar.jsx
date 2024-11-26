import React from 'react';
import { NavLink } from 'react-router-dom';

const NavBar = () => {
    return (
        <nav style={{ padding: '10px', backgroundColor: '#333', color: 'white', display: 'flex', gap: '10px' }}>
            <NavLink to="/" style={({ isActive }) => ({ color: isActive ? 'yellow' : 'white' })}>
                Home
            </NavLink>
            <NavLink to="/upload" style={({ isActive }) => ({ color: isActive ? 'yellow' : 'white' })}>
                Upload
            </NavLink>
            <NavLink to="/files" style={({ isActive }) => ({ color: isActive ? 'yellow' : 'white' })}>
                Files
            </NavLink>
        </nav>
    );
};

export default NavBar;
