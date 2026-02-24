import React, { useState } from 'react';
import { useAuth } from '../../contexts/AuthContext';
import { toast } from 'react-toastify';

export function Login() {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [focusedField, setFocusedField] = useState<string | null>(null);
  const { login } = useAuth();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsLoading(true);

    try {
      await login(username, password);
      toast.success('Login successful');
    } catch (error) {
      toast.error(error instanceof Error ? error.message : 'Login failed');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div style={styles.pageWrapper}>
      {/* Decorative background elements */}
      <div style={styles.bgCircle1} />
      <div style={styles.bgCircle2} />

      <div style={styles.card}>
        {/* Header accent bar */}
        <div style={styles.accentBar} />

        {/* Logo / Branding */}
        <div style={styles.brandingSection}>
          <div style={styles.logoIcon}>
            <svg width="40" height="40" viewBox="0 0 40 40" fill="none">
              <rect width="40" height="40" rx="10" fill="#1a365d" />
              <path d="M12 28V14l8-4 8 4v14l-8 4-8-4z" stroke="#63b3ed" strokeWidth="2" fill="none" />
              <path d="M20 10v22M12 14l8 4 8-4M12 28l8-4 8 4" stroke="#63b3ed" strokeWidth="1.5" opacity="0.6" />
            </svg>
          </div>
          <h1 style={styles.title}>ARR Truing-Up DSS</h1>
          <p style={styles.subtitle}>Kerala State Electricity Regulatory Commission</p>
          <p style={styles.tagline}>Enterprise Decision Support System</p>
        </div>

        {/* Form */}
        <form onSubmit={handleSubmit} style={styles.form}>
          <div style={styles.inputGroup}>
            <label style={styles.label}>Email / Username</label>
            <input
              type="text"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              onFocus={() => setFocusedField('username')}
              onBlur={() => setFocusedField(null)}
              placeholder="regulatory.officer@kserc.gov.in"
              style={{
                ...styles.input,
                ...(focusedField === 'username' ? styles.inputFocused : {}),
              }}
              required
            />
          </div>

          <div style={styles.inputGroup}>
            <label style={styles.label}>Password</label>
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              onFocus={() => setFocusedField('password')}
              onBlur={() => setFocusedField(null)}
              placeholder="Enter your password"
              style={{
                ...styles.input,
                ...(focusedField === 'password' ? styles.inputFocused : {}),
              }}
              required
            />
          </div>

          <button
            type="submit"
            disabled={isLoading}
            style={{
              ...styles.button,
              ...(isLoading ? styles.buttonDisabled : {}),
            }}
            onMouseEnter={(e) => {
              if (!isLoading) {
                e.currentTarget.style.background = 'linear-gradient(135deg, #1a365d 0%, #2c5282 100%)';
                e.currentTarget.style.transform = 'translateY(-1px)';
                e.currentTarget.style.boxShadow = '0 6px 20px rgba(26, 54, 93, 0.4)';
              }
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.background = 'linear-gradient(135deg, #2c5282 0%, #2b6cb0 100%)';
              e.currentTarget.style.transform = 'translateY(0)';
              e.currentTarget.style.boxShadow = '0 4px 14px rgba(44, 82, 130, 0.35)';
            }}
          >
            {isLoading ? (
              <span style={styles.loadingText}>
                <span style={styles.spinner} />
                Authenticating...
              </span>
            ) : (
              'Sign In'
            )}
          </button>
        </form>

        {/* Divider */}
        <div style={styles.divider}>
          <span style={styles.dividerLine} />
          <span style={styles.dividerText}>Demo Access</span>
          <span style={styles.dividerLine} />
        </div>

        {/* Credentials hint */}
        <div style={styles.credentialsBox}>
          <p style={styles.credLabel}>Test credentials:</p>
          <p style={styles.credValue}>
            <strong>regulatory.officer@kserc.gov.in</strong>
          </p>
          <p style={styles.credValue}>TempPass123!</p>
        </div>

        {/* Footer */}
        <p style={styles.footer}>
          Powered by KSERC MYT 2022-27 Framework
        </p>
      </div>
    </div>
  );
}

