import { useState, useEffect, type FormEvent } from 'react';
import { useNavigate } from 'react-router-dom';
import axios from 'axios';
import { authService } from '../services';
import { useAuthStore } from '../utils/store';

type Mode = 'login' | 'register';

export function LoginPage() {
  const navigate = useNavigate();
  const { isAuthenticated, setToken, setUser } = useAuthStore();
  const [mode, setMode] = useState<Mode>('login');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [fullName, setFullName] = useState('');
  const [showPw, setShowPw] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');

  useEffect(() => {
    if (isAuthenticated) navigate('/dashboard', { replace: true });
  }, [isAuthenticated, navigate]);

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    if (!email || !password) { setError('Email and password are required.'); return; }
    setLoading(true); setError(''); setSuccess('');

    try {
      // #region agent log
      fetch('http://127.0.0.1:7762/ingest/6218fe6f-01d8-48f8-bdc8-b336105d4c91',{method:'POST',headers:{'Content-Type':'application/json','X-Debug-Session-Id':'afb2d0'},body:JSON.stringify({sessionId:'afb2d0',location:'LoginPage.tsx:handleSubmit:start',message:'Auth submit started',data:{mode,hasEmail:!!email,hasPassword:!!password},timestamp:Date.now(),hypothesisId:'A'})}).catch(()=>{});
      // #endregion
      if (mode === 'login') {
        const res = await authService.login(email, password);
        // #region agent log
        fetch('http://127.0.0.1:7762/ingest/6218fe6f-01d8-48f8-bdc8-b336105d4c91',{method:'POST',headers:{'Content-Type':'application/json','X-Debug-Session-Id':'afb2d0'},body:JSON.stringify({sessionId:'afb2d0',location:'LoginPage.tsx:handleSubmit:loginSuccess',message:'Login API success',data:{status:res.status,hasToken:!!res.data?.access_token},timestamp:Date.now(),hypothesisId:'C'})}).catch(()=>{});
        // #endregion
        setToken(res.data.access_token);
        setUser(res.data.user);
        navigate('/dashboard', { replace: true });
      } else {
        const res = await authService.register(email, password, fullName || undefined);
        // #region agent log
        fetch('http://127.0.0.1:7762/ingest/6218fe6f-01d8-48f8-bdc8-b336105d4c91',{method:'POST',headers:{'Content-Type':'application/json','X-Debug-Session-Id':'afb2d0'},body:JSON.stringify({sessionId:'afb2d0',location:'LoginPage.tsx:handleSubmit:registerSuccess',message:'Register API success',data:{status:res.status,hasToken:!!res.data?.access_token},timestamp:Date.now(),hypothesisId:'C'})}).catch(()=>{});
        // #endregion
        // Auto-login: the register endpoint returns tokens directly
        setToken(res.data.access_token);
        setUser(res.data.user);
        navigate('/dashboard', { replace: true });
      }
    } catch (err) {
      // #region agent log
      fetch('http://127.0.0.1:7762/ingest/6218fe6f-01d8-48f8-bdc8-b336105d4c91',{method:'POST',headers:{'Content-Type':'application/json','X-Debug-Session-Id':'afb2d0'},body:JSON.stringify({sessionId:'afb2d0',location:'LoginPage.tsx:handleSubmit:error',message:'Auth submit failed',data:{isAxios:axios.isAxiosError(err),code:axios.isAxiosError(err)?err.code:null,status:axios.isAxiosError(err)?err.response?.status:null,hasResponse:axios.isAxiosError(err)?!!err.response:false},timestamp:Date.now(),hypothesisId:'A,B,D'})}).catch(()=>{});
      // #endregion
      if (axios.isAxiosError(err)) {
        const msg = err.response?.data?.error?.message
          || err.response?.data?.detail
          || (err.response ? 'Invalid credentials.' : 'Cannot reach server — ensure backend is running on port 8000.');
        setError(msg);
      } else {
        setError(err instanceof Error ? err.message : 'An error occurred.');
      }
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="login-page">
      <div className="login-card">
        <div className="login-brand">
          <div className="login-brand-logo">⚡</div>
          <h1>Codity</h1>
          <p>Distributed Job Scheduling Platform</p>
        </div>

        {/* Mode tabs */}
        <div className="tabs">
          <button
            className={`tab-btn ${mode === 'login' ? 'active' : ''}`}
            onClick={() => { setMode('login'); setError(''); setSuccess(''); }}
          >
            Sign In
          </button>
          <button
            className={`tab-btn ${mode === 'register' ? 'active' : ''}`}
            onClick={() => { setMode('register'); setError(''); setSuccess(''); }}
          >
            Create Account
          </button>
        </div>

        {error && <div className="alert alert-error">{error}</div>}
        {success && <div className="alert alert-success">{success}</div>}

        <form onSubmit={handleSubmit}>
          {mode === 'register' && (
            <div className="form-group">
              <label className="form-label">Full Name</label>
              <input
                className="input"
                type="text"
                value={fullName}
                onChange={e => setFullName(e.target.value)}
                placeholder="Jane Smith"
              />
            </div>
          )}

          <div className="form-group">
            <label className="form-label">Email</label>
            <input
              id="email"
              className="input"
              type="email"
              value={email}
              onChange={e => setEmail(e.target.value)}
              placeholder="you@example.com"
              required
              autoComplete="email"
            />
          </div>

          <div className="form-group">
            <label className="form-label">Password</label>
            <div style={{ position: 'relative' }}>
              <input
                id="password"
                className="input"
                type={showPw ? 'text' : 'password'}
                value={password}
                onChange={e => setPassword(e.target.value)}
                placeholder="••••••••"
                required
                autoComplete={mode === 'login' ? 'current-password' : 'new-password'}
                style={{ paddingRight: '2.5rem' }}
              />
              <button
                type="button"
                onClick={() => setShowPw(!showPw)}
                style={{
                  position: 'absolute', right: '0.75rem', top: '50%',
                  transform: 'translateY(-50%)', background: 'none', border: 'none',
                  cursor: 'pointer', color: 'var(--c-text-muted)', fontSize: '1rem',
                }}
              >
                {showPw ? '🙈' : '👁️'}
              </button>
            </div>
          </div>

          <button
            id="submit-btn"
            type="submit"
            disabled={loading}
            className="btn btn-primary w-full"
            style={{ marginTop: '0.5rem', height: '2.75rem', fontSize: '0.9375rem' }}
          >
            {loading
              ? <span className="spinner" style={{ width: 18, height: 18, borderWidth: 2 }} />
              : mode === 'login' ? 'Sign In' : 'Create Account'}
          </button>
        </form>

        <p style={{
          textAlign: 'center',
          fontSize: '0.75rem',
          color: 'var(--c-text-muted)',
          marginTop: '1.5rem',
        }}>
          Production-grade Job Scheduling Platform · v1.0.0
        </p>
      </div>
    </div>
  );
}
