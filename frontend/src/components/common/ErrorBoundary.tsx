import React, { Component, ReactNode, ErrorInfo } from 'react';

interface Props {
    children: ReactNode;
    fallback?: ReactNode;
}

interface State {
    hasError: boolean;
    error: Error | null;
    errorInfo: ErrorInfo | null;
}

/**
 * F-10: Global ErrorBoundary to prevent white-screen crashes.
 * Catches React render errors and shows a recovery UI instead
 * of killing the entire app.
 */
export class ErrorBoundary extends Component<Props, State> {
    constructor(props: Props) {
        super(props);
        this.state = { hasError: false, error: null, errorInfo: null };
    }

    static getDerivedStateFromError(error: Error): Partial<State> {
        return { hasError: true, error };
    }

    componentDidCatch(error: Error, errorInfo: ErrorInfo) {
        this.setState({ errorInfo });
        // In production: send to Sentry/LogRocket
        console.error('[ErrorBoundary] Caught render error:', error, errorInfo);
    }

    handleReset = () => {
        this.setState({ hasError: false, error: null, errorInfo: null });
    };

    render() {
        if (this.state.hasError) {
            if (this.props.fallback) {
                return this.props.fallback;
            }

            return (
                <div style={s.container}>
                    <div style={s.card}>
                        <div style={s.icon}>⚠️</div>
                        <h2 style={s.title}>
                            Something went wrong
                        </h2>
                        <p style={s.subtitle}>
                            An unexpected system error occurred. Your data is safe—please try refreshing the application.
                        </p>
                        {this.state.error && (
                            <details style={s.details}>
                                <summary style={s.summary}>
                                    Technical details
                                </summary>
                                <pre style={s.pre}>
                                    {this.state.error.toString()}
                                    {this.state.errorInfo?.componentStack}
                                </pre>
                            </details>
                        )}
                        <div style={s.buttonGroup}>
                            <button
                                onClick={this.handleReset}
                                style={s.primaryButton}
                                onMouseOver={(e) => e.currentTarget.style.backgroundColor = '#2c5282'}
                                onMouseOut={(e) => e.currentTarget.style.backgroundColor = '#3182ce'}
                            >
                                Try Again
                            </button>
                            <button
                                onClick={() => window.location.reload()}
                                style={s.secondaryButton}
                                onMouseOver={(e) => e.currentTarget.style.backgroundColor = '#e2e8f0'}
                                onMouseOut={(e) => e.currentTarget.style.backgroundColor = '#edf2f7'}
                            >
                                Refresh Page
                            </button>
                        </div>
                    </div>
                </div>
            );
        }

        return this.props.children;
    }
}

const s: Record<string, React.CSSProperties> = {
    container: { minHeight: '100vh', display: 'flex', alignItems: 'center', justifyContent: 'center', backgroundColor: '#f7fafc', padding: '2rem' },
    card: { width: '100%', maxWidth: '450px', backgroundColor: '#ffffff', borderRadius: '8px', boxShadow: '0 10px 25px -5px rgba(0,0,0,0.1), 0 8px 10px -6px rgba(0,0,0,0.1)', padding: '2rem', textAlign: 'center' as const, borderTop: '4px solid #e53e3e' },
    icon: { fontSize: '3rem', marginBottom: '1rem' },
    title: { fontSize: '1.5rem', fontWeight: 700, color: '#2d3748', margin: '0 0 0.5rem 0' },
    subtitle: { color: '#718096', marginBottom: '1.5rem', fontSize: '0.95rem', lineHeight: 1.5 },
    details: { textAlign: 'left' as const, fontSize: '0.875rem', color: '#a0aec0', marginBottom: '1.5rem', border: '1px solid #edf2f7', borderRadius: '4px', padding: '0.5rem' },
    summary: { cursor: 'pointer', color: '#3182ce', fontWeight: 500, outline: 'none' },
    pre: { marginTop: '0.5rem', padding: '0.5rem', backgroundColor: '#f1f5f9', borderRadius: '4px', overflow: 'auto', fontSize: '0.75rem', color: '#4a5568', whiteSpace: 'pre-wrap' },
    buttonGroup: { display: 'flex', gap: '1rem', justifyContent: 'center' },
    primaryButton: { padding: '0.5rem 1.5rem', backgroundColor: '#3182ce', color: '#ffffff', border: 'none', borderRadius: '4px', fontWeight: 600, cursor: 'pointer', transition: 'background-color 0.2s' },
    secondaryButton: { padding: '0.5rem 1.5rem', backgroundColor: '#edf2f7', color: '#4a5568', border: 'none', borderRadius: '4px', fontWeight: 600, cursor: 'pointer', transition: 'background-color 0.2s' }
};