const styles: Record<string, React.CSSProperties> = {
  pageWrapper: {
    minHeight: '100vh',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    background: 'linear-gradient(145deg, #e8f0fe 0%, #f0f4f8 50%, #e2e8f0 100%)',
    fontFamily: "'Roboto', 'Noto Sans Malayalam', sans-serif",
    position: 'relative',
    overflow: 'hidden',
  },
  bgCircle1: {
    position: 'absolute',
    width: '500px',
    height: '500px',
    borderRadius: '50%',
    background: 'radial-gradient(circle, rgba(44, 82, 130, 0.08) 0%, transparent 70%)',
    top: '-150px',
    right: '-100px',
  },
  bgCircle2: {
    position: 'absolute',
    width: '400px',
    height: '400px',
    borderRadius: '50%',
    background: 'radial-gradient(circle, rgba(49, 130, 206, 0.06) 0%, transparent 70%)',
    bottom: '-100px',
    left: '-80px',
  },
  card: {
    width: '100%',
    maxWidth: '420px',
    background: '#ffffff',
    borderRadius: '16px',
    boxShadow: '0 20px 60px rgba(0, 0, 0, 0.08), 0 1px 3px rgba(0, 0, 0, 0.05)',
    position: 'relative' as const,
    overflow: 'hidden',
    zIndex: 1,
    margin: '1rem',
  },
  accentBar: {
    height: '4px',
    background: 'linear-gradient(90deg, #1a365d 0%, #2b6cb0 50%, #63b3ed 100%)',
  },
  brandingSection: {
    textAlign: 'center' as const,
    padding: '2rem 2rem 0.5rem',
  },
  logoIcon: {
    display: 'inline-flex',
    alignItems: 'center',
    justifyContent: 'center',
    marginBottom: '1rem',
  },
  title: {
    fontSize: '1.5rem',
    fontWeight: 700,
    color: '#1a365d',
    margin: '0 0 0.25rem',
    letterSpacing: '-0.02em',
    fontFamily: "'Roboto', sans-serif",
  },
  subtitle: {
    fontSize: '0.8rem',
    color: '#718096',
    margin: '0 0 0.15rem',
    fontWeight: 400,
  },
  tagline: {
    fontSize: '0.75rem',
    color: '#a0aec0',
    margin: 0,
    textTransform: 'uppercase' as const,
    letterSpacing: '0.1em',
    fontWeight: 500,
  },
  form: {
    padding: '1.5rem 2rem',
  },
  inputGroup: {
    marginBottom: '1.25rem',
  },
  label: {
    display: 'block',
    fontSize: '0.8rem',
    fontWeight: 600,
    color: '#4a5568',
    marginBottom: '0.4rem',
    letterSpacing: '0.02em',
  },
  input: {
    width: '100%',
    padding: '0.7rem 0.9rem',
    border: '1.5px solid #e2e8f0',
    borderRadius: '8px',
    fontSize: '0.9rem',
    color: '#2d3748',
    background: '#f7fafc',
    transition: 'all 0.2s ease',
    outline: 'none',
    boxSizing: 'border-box' as const,
    fontFamily: 'inherit',
  },
  inputFocused: {
    borderColor: '#3182ce',
    background: '#ffffff',
    boxShadow: '0 0 0 3px rgba(49, 130, 206, 0.1)',
  },
  button: {
    width: '100%',
    padding: '0.75rem',
    background: 'linear-gradient(135deg, #2c5282 0%, #2b6cb0 100%)',
    color: '#ffffff',
    border: 'none',
    borderRadius: '8px',
    fontSize: '0.95rem',
    fontWeight: 600,
    cursor: 'pointer',
    transition: 'all 0.25s ease',
    boxShadow: '0 4px 14px rgba(44, 82, 130, 0.35)',
    letterSpacing: '0.02em',
    marginTop: '0.5rem',
    fontFamily: 'inherit',
  },
  buttonDisabled: {
    opacity: 0.6,
    cursor: 'not-allowed',
  },
  loadingText: {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    gap: '0.5rem',
  },
  spinner: {
    width: '16px',
    height: '16px',
    border: '2px solid rgba(255,255,255,0.3)',
    borderTopColor: '#ffffff',
    borderRadius: '50%',
    animation: 'spin 0.8s linear infinite',
  },
  divider: {
    display: 'flex',
    alignItems: 'center',
    gap: '0.75rem',
    padding: '0 2rem',
  },
  dividerLine: {
    flex: 1,
    height: '1px',
    background: '#e2e8f0',
  },
  dividerText: {
    fontSize: '0.7rem',
    color: '#a0aec0',
    textTransform: 'uppercase' as const,
    letterSpacing: '0.1em',
    fontWeight: 500,
  },
  credentialsBox: {
    margin: '1rem 2rem',
    padding: '0.75rem 1rem',
    background: '#f7fafc',
    borderRadius: '8px',
    border: '1px solid #edf2f7',
    textAlign: 'center' as const,
  },
  credLabel: {
    fontSize: '0.7rem',
    color: '#a0aec0',
    margin: '0 0 0.3rem',
    textTransform: 'uppercase' as const,
    letterSpacing: '0.05em',
  },
  credValue: {
    fontSize: '0.8rem',
    color: '#4a5568',
    margin: '0.15rem 0',
    fontFamily: "'Roboto Mono', monospace",
  },
  footer: {
    textAlign: 'center' as const,
    fontSize: '0.65rem',
    color: '#cbd5e0',
    padding: '0.75rem 2rem 1.5rem',
    margin: 0,
    letterSpacing: '0.05em',
  },
};
