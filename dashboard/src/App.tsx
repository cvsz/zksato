import { useState, useEffect } from 'react';
import { ShieldAlert, Check, X, Activity } from 'lucide-react';
import './index.css';

interface RiskApproval {
  id: string;
  symbol: string;
  action: 'BUY' | 'SELL';
  quantity: number;
  notionalValue: number;
  riskReason: string;
  status: 'PENDING' | 'APPROVED' | 'REJECTED';
}

function App() {
  const [approvals, setApprovals] = useState<RiskApproval[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    // Simulate fetching pending risk approvals
    setTimeout(() => {
      setApprovals([
        {
          id: 'req_8f72h',
          symbol: 'S50Z26',
          action: 'BUY',
          quantity: 10,
          notionalValue: 2000000,
          riskReason: 'Live equity mutation requires operator authorization (P11)',
          status: 'PENDING'
        }
      ]);
      setLoading(false);
    }, 1000);
  }, []);

  const handleAction = (id: string, action: 'APPROVED' | 'REJECTED') => {
    setApprovals(prev => 
      prev.map(app => app.id === id ? { ...app, status: action } : app)
    );
  };

  const pendingApprovals = approvals.filter(a => a.status === 'PENDING');

  return (
    <div className="layout-container">
      <header className="header">
        <h1 className="header-title">Operator Control Center</h1>
        <p className="header-subtitle">Secure live-money execution and deterministic risk monitoring</p>
      </header>

      <main className="main-content">
        <section className="section">
          <h2 className="section-title">Portfolio Risk Overview</h2>
          <div className="surface metrics-grid">
            <div className="metric-item">
              <span className="metric-label">Total Exposure</span>
              <span className="metric-value">฿1,450,000</span>
            </div>
            <div className="metric-item">
              <span className="metric-label">Margin Utilization</span>
              <span className="metric-value">42.5%</span>
            </div>
            <div className="metric-item">
              <span className="metric-label">Daily Drawdown</span>
              <span className="metric-value success">-1.2%</span>
            </div>
            <div className="metric-item">
              <span className="metric-label">System Status</span>
              <span className="metric-value" style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <Activity size={20} color="var(--success-color)" /> Active
              </span>
            </div>
          </div>
        </section>

        <section className="section">
          <h2 className="section-title">Action Required</h2>
          
          {loading ? (
            <div className="empty-state">Syncing security context...</div>
          ) : pendingApprovals.length === 0 ? (
            <div className="empty-state">No pending operator approvals required.</div>
          ) : (
            pendingApprovals.map(approval => (
              <div key={approval.id} className="approval-flow">
                <div className="approval-details">
                  <h3 className="approval-title" style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                    <ShieldAlert size={18} color="var(--danger-color)" />
                    Manual Risk Approval Required
                  </h3>
                  <p className="approval-description">
                    The deterministic risk engine halted an autonomous live-money execution attempt. Explicit operator authorization is required to proceed.
                  </p>
                  
                  <div className="approval-meta">
                    <div><strong>ID:</strong> {approval.id}</div>
                    <div><strong>Intent:</strong> {approval.action} {approval.quantity} {approval.symbol}</div>
                    <div><strong>Notional:</strong> ฿{approval.notionalValue.toLocaleString()}</div>
                    <div><strong>Reason:</strong> {approval.riskReason}</div>
                  </div>
                </div>

                <div className="approval-actions">
                  <button 
                    className="btn btn-primary"
                    onClick={() => handleAction(approval.id, 'APPROVED')}
                  >
                    <Check size={16} /> Authorize Execution
                  </button>
                  <button 
                    className="btn btn-danger"
                    onClick={() => handleAction(approval.id, 'REJECTED')}
                  >
                    <X size={16} /> Reject Intent
                  </button>
                </div>
              </div>
            ))
          )}
        </section>
      </main>
    </div>
  );
}

export default App;
