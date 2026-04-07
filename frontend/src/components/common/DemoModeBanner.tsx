/**
 * Demo Mode Banner Component
 * 
 * Displays a prominent banner when the application is running in Demo Mode.
 * Shows "Demo Mode Enabled — Outputs are simulated" message.
 */

import React from 'react';
import { IS_DEMO_MODE } from '../../services/config';

/**
 * Demo Mode Banner - Top banner indicating demo mode status
 */
const DemoModeBanner: React.FC = () => {
  if (!IS_DEMO_MODE) {
    return null;
  }

  return (
    <>
      <div className="demo-mode-banner">
        <div className="demo-banner-content">
          <span className="demo-icon">🎮</span>
          <span className="demo-text">
            <strong>Demo Mode Enabled</strong> — Outputs are simulated for demonstration purposes only
          </span>
          <span className="demo-badge">NOT FOR REGULATORY USE</span>
        </div>
      </div>
      <style>{`
        .demo-mode-banner {
          background: linear-gradient(90deg, #ff6b6b 0%, #feca57 100%);
          color: white;
          padding: 12px 20px;
          text-align: center;
          font-size: 14px;
          font-weight: 500;
          box-shadow: 0 2px 4px rgba(0,0,0,0.1);
          position: sticky;
          top: 0;
          z-index: 1000;
        }

        .demo-banner-content {
          display: flex;
          align-items: center;
          justify-content: center;
          gap: 12px;
          flex-wrap: wrap;
          max-width: 1200px;
          margin: 0 auto;
        }

        .demo-icon {
          font-size: 20px;
        }

        .demo-text {
          color: white;
        }

        .demo-badge {
          background: rgba(255, 255, 255, 0.2);
          padding: 4px 10px;
          border-radius: 12px;
          font-size: 11px;
          font-weight: 600;
          text-transform: uppercase;
          letter-spacing: 0.5px;
        }
      `}</style>
    </>
  );
};

export default DemoModeBanner;
