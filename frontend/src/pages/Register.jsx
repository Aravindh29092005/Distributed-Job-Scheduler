import React, { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { authService } from '../services';

export function Register() {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [name, setName] = useState('');
  const [error, setError] = useState('');
  const navigate = useNavigate();

  const handleRegister = async (e) => {
    e.preventDefault();
    try {
      await authService.register(email, password, name);
      navigate('/login');
    } catch (err) {
      setError('Registration failed.');
    }
  };

  return (
    <div style={{ maxWidth: 400, margin: '100px auto', padding: 20, border: '1px solid #ccc' }}>
      <h2>Register</h2>
      {error && <div style={{ color: 'red' }}>{error}</div>}
      <form onSubmit={handleRegister}>
        <input type="text" placeholder="Full Name" value={name} onChange={e => setName(e.target.value)} style={{ display: 'block', width: '100%', marginBottom: 10 }} />
        <input type="email" placeholder="Email" value={email} onChange={e => setEmail(e.target.value)} required style={{ display: 'block', width: '100%', marginBottom: 10 }} />
        <input type="password" placeholder="Password" value={password} onChange={e => setPassword(e.target.value)} required style={{ display: 'block', width: '100%', marginBottom: 10 }} />
        <button type="submit" style={{ display: 'block', width: '100%' }}>Register</button>
      </form>
      <p>Already have an account? <Link to="/login">Login</Link></p>
    </div>
  );
}
export default Register;
