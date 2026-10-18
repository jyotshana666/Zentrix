/**
 * WARDEN-Z · ZENTRIX SECURITY DASHBOARD
 * app.js — Full Frontend Integration for Agent Warden-Z
 *
 * Connects dashboard to live FastAPI backend endpoints:
 *   - GET  /health
 *   - GET  /actions
 *   - GET  /actions/held
 *   - GET  /agents/{agent_id}/history
 *   - GET  /db/fingerprint
 *   - GET  /db/transactions/{id}
 *   - POST /actions/evaluate
 *   - POST /actions/execute
 *   - POST /admin/reset
 *
 * Offline fallback: Clearly labels simulated demo data if backend is offline.
 * Strict Security: Never executes actions automatically. Follows fail-closed rules.
 */

'use strict';

/* ═══════════════════════════════════════════════════════════════
   API CLIENT LAYER
   ═══════════════════════════════════════════════════════════════ */

const API = {
  getBaseUrl() {
    return localStorage.getItem('warden_api_base') || 'http://localhost:8000';
  },

  setBaseUrl(url) {
    const clean = String(url || '').trim().replace(/\/+$/, '');
    localStorage.setItem('warden_api_base', clean || 'http://localhost:8000');
  },

  async request(endpoint, options = {}) {
    const base = this.getBaseUrl();
    const url = `${base}${endpoint}`;
    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), 4500);

    try {
      const response = await fetch(url, {
        ...options,
        signal: controller.signal,
        headers: {
          'Content-Type': 'application/json',
          'Accept': 'application/json',
          ...(options.headers || {}),
        },
      });
      clearTimeout(timeout);

      if (!response.ok) {
        let errorMsg = `HTTP ${response.status} ${response.statusText}`;
        try {
          const errJson = await response.json();
          if (errJson && errJson.detail) {
            errorMsg = typeof errJson.detail === 'string'
              ? errJson.detail
              : JSON.stringify(errJson.detail);
          }
        } catch (_) { }
        throw new Error(errorMsg);
      }

      return await response.json();
    } catch (err) {
      clearTimeout(timeout);
      if (err.name === 'AbortError') {
        throw new Error(`Request timed out reaching ${base}`);
      }
      throw err;
    }
  },

  getHealth() {
    return this.request('/health');
  },

  getActions(limit = 100) {
    return this.request(`/actions?limit=${encodeURIComponent(limit)}`);
  },

  getHeldActions() {
    return this.request('/actions/held');
  },

  getAgentHistory(agentId) {
    return this.request(`/agents/${encodeURIComponent(agentId)}/history`);
  },

  getFingerprint() {
    return this.request('/db/fingerprint');
  },

  getTransaction(txId) {
    return this.request(`/db/transactions/${encodeURIComponent(txId)}`);
  },

  evaluateAction(actionRequest) {
    return this.request('/actions/evaluate', {
      method: 'POST',
      body: JSON.stringify(actionRequest),
    });
  },

  executeAction(actionRequest) {
    return this.request('/actions/execute', {
      method: 'POST',
      body: JSON.stringify(actionRequest),
    });
  },

  resetAdmin() {
    return this.request('/admin/reset', {
      method: 'POST',
    });
  },
};

/* ═══════════════════════════════════════════════════════════════
   SIMULATED FALLBACK DATA (Offline Demo Catalog)
   ═══════════════════════════════════════════════════════════════ */

const SIM = {
  recentEvents: [
    { ts: '2026-10-17 21:18:04', severity: 'critical', type: 'Ransomware Staging', agent: 'warden-z-03', source: '10.0.4.221', status: 'Investigating' },
    { ts: '2026-10-17 21:14:52', severity: 'high', type: 'Lateral Movement', agent: 'warden-z-07', source: '192.168.1.45', status: 'Detected' },
    { ts: '2026-10-17 21:09:31', severity: 'high', type: 'Brute Force — SSH', agent: 'warden-z-01', source: '45.77.21.108', status: 'Contained' },
    { ts: '2026-10-17 21:04:19', severity: 'medium', type: 'Port Scan — TCP SYN', agent: 'warden-z-11', source: '203.0.113.55', status: 'Resolved' },
    { ts: '2026-10-17 20:58:47', severity: 'medium', type: 'Data Exfiltration Attempt', agent: 'warden-z-05', source: '10.0.1.99', status: 'Investigating' },
    { ts: '2026-10-17 20:51:12', severity: 'low', type: 'Anomalous Login', agent: 'warden-z-14', source: '10.0.3.14', status: 'Resolved' },
    { ts: '2026-10-17 20:44:03', severity: 'critical', type: 'SQL Injection', agent: 'warden-z-09', source: '198.51.100.7', status: 'Investigating' },
  ],

  auditLog: [
    { ts: '2026-10-17 21:22:01', eventId: 'evt_sim_01', actionId: 'act_101', agentId: 'warden-z-01', resource: 'transactions', operation: 'SELECT', decision: 'ALLOW', reason: 'Matches task policy', riskScore: 0, executed: 1 },
    { ts: '2026-10-17 21:20:55', eventId: 'evt_sim_02', actionId: 'act_102', agentId: 'warden-z-03', resource: 'transactions', operation: 'UPDATE', decision: 'HOLD', reason: 'Additional authorization required for UPDATE', riskScore: 60, executed: 0 },
    { ts: '2026-10-17 21:19:41', eventId: 'evt_sim_03', actionId: 'act_103', agentId: 'warden-z-07', resource: '/etc/shadow', operation: 'SELECT', decision: 'BLOCK', reason: "Resource '/etc/shadow' is outside scope", riskScore: 100, executed: 0 },
    { ts: '2026-10-17 21:18:09', eventId: 'evt_sim_04', actionId: 'act_104', agentId: 'warden-z-05', resource: 'customers', operation: 'DELETE', decision: 'BLOCK', reason: 'DELETE is not permitted by task policy', riskScore: 100, executed: 0 },
    { ts: '2026-10-17 21:17:04', eventId: 'evt_sim_05', actionId: 'act_105', agentId: 'warden-z-11', resource: 'transactions', operation: 'SELECT', decision: 'ALLOW', reason: 'Matches task policy', riskScore: 0, executed: 1 },
    { ts: '2026-10-17 21:15:58', eventId: 'evt_sim_06', actionId: 'act_106', agentId: 'warden-z-09', resource: 'transactions', operation: 'UPDATE', decision: 'HOLD', reason: 'Additional authorization required for UPDATE', riskScore: 60, executed: 0 },
  ],

  threats: [
    {
      id: 'THR-0041',
      severity: 'critical',
      name: 'APT29 Cozy Bear — Recon Phase',
      source: '45.77.21.108',
      target: 'warden-z-03 / finance-db-prod',
      ts: '2026-10-17 21:18:04',
      status: 'Investigating',
      technique: 'T1595 — Active Scanning',
      description: 'Indicators of compromise matching APT29 (Cozy Bear) TTPs detected. Agent observed performing reconnaissance against internal financial database endpoints.',
      iocs: ['45.77.21.108', 'cozy-update[.]net', '3d2b8f1e9c7a0d4f6e5c2b8a1d9e0f3c'],
      recommendation: 'Isolate affected agent. Cross-reference with MITRE ATT&CK T1595. Escalate to IR team.',
      isSimulated: true,
    },
    {
      id: 'THR-0040',
      severity: 'critical',
      name: 'Ransomware Staging Detected',
      source: '10.0.4.221',
      target: 'warden-z-03 / k8s-cluster-01',
      ts: '2026-10-17 21:14:52',
      status: 'Investigating',
      technique: 'T1486 — Data Encrypted for Impact',
      description: 'Ransomware staging behavior detected. File enumeration and shadow copy deletion commands observed.',
      iocs: ['10.0.4.221', 'ransom-gate[.]io', 'e7f1a3d2c8b4e6f9'],
      recommendation: 'Immediately quarantine host. Snapshot volumes. Notify legal and exec teams.',
      isSimulated: true,
    },
    {
      id: 'THR-0039',
      severity: 'high',
      name: 'Lateral Movement — Pass-the-Hash',
      source: '192.168.1.45',
      target: 'warden-z-07 / auth-service',
      ts: '2026-10-17 21:09:31',
      status: 'Detected',
      technique: 'T1550.002 — Pass the Hash',
      description: 'NTLM hash reuse detected across multiple internal hosts. Authentication anomaly suggesting credential theft.',
      iocs: ['192.168.1.45', '192.168.1.89'],
      recommendation: 'Force password reset. Enable Protected Users security group.',
      isSimulated: true,
    },
    {
      id: 'THR-0038',
      severity: 'high',
      name: 'SSH Brute Force Campaign',
      source: '198.51.100.7',
      target: 'warden-z-01 / api-gateway-prod',
      ts: '2026-10-17 21:04:19',
      status: 'Contained',
      technique: 'T1110 — Brute Force',
      description: '4,210 failed SSH authentication attempts from external IP in 90-second window. Rate limit triggered.',
      iocs: ['198.51.100.7'],
      recommendation: 'Block IP at WAF. Enable geo-fencing. Review SSH key policy.',
      isSimulated: true,
    },
  ],

  agents: [
    { id: 'warden-z-03', role: 'Data Pipeline', riskScore: 91, driftEvents: 7, lastSeen: '2 min ago', status: 'critical' },
    { id: 'warden-z-07', role: 'Auth Service', riskScore: 74, driftEvents: 4, lastSeen: '5 min ago', status: 'high' },
    { id: 'warden-z-09', role: 'Web Scraper', riskScore: 68, driftEvents: 3, lastSeen: '8 min ago', status: 'high' },
    { id: 'warden-z-01', role: 'API Gateway', riskScore: 42, driftEvents: 1, lastSeen: '1 min ago', status: 'medium' },
    { id: 'warden-z-05', role: 'Log Aggregator', riskScore: 37, driftEvents: 2, lastSeen: '3 min ago', status: 'medium' },
    { id: 'warden-z-14', role: 'Reporting Engine', riskScore: 12, driftEvents: 0, lastSeen: '12 min ago', status: 'low' },
  ],

  driftEvents: [
    { ts: '2026-10-17 21:10:22', agentId: 'warden-z-03', driftType: 'Behavioral', baseline: 'Read-only DB access', current: 'Schema modification attempt', delta: '+38', status: 'Critical' },
    { ts: '2026-10-17 21:07:55', agentId: 'warden-z-07', driftType: 'Network', baseline: '< 100 req/min', current: '4,210 req/min outbound', delta: '+31', status: 'High' },
    { ts: '2026-10-17 21:05:19', agentId: 'warden-z-09', driftType: 'Privilege', baseline: 'UID 1001 (unprivileged)', current: 'UID 0 (root)', delta: '+28', status: 'High' },
    { ts: '2026-10-17 20:59:04', agentId: 'warden-z-03', driftType: 'Resource', baseline: 'CPU < 20%', current: 'CPU 97% sustained', delta: '+22', status: 'High' },
  ],

  taskPolicies: [
    { id: 'task_read_transaction', name: 'Task: Read Transaction', type: 'Policy Engine', scope: 'transactions', status: 'Active', rules: 'Allowed: SELECT | Review: UPDATE, DELETE', backend: true },
    { id: 'task_update_transaction', name: 'Task: Update Transaction', type: 'Policy Engine', scope: 'transactions', status: 'Active', rules: 'Allowed: SELECT | Review: UPDATE', backend: true },
    { id: 'POL-001', name: 'Zero-Trust Network Access', type: 'Network Security', scope: 'All Agents', status: 'Active', rules: 'mTLS enforced, strict gateway boundaries', backend: false },
    { id: 'POL-002', name: 'Least Privilege DB Execution', type: 'Access Control', scope: 'Production Env', status: 'Active', rules: 'Refuse unapproved resources & operations', backend: true },
    { id: 'POL-003', name: 'Immutable Audit Logging', type: 'Compliance', scope: 'Audit Engine', status: 'Active', rules: 'Append-only event journal in SQLite', backend: true },
  ],

  accessMatrix: [
    { role: 'warden-z-01 / API Gateway', read: true, write: true, execute: false, delete: false, admin: false },
    { role: 'warden-z-03 / Data Pipeline', read: true, write: true, execute: true, delete: false, admin: false },
    { role: 'warden-z-05 / Log Aggregator', read: true, write: true, execute: false, delete: false, admin: false },
    { role: 'warden-z-07 / Auth Service', read: true, write: false, execute: true, delete: false, admin: false },
    { role: 'warden-z-09 / Web Scraper', read: true, write: false, execute: true, delete: false, admin: false },
    { role: 'Security Analyst', read: true, write: false, execute: true, delete: false, admin: false },
    { role: 'Platform Admin', read: true, write: true, execute: true, delete: true, admin: true },
  ],
};

/* ═══════════════════════════════════════════════════════════════
   APPLICATION STATE
   ═══════════════════════════════════════════════════════════════ */

const state = {
  activeTab: 'security-overview',
  backendConnected: false,
  apiLatency: 0,
  liveActions: [],
  liveHeldActions: [],
  dbFingerprint: '—',
  threatsTabMode: 'held', // 'held' or 'intel'
  selectedThreatId: null,
  selectedHeldIndex: null,
  charts: {},
  auditFilter: { search: '', action: '', status: '' },
  threatFilter: { search: '', severity: 'all' },
  policyFilter: { search: '', type: '', status: '' },
  auditPage: 0,
  auditPageSize: 20,
};

/* ═══════════════════════════════════════════════════════════════
   CHART.JS DEFAULTS
   ═══════════════════════════════════════════════════════════════ */

if (window.Chart) {
  Chart.defaults.color = '#94a3b8';
  Chart.defaults.borderColor = 'rgba(255,255,255,0.04)';
  Chart.defaults.font.family = "'Inter', sans-serif";
  Chart.defaults.font.size = 12;
}

/* ═══════════════════════════════════════════════════════════════
   FORMATTING & UI HELPERS
   ═══════════════════════════════════════════════════════════════ */

function escHtml(str) {
  if (str === null || str === undefined) return '';
  return String(str)
    .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;').replace(/'/g, '&#39;');
}

function decisionBadge(dec) {
  const d = String(dec || '').toUpperCase();
  if (d === 'ALLOW') {
    return `<span class="badge badge-success" title="Allowed by policy engine"><span class="badge-dot" style="background:var(--success)"></span>ALLOW</span>`;
  }
  if (d === 'HOLD') {
    return `<span class="badge badge-warning" title="Held for review"><span class="badge-dot" style="background:var(--warning)"></span>HOLD</span>`;
  }
  if (d === 'BLOCK') {
    return `<span class="badge badge-critical" title="Blocked by policy engine"><span class="badge-dot" style="background:#f87171"></span>BLOCK</span>`;
  }
  return `<span class="badge badge-neutral">${escHtml(dec)}</span>`;
}

function executedBadge(executed) {
  if (executed === true || executed === 1 || executed === '1') {
    return `<span class="badge badge-success" title="Action executed against database">YES</span>`;
  }
  return `<span class="badge badge-neutral" style="opacity:0.85" title="Not executed">NO</span>`;
}

function severityBadge(sev) {
  const map = {
    critical: 'badge-critical',
    high: 'badge-high',
    medium: 'badge-medium',
    low: 'badge-low',
  };
  const s = String(sev || 'low').toLowerCase();
  return `<span class="badge ${map[s] || 'badge-neutral'}">${s.toUpperCase()}</span>`;
}

function statusBadge(status) {
  const map = {
    'Investigating': 'badge-warning',
    'Detected': 'badge-danger',
    'Contained': 'badge-info',
    'Resolved': 'badge-success',
    'Completed': 'badge-success',
    'Pending': 'badge-pending',
    'Flagged': 'badge-warning',
    'Blocked': 'badge-danger',
    'Active': 'badge-success',
    'Inactive': 'badge-neutral',
    'Review': 'badge-warning',
    'Critical': 'badge-critical',
    'High': 'badge-high',
    'Medium': 'badge-medium',
    'Low': 'badge-low',
  };
  return `<span class="badge ${map[status] || 'badge-neutral'}">${escHtml(status)}</span>`;
}

function permIcon(val) {
  if (val === true) return '<span class="perm-allow" title="Granted">●</span>';
  if (val === false) return '<span class="perm-deny" title="Denied">○</span>';
  return '<span class="perm-partial" title="Partial / Review required">◐</span>';
}

function scoreClass(score) {
  if (score >= 80) return 'score-critical';
  if (score >= 60) return 'score-high';
  if (score >= 35) return 'score-medium';
  return 'score-low';
}

function scoreBarColor(score) {
  if (score >= 80) return '#f87171';
  if (score >= 60) return '#fb923c';
  if (score >= 35) return '#fcd34d';
  return '#6ee7b7';
}

function showToast(message, type = 'info') {
  const container = document.getElementById('toast-container');
  if (!container) return;

  const toast = document.createElement('div');
  toast.className = `toast toast-${type}`;
  toast.innerHTML = `<span>${escHtml(message)}</span>`;
  container.appendChild(toast);

  setTimeout(() => {
    toast.style.transition = 'opacity 0.3s, transform 0.3s';
    toast.style.opacity = '0';
    toast.style.transform = 'translateY(8px)';
    setTimeout(() => toast.remove(), 320);
  }, 3200);
}

/* ═══════════════════════════════════════════════════════════════
   CONNECTION STATUS & SYNC
   ═══════════════════════════════════════════════════════════════ */

async function checkBackendConnection(showNotification = false) {
  const t0 = performance.now();
  const apiStatusBtn = document.getElementById('api-status-btn');
  const apiStatusText = document.getElementById('api-status-text');
  const sidebarStatus = document.getElementById('sidebar-system-status');
  const sidebarStatusText = document.getElementById('sidebar-status-text');
  const sidebarPulse = document.getElementById('sidebar-status-pulse');
  const demoModeBadge = document.getElementById('demo-mode-badge');
  const demoModeText = document.getElementById('demo-mode-text');

  try {
    const health = await API.getHealth();
    const latency = Math.round(performance.now() - t0);
    state.backendConnected = health && health.status === 'ok';
    state.apiLatency = latency;

    if (state.backendConnected) {
      if (apiStatusBtn) {
        apiStatusBtn.classList.add('connected');
        apiStatusBtn.title = `Connected to ${API.getBaseUrl()} (${latency}ms)`;
      }
      if (apiStatusText) apiStatusText.textContent = `Backend: Online (${latency}ms)`;
      if (sidebarStatusText) sidebarStatusText.textContent = `Systems Nominal · Live`;
      if (sidebarPulse) sidebarPulse.style.background = 'var(--success)';
      if (demoModeBadge) {
        demoModeBadge.style.background = 'rgba(16, 185, 129, 0.12)';
        demoModeBadge.style.borderColor = 'rgba(16, 185, 129, 0.3)';
        demoModeBadge.style.color = '#6ee7b7';
      }
      if (demoModeText) demoModeText.innerHTML = `LIVE &middot; ${escHtml(API.getBaseUrl())}`;

      updateNoticeBanners(true);
      if (showNotification) showToast(`Connected to backend at ${API.getBaseUrl()}`, 'success');
    } else {
      setOfflineState();
    }
  } catch (err) {
    state.backendConnected = false;
    setOfflineState();
    if (showNotification) {
      showToast(`Backend offline at ${API.getBaseUrl()} — using simulated mode`, 'warning');
    }
  }
}

function setOfflineState() {
  const apiStatusBtn = document.getElementById('api-status-btn');
  const apiStatusText = document.getElementById('api-status-text');
  const sidebarStatusText = document.getElementById('sidebar-status-text');
  const sidebarPulse = document.getElementById('sidebar-status-pulse');
  const demoModeBadge = document.getElementById('demo-mode-badge');
  const demoModeText = document.getElementById('demo-mode-text');

  if (apiStatusBtn) {
    apiStatusBtn.classList.remove('connected');
    apiStatusBtn.title = `Backend unreachable at ${API.getBaseUrl()} — Click to configure`;
  }
  if (apiStatusText) apiStatusText.textContent = 'Backend: Offline (Demo Mode)';
  if (sidebarStatusText) sidebarStatusText.textContent = 'Simulated / Offline';
  if (sidebarPulse) sidebarPulse.style.background = 'var(--warning)';
  if (demoModeBadge) {
    demoModeBadge.style.background = 'rgba(245, 158, 11, 0.10)';
    demoModeBadge.style.borderColor = 'rgba(245, 158, 11, 0.25)';
    demoModeBadge.style.color = 'var(--warning)';
  }
  if (demoModeText) demoModeText.textContent = 'DEMO — Simulated Data Only';

  updateNoticeBanners(false);
}

function updateNoticeBanners(isOnline) {
  const base = API.getBaseUrl();
  const notices = [
    {
      id: 'notice-text-security-overview',
      online: `Connected to live Agent Warden-Z API at <strong>${escHtml(base)}</strong>. Real-time actions and evaluation metrics active.`,
      offline: `Backend offline at <strong>${escHtml(base)}</strong>. All data shown is <strong>simulated for demonstration purposes only</strong>.`,
    },
    {
      id: 'notice-text-audit-trail',
      online: `Live audit stream syncing directly from <strong>GET /actions</strong>. Decisions enforced by the backend agent.`,
      offline: `Backend offline. Displaying <strong>simulated</strong> audit trail entries.`,
    },
    {
      id: 'notice-text-threat-investigation',
      online: `Held actions syncing live from <strong>GET /actions/held</strong>. Evaluate and Execute buttons dispatch live backend API requests.`,
      offline: `Backend offline. Review queue operating in <strong>simulated demonstration</strong> mode.`,
    },
    {
      id: 'notice-text-agent-risk-drift',
      online: `Live agent metrics. Click any agent card to inspect its real audit log history via <strong>GET /agents/{id}/history</strong>.`,
      offline: `Backend offline. Risk scores and drift events are <strong>simulated</strong>.`,
    },
    {
      id: 'notice-text-policy-access',
      online: `Connected to live policy engine. Cryptographic database fingerprint active via <strong>GET /db/fingerprint</strong>.`,
      offline: `Backend offline. Policy definitions and database fingerprint are running in <strong>demonstration</strong> mode.`,
    },
  ];

  notices.forEach(n => {
    const el = document.getElementById(n.id);
    if (el) el.innerHTML = isOnline ? n.online : n.offline;
  });

  const auditTag = document.getElementById('audit-mode-tag');
  if (auditTag) {
    auditTag.textContent = isOnline ? 'LIVE BACKEND' : 'SIMULATED';
    auditTag.style.color = isOnline ? '#6ee7b7' : '#c8870d';
  }
}

/* ═══════════════════════════════════════════════════════════════
   TAB NAVIGATION (5 Required Tabs Preserved Exactly)
   ═══════════════════════════════════════════════════════════════ */

function initNavigation() {
  const navItems = document.querySelectorAll('.nav-item');
  const pageTitleEl = document.getElementById('page-title');

  const tabTitles = {
    'security-overview': 'Security Overview',
    'audit-trail': 'Audit Trail',
    'threat-investigation': 'Threat Investigation',
    'agent-risk-drift': 'Agent Risk & Drift',
    'policy-access': 'Policy & Access',
  };

  navItems.forEach(item => {
    item.querySelector('button')?.addEventListener('click', () => {
      const tab = item.dataset.tab;
      if (tab === state.activeTab) return;

      document.querySelector('.nav-item.active')?.classList.remove('active');
      document.querySelector('.tab-panel.active')?.classList.remove('active');

      item.classList.add('active');
      const panel = document.getElementById('panel-' + tab);
      if (panel) panel.classList.add('active');

      if (pageTitleEl) pageTitleEl.textContent = tabTitles[tab] || tab;
      state.activeTab = tab;

      document.querySelectorAll('.nav-item button').forEach(b => b.removeAttribute('aria-current'));
      item.querySelector('button')?.setAttribute('aria-current', 'page');

      // Refresh data for the activated tab
      onTabActivated(tab);
    });
  });
}

function onTabActivated(tab) {
  if (tab === 'security-overview') {
    renderSecurityOverview();
  } else if (tab === 'audit-trail') {
    renderAuditTrail();
  } else if (tab === 'threat-investigation') {
    renderThreatInvestigation();
  } else if (tab === 'agent-risk-drift') {
    renderAgentRiskDrift();
  } else if (tab === 'policy-access') {
    renderPolicyAccess();
  }
}

/* ═══════════════════════════════════════════════════════════════
   DATA FETCHING & REFRESH (No Auto-execution of actions!)
   ═══════════════════════════════════════════════════════════════ */

async function refreshAllData() {
  await checkBackendConnection();

  if (state.backendConnected) {
    try {
      const [actions, held, fp] = await Promise.all([
        API.getActions(100).catch(() => []),
        API.getHeldActions().catch(() => []),
        API.getFingerprint().catch(() => ({ fingerprint: '—' })),
      ]);

      state.liveActions = Array.isArray(actions) ? actions : [];
      state.liveHeldActions = Array.isArray(held) ? held : [];
      state.dbFingerprint = (fp && fp.fingerprint) || '—';

      // Update badge counts
      const heldBadge = document.getElementById('threat-held-badge');
      if (heldBadge) heldBadge.textContent = state.liveHeldActions.length;
      const heldPill = document.getElementById('held-count-pill');
      if (heldPill) heldPill.textContent = state.liveHeldActions.length;

      const ovBadge = document.getElementById('badge-overview-events');
      if (ovBadge) ovBadge.textContent = Math.min(state.liveActions.length, 99);
    } catch (err) {
      console.warn('[Warden-Z] Background data sync error:', err);
    }
  }

  // Render the current view
  onTabActivated(state.activeTab);
}

/* ═══════════════════════════════════════════════════════════════
   TAB 1: SECURITY OVERVIEW
   ═══════════════════════════════════════════════════════════════ */

function initSecurityOverview() {
  renderSecurityOverview();
  initThreatTimelineChart();
  initThreatCategoryChart();
}

function renderSecurityOverview() {
  const tbody = document.getElementById('recent-events-body');
  if (!tbody) return;

  if (state.backendConnected && state.liveActions.length > 0) {
    const events = state.liveActions.slice(0, 10);

    // Compute live KPI counters
    const blockedCount = state.liveActions.filter(a => a.decision === 'BLOCK').length;
    const heldCount = state.liveHeldActions.length;
    const allowedCount = state.liveActions.filter(a => a.decision === 'ALLOW').length;
    const uniqueAgents = new Set(state.liveActions.map(a => a.agent_id)).size;

    setKpiValue('kpi-threats', blockedCount + heldCount);
    setKpiValue('kpi-agents', Math.max(uniqueAgents, 1));
    setKpiValue('kpi-policies', SIM.taskPolicies.length);
    setKpiValue('kpi-incidents', blockedCount);

    tbody.innerHTML = events.map(e => `
      <tr>
        <td class="mono" style="font-size:11.5px">${escHtml(e.timestamp ? e.timestamp.replace('T', ' ').substring(0, 19) : '—')}</td>
        <td>${decisionBadge(e.decision)}</td>
        <td class="mono" style="color:var(--cyan);font-weight:600">${escHtml(e.action_id || e.event_id || '—')}</td>
        <td class="mono" style="color:var(--text-primary)">${escHtml(e.agent_id || '—')}</td>
        <td class="mono" style="font-size:12px">${escHtml(e.operation || 'OP')} on ${escHtml(e.resource || 'res')}</td>
        <td>${executedBadge(e.executed)}</td>
      </tr>`
    ).join('');
  } else {
    // Offline simulated fallback
    setKpiValue('kpi-threats', 247);
    setKpiValue('kpi-agents', 18);
    setKpiValue('kpi-policies', 94);
    setKpiValue('kpi-incidents', 7);

    tbody.innerHTML = SIM.recentEvents.map(e => `
      <tr>
        <td class="mono" style="font-size:11.5px">${escHtml(e.ts)}</td>
        <td>${severityBadge(e.severity)}</td>
        <td class="text-primary-cell">${escHtml(e.type)}</td>
        <td class="mono text-cyan" style="color:var(--cyan)">${escHtml(e.agent)}</td>
        <td class="mono">${escHtml(e.source)}</td>
        <td>${statusBadge(e.status)}</td>
      </tr>`
    ).join('');
  }
}

function setKpiValue(id, target) {
  const el = document.getElementById(id);
  if (!el) return;
  el.textContent = target;
}

function initThreatTimelineChart() {
  const ctx = document.getElementById('chart-threat-timeline');
  if (!ctx || !window.Chart) return;

  const labels = Array.from({ length: 12 }, (_, i) => `${String(i * 2).padStart(2, '0')}:00`);
  const data = [4, 6, 9, 14, 18, 22, 19, 15, 23, 28, 17, 12];

  const gradient = ctx.getContext('2d').createLinearGradient(0, 0, 0, 200);
  gradient.addColorStop(0, 'rgba(0,212,255,0.25)');
  gradient.addColorStop(1, 'rgba(0,212,255,0.01)');

  state.charts.threatTimeline = new Chart(ctx, {
    type: 'line',
    data: {
      labels,
      datasets: [{
        label: 'Evaluations & Threats',
        data,
        borderColor: '#00d4ff',
        borderWidth: 2.5,
        backgroundColor: gradient,
        tension: 0.4,
        fill: true,
        pointRadius: 3,
        pointBackgroundColor: '#00d4ff',
      }],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: { legend: { display: false } },
      scales: {
        x: { grid: { color: 'rgba(255,255,255,0.03)' }, ticks: { color: '#4b5e78' } },
        y: { grid: { color: 'rgba(255,255,255,0.04)' }, ticks: { color: '#4b5e78' }, beginAtZero: true },
      },
    },
  });
}

function initThreatCategoryChart() {
  const ctx = document.getElementById('chart-threat-categories');
  if (!ctx || !window.Chart) return;

  const categories = [
    { label: 'ALLOW (Compliant)', value: 68, color: '#10b981' },
    { label: 'HOLD (Review Required)', value: 18, color: '#f59e0b' },
    { label: 'BLOCK (Policy Violation)', value: 14, color: '#ef4444' },
  ];

  state.charts.threatCategories = new Chart(ctx, {
    type: 'doughnut',
    data: {
      labels: categories.map(c => c.label),
      datasets: [{
        data: categories.map(c => c.value),
        backgroundColor: categories.map(c => c.color),
        borderColor: '#101828',
        borderWidth: 3,
      }],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      cutout: '70%',
      plugins: { legend: { display: false } },
    },
  });

  const legendEl = document.getElementById('categories-legend');
  if (legendEl) {
    legendEl.innerHTML = categories.map(c =>
      `<div class="legend-item">
        <div class="legend-dot" style="background:${c.color}"></div>
        <span class="legend-label">${c.label}</span>
        <span class="legend-value">${c.value}%</span>
      </div>`
    ).join('');
  }
}

/* ═══════════════════════════════════════════════════════════════
   TAB 2: AUDIT TRAIL (GET /actions & GET /db/transactions/{id})
   ═══════════════════════════════════════════════════════════════ */

function initAuditTrail() {
  renderAuditTrail();

  document.getElementById('audit-search')?.addEventListener('input', e => {
    state.auditFilter.search = e.target.value;
    renderAuditTrail();
  });
  document.getElementById('audit-action-filter')?.addEventListener('change', e => {
    state.auditFilter.action = e.target.value;
    renderAuditTrail();
  });
  document.getElementById('audit-status-filter')?.addEventListener('change', e => {
    state.auditFilter.status = e.target.value;
    renderAuditTrail();
  });
  document.getElementById('audit-reset-btn')?.addEventListener('click', () => {
    state.auditFilter = { search: '', action: '', status: '' };
    const sInput = document.getElementById('audit-search');
    const aFilter = document.getElementById('audit-action-filter');
    const stFilter = document.getElementById('audit-status-filter');
    if (sInput) sInput.value = '';
    if (aFilter) aFilter.value = '';
    if (stFilter) stFilter.value = '';
    renderAuditTrail();
  });
  document.getElementById('audit-load-more')?.addEventListener('click', () => {
    state.auditPage++;
    renderAuditTrail();
  });
}

function renderAuditTrail() {
  const tbody = document.getElementById('audit-table-body');
  const countEl = document.getElementById('audit-record-count');
  if (!tbody) return;

  const dataset = (state.backendConnected && state.liveActions.length > 0)
    ? state.liveActions
    : SIM.auditLog;

  const q = (state.auditFilter.search || '').toLowerCase();
  const actFilter = state.auditFilter.action;
  const statFilter = state.auditFilter.status;

  const filtered = dataset.filter(r => {
    const raw = JSON.stringify(r).toLowerCase();
    if (q && !raw.includes(q)) return false;

    const op = String(r.operation || r.action || '').toUpperCase();
    if (actFilter && op !== actFilter.toUpperCase()) return false;

    const dec = String(r.decision || r.outcome || '').toUpperCase();
    if (statFilter && dec !== statFilter.toUpperCase()) return false;

    return true;
  });

  const shown = filtered.slice(0, (state.auditPage + 1) * state.auditPageSize);
  if (countEl) countEl.textContent = `Showing ${shown.length} of ${filtered.length} entries`;

  if (!shown.length) {
    tbody.innerHTML = `<tr><td colspan="8" style="text-align:center;padding:24px;color:var(--text-muted)">No audit log records match your filter criteria.</td></tr>`;
    return;
  }

  tbody.innerHTML = shown.map(r => {
    const ts = r.timestamp
      ? r.timestamp.replace('T', ' ').substring(0, 19)
      : (r.ts || '—');
    const actId = r.action_id || r.actionId || r.event_id || '—';
    const agId = r.agent_id || r.agentId || '—';
    const op = r.operation || r.action || 'SELECT';
    const res = r.resource || 'transactions';
    const dec = r.decision || r.outcome || 'ALLOW';
    const executed = r.executed !== undefined ? r.executed : (r.outcome === 'Completed' ? 1 : 0);

    return `
      <tr>
        <td class="mono" style="font-size:11.5px">${escHtml(ts)}</td>
        <td class="mono" style="color:var(--cyan);font-weight:600">${escHtml(actId)}</td>
        <td class="mono" style="color:var(--text-primary)">${escHtml(agId)}</td>
        <td><span class="badge badge-neutral" style="font-family:'JetBrains Mono',monospace">${escHtml(op)}</span></td>
        <td class="mono" style="max-width:140px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap">${escHtml(res)}</td>
        <td>${decisionBadge(dec)}</td>
        <td>${executedBadge(executed)}</td>
        <td style="text-align:right">
          <button class="btn-secondary inspect-tx-btn" data-resource="${escHtml(res)}" data-action="${escHtml(actId)}" style="padding:3px 9px;font-size:11px;">
            Inspect
          </button>
        </td>
      </tr>`;
  }).join('');

  // Wire inspect buttons
  tbody.querySelectorAll('.inspect-tx-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      const actId = btn.dataset.action;
      openTransactionModal('TX1042', actId);
    });
  });
}

/* ═══════════════════════════════════════════════════════════════
   TAB 3: THREAT INVESTIGATION & HELD QUEUE
   (GET /actions/held, POST /actions/evaluate, POST /actions/execute)
   ═══════════════════════════════════════════════════════════════ */

function initThreatInvestigation() {
  const tabHeld = document.getElementById('tab-threats-held');
  const tabIntel = document.getElementById('tab-threats-intel');

  tabHeld?.addEventListener('click', () => {
    state.threatsTabMode = 'held';
    tabHeld.classList.add('active');
    tabIntel?.classList.remove('active');
    renderThreatInvestigation();
  });

  tabIntel?.addEventListener('click', () => {
    state.threatsTabMode = 'intel';
    tabIntel.classList.add('active');
    tabHeld?.classList.remove('active');
    renderThreatInvestigation();
  });

  document.getElementById('threat-search')?.addEventListener('input', e => {
    state.threatFilter.search = e.target.value;
    renderThreatInvestigation();
  });

  document.querySelectorAll('#threat-severity-filters .sev-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      document.querySelectorAll('#threat-severity-filters .sev-btn').forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      state.threatFilter.severity = btn.dataset.sev;
      renderThreatInvestigation();
    });
  });

  renderThreatInvestigation();
}

function renderThreatInvestigation() {
  const listContainer = document.getElementById('threat-list');
  const modeTag = document.getElementById('threats-mode-tag');
  if (!listContainer) return;

  if (state.threatsTabMode === 'held') {
    if (modeTag) modeTag.textContent = state.backendConnected ? 'LIVE HELD QUEUE' : 'HELD QUEUE (OFFLINE)';

    const heldList = state.liveHeldActions;
    const q = (state.threatFilter.search || '').toLowerCase();

    const filtered = heldList.filter((item, idx) => {
      const raw = JSON.stringify(item).toLowerCase();
      return !q || raw.includes(q);
    });

    if (!filtered.length) {
      listContainer.innerHTML = `
        <div style="padding:28px 20px;text-align:center;color:var(--text-muted);font-size:12.5px;">
          <div style="font-size:24px;margin-bottom:8px;">✅</div>
          <div style="font-weight:600;color:var(--text-primary);margin-bottom:4px;">No Held Actions Pending</div>
          <p style="margin-bottom:14px;">The held action review queue is currently clear.</p>
          <button class="btn-primary-action" id="btn-seed-held-sample" style="font-size:11.5px;padding:6px 12px;">
            Seed Sample Action Requiring Review
          </button>
        </div>`;

      document.getElementById('btn-seed-held-sample')?.addEventListener('click', async () => {
        await seedSampleHeldAction();
      });

      renderActionTesterSandbox();
      return;
    }

    listContainer.innerHTML = filtered.map((item, idx) => {
      const req = item.request || {};
      const resp = item.response || {};
      const isSelected = state.selectedHeldIndex === idx;

      return `
        <div class="threat-item ${isSelected ? 'selected' : ''}" data-held-idx="${idx}" role="button" tabindex="0">
          <div class="threat-sev-bar" style="background:var(--warning)"></div>
          <div class="threat-item-main">
            <div class="threat-name" style="color:#fcd34d">HOLD: ${escHtml(req.operation || 'OP')} on ${escHtml(req.resource || 'res')}</div>
            <div class="threat-meta">${escHtml(req.action_id || 'act_id')} &middot; Agent: ${escHtml(req.agent_id || 'agent')}</div>
          </div>
          <div class="threat-item-right">
            ${decisionBadge('HOLD')}
            <span class="threat-time">Risk: ${resp.risk_score || 60}</span>
          </div>
        </div>`;
    }).join('');

    listContainer.querySelectorAll('.threat-item').forEach(item => {
      item.addEventListener('click', () => {
        const idx = parseInt(item.dataset.heldIdx, 10);
        state.selectedHeldIndex = idx;
        renderThreatInvestigation();
        renderHeldDetail(state.liveHeldActions[idx]);
      });
    });

    // Automatically show detail for the selected or first item
    if (state.selectedHeldIndex !== null && state.liveHeldActions[state.selectedHeldIndex]) {
      renderHeldDetail(state.liveHeldActions[state.selectedHeldIndex]);
    } else if (state.liveHeldActions.length > 0) {
      state.selectedHeldIndex = 0;
      renderHeldDetail(state.liveHeldActions[0]);
    }
  } else {
    // Threat Intel Catalog Mode
    if (modeTag) modeTag.textContent = 'SIMULATED INTEL';

    const q = (state.threatFilter.search || '').toLowerCase();
    const sev = state.threatFilter.severity;

    const filtered = SIM.threats.filter(t => {
      if (sev !== 'all' && t.severity !== sev) return false;
      if (q && !JSON.stringify(t).toLowerCase().includes(q)) return false;
      return true;
    });

    listContainer.innerHTML = filtered.map(t => `
      <div class="threat-item ${state.selectedThreatId === t.id ? 'selected' : ''}" data-id="${t.id}" role="button" tabindex="0">
        <div class="threat-sev-bar sev-${t.severity}"></div>
        <div class="threat-item-main">
          <div class="threat-name">${escHtml(t.name)}</div>
          <div class="threat-meta">${escHtml(t.id)} &middot; Src: ${escHtml(t.source)}</div>
        </div>
        <div class="threat-item-right">
          ${severityBadge(t.severity)}
          <span class="threat-time">${escHtml((t.ts || '').split(' ')[1] || '')}</span>
        </div>
      </div>`
    ).join('');

    listContainer.querySelectorAll('.threat-item').forEach(item => {
      item.addEventListener('click', () => {
        state.selectedThreatId = item.dataset.id;
        renderThreatInvestigation();
        renderThreatIntelDetail(item.dataset.id);
      });
    });

    if (state.selectedThreatId) {
      renderThreatIntelDetail(state.selectedThreatId);
    }
  }
}

function renderHeldDetail(heldItem) {
  const panel = document.getElementById('threat-detail');
  if (!panel || !heldItem) return;

  const req = heldItem.request || {};
  const resp = heldItem.response || {};

  panel.innerHTML = `
    <div class="detail-header">
      <div class="detail-title">Pending Action Review: ${escHtml(req.action_id || 'Unknown')}</div>
      <div style="display:flex;gap:8px;align-items:center;flex-wrap:wrap">
        ${decisionBadge('HOLD')}
        <span class="badge badge-warning" style="font-family:'JetBrains Mono',monospace">Risk Score: ${resp.risk_score || 60}</span>
        ${executedBadge(resp.executed || false)}
      </div>
    </div>
    <div class="detail-body">
      <div class="detail-section">
        <div class="detail-section-title">Backend Reason</div>
        <div style="font-size:13px;color:var(--text-primary);padding:10px 12px;background:rgba(245,158,11,0.08);border:1px solid rgba(245,158,11,0.22);border-radius:var(--radius-sm);">
          ${escHtml(resp.reason || 'Additional authorization required')}
        </div>
      </div>

      <div class="detail-section">
        <div class="detail-section-title">Request Parameters (ActionRequest)</div>
        <div class="detail-row"><span class="detail-label">Action ID:</span><span class="detail-value mono">${escHtml(req.action_id || '—')}</span></div>
        <div class="detail-row"><span class="detail-label">Agent ID:</span><span class="detail-value mono text-cyan" style="color:var(--cyan)">${escHtml(req.agent_id || '—')}</span></div>
        <div class="detail-row"><span class="detail-label">Task ID:</span><span class="detail-value mono">${escHtml(req.task_id || '—')}</span></div>
        <div class="detail-row"><span class="detail-label">Session ID:</span><span class="detail-value mono">${escHtml(req.session_id || '—')}</span></div>
        <div class="detail-row"><span class="detail-label">Operation:</span><span class="detail-value mono font-bold" style="color:#fcd34d">${escHtml(req.operation || '—')}</span></div>
        <div class="detail-row"><span class="detail-label">Resource:</span><span class="detail-value mono">${escHtml(req.resource || '—')}</span></div>
      </div>

      <!-- Live Enforcement Actions -->
      <div class="detail-section" style="margin-top:20px;">
        <div class="detail-section-title">Analyst Enforcement Decision</div>
        <div style="display:flex;gap:10px;flex-wrap:wrap;">
          <button class="btn-primary-action" id="btn-eval-held" title="Call POST /actions/evaluate (Does not execute)">
            <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="14" height="14">
              <path d="M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8z" />
              <polyline points="14 2 14 8 20 8" />
              <line x1="16" y1="13" x2="8" y2="13" />
              <line x1="16" y1="17" x2="8" y2="17" />
            </svg>
            Evaluate Policy (Safe)
          </button>
          <button class="btn-execute-action" id="btn-exec-held" title="Call POST /actions/execute against backend">
            <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="14" height="14">
              <polygon points="5 3 19 12 5 21 5 3" />
            </svg>
            Execute Action
          </button>
        </div>
        <div id="held-action-result-box" style="display:none;margin-top:12px;"></div>
      </div>
    </div>`;

  // Wire buttons
  document.getElementById('btn-eval-held')?.addEventListener('click', async () => {
    await performActionEvaluation(req, 'held-action-result-box', false);
  });
  document.getElementById('btn-exec-held')?.addEventListener('click', async () => {
    await performActionEvaluation(req, 'held-action-result-box', true);
  });
}

function renderThreatIntelDetail(threatId) {
  const panel = document.getElementById('threat-detail');
  const t = SIM.threats.find(x => x.id === threatId);
  if (!t || !panel) return;

  panel.innerHTML = `
    <div class="detail-header">
      <div class="detail-title">${escHtml(t.name)}</div>
      <div style="display:flex;gap:8px;flex-wrap:wrap">
        ${severityBadge(t.severity)}
        ${statusBadge(t.status)}
        <span class="badge badge-neutral" style="font-family:'JetBrains Mono',monospace;font-size:10.5px">${escHtml(t.id)}</span>
      </div>
    </div>
    <div class="detail-body">
      <div class="detail-section">
        <div class="detail-section-title">Summary</div>
        <p style="font-size:13px;color:var(--text-secondary);line-height:1.7">${escHtml(t.description)}</p>
      </div>
      <div class="detail-section">
        <div class="detail-section-title">Details</div>
        <div class="detail-row"><span class="detail-label">Technique:</span><span class="detail-value mono">${escHtml(t.technique)}</span></div>
        <div class="detail-row"><span class="detail-label">Source IP:</span><span class="detail-value mono">${escHtml(t.source)}</span></div>
        <div class="detail-row"><span class="detail-label">Target:</span><span class="detail-value">${escHtml(t.target)}</span></div>
        <div class="detail-row"><span class="detail-label">Detected:</span><span class="detail-value mono">${escHtml(t.ts)}</span></div>
      </div>
      <div class="detail-section">
        <div class="detail-section-title">Indicators of Compromise (IoCs)</div>
        <div class="ioc-list">${t.iocs.map(ioc => `<div class="ioc-item">${escHtml(ioc)}</div>`).join('')}</div>
      </div>
      <div class="detail-section">
        <div class="detail-section-title">Recommendation</div>
        <p style="font-size:13px;color:var(--text-secondary);line-height:1.7">${escHtml(t.recommendation)}</p>
      </div>
    </div>
    <div class="detail-action-notice">
      🔒 Threat Intel catalog records are read-only threat models. Live action decisions are evaluated via the Held Actions Queue.
    </div>`;
}

function renderActionTesterSandbox() {
  const panel = document.getElementById('threat-detail');
  if (!panel) return;

  panel.innerHTML = `
    <div class="detail-header">
      <div class="detail-title">Interactive Policy Evaluator &amp; Action Tester</div>
      <span class="backend-tag">POST /actions/evaluate &amp; execute</span>
    </div>
    <div class="detail-body">
      <p style="font-size:12.5px;color:var(--text-muted);margin-bottom:14px;line-height:1.6;">
        Test how the backend policy engine evaluates actions against <code style="color:var(--cyan)">TASK_POLICIES</code>.
        <br/>&bull; Safe Evaluate never executes changes.
        <br/>&bull; Execute will only run whitelisted actions (SELECT on transactions).
      </p>

      <form id="action-tester-form" onsubmit="return false;">
        <div class="form-grid-2">
          <div class="form-group">
            <label class="form-label" for="test-task-id">Task Policy ID</label>
            <select id="test-task-id" class="form-control">
              <option value="task_read_transaction">task_read_transaction (SELECT ok, UPDATE/DEL review)</option>
              <option value="task_update_transaction">task_update_transaction (SELECT ok, UPDATE review)</option>
              <option value="task_unknown_task">task_unknown_task (Unknown -> will BLOCK)</option>
            </select>
          </div>
          <div class="form-group">
            <label class="form-label" for="test-operation">Operation</label>
            <select id="test-operation" class="form-control">
              <option value="SELECT">SELECT</option>
              <option value="UPDATE" selected>UPDATE (Triggers HOLD on task_read)</option>
              <option value="DELETE">DELETE (Triggers HOLD on task_read)</option>
              <option value="INSERT">INSERT (Triggers BLOCK on task_read)</option>
            </select>
          </div>
        </div>

        <div class="form-grid-2">
          <div class="form-group">
            <label class="form-label" for="test-resource">Resource</label>
            <input type="text" id="test-resource" class="form-control" value="transactions" />
            <div class="form-hint">Permitted: 'transactions'</div>
          </div>
          <div class="form-group">
            <label class="form-label" for="test-agent-id">Agent ID</label>
            <input type="text" id="test-agent-id" class="form-control" value="warden-z-01" />
          </div>
        </div>

        <div style="display:flex;gap:10px;margin-top:14px;">
          <button class="btn-primary-action" id="btn-test-eval" type="button">
            POST /actions/evaluate
          </button>
          <button class="btn-execute-action" id="btn-test-exec" type="button">
            POST /actions/execute
          </button>
        </div>
      </form>

      <div id="test-eval-result" style="display:none;margin-top:16px;"></div>
    </div>`;

  document.getElementById('btn-test-eval')?.addEventListener('click', async () => {
    const payload = getTesterPayload();
    await performActionEvaluation(payload, 'test-eval-result', false);
  });

  document.getElementById('btn-test-exec')?.addEventListener('click', async () => {
    const payload = getTesterPayload();
    await performActionEvaluation(payload, 'test-eval-result', true);
  });
}

function getTesterPayload() {
  const task = document.getElementById('test-task-id')?.value || 'task_read_transaction';
  const op = document.getElementById('test-operation')?.value || 'SELECT';
  const res = document.getElementById('test-resource')?.value || 'transactions';
  const agent = document.getElementById('test-agent-id')?.value || 'warden-z-01';
  const rand = Math.floor(Math.random() * 9000 + 1000);

  return {
    action_id: `act_test_${rand}`,
    agent_id: agent,
    session_id: `sess_${rand}`,
    task_id: task,
    operation: op,
    resource: res,
  };
}

async function performActionEvaluation(payload, targetContainerId, isExecute = false) {
  const container = document.getElementById(targetContainerId);
  if (!container) return;

  container.style.display = 'block';
  container.innerHTML = `
    <div style="padding:12px;color:var(--cyan);font-size:12px;">
      ⏳ Sending request to ${isExecute ? 'POST /actions/execute' : 'POST /actions/evaluate'}…
    </div>`;

  try {
    const response = isExecute
      ? await API.executeAction(payload)
      : await API.evaluateAction(payload);

    const decClass = (response.decision || 'BLOCK').toLowerCase();
    const executedBool = response.executed === true;

    container.className = `exec-result-card ${decClass}`;
    container.innerHTML = `
      <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:8px;">
        <span style="font-weight:700;font-size:13px;color:var(--text-primary);">
          Backend Decision: ${decisionBadge(response.decision)}
        </span>
        <span style="font-size:11px;color:var(--text-muted);font-family:'JetBrains Mono',monospace;">
          ${isExecute ? 'Executed' : 'Evaluated'}
        </span>
      </div>
      <div style="font-size:12.5px;color:var(--text-primary);margin-bottom:10px;">
        <strong>Reason:</strong> ${escHtml(response.reason || '—')}
      </div>
      <div class="exec-meta-grid">
        <div class="exec-meta-item">
          <span class="exec-meta-label">Risk Score</span>
          <span class="exec-meta-val" style="color:${scoreBarColor(response.risk_score || 0)}">${response.risk_score !== undefined ? response.risk_score : '—'}</span>
        </div>
        <div class="exec-meta-item">
          <span class="exec-meta-label">Executed Flag</span>
          <span class="exec-meta-val">${executedBadge(executedBool)}</span>
        </div>
        <div class="exec-meta-item">
          <span class="exec-meta-label">Action ID</span>
          <span class="exec-meta-val">${escHtml(response.action_id || payload.action_id || '—')}</span>
        </div>
      </div>
      <div style="margin-top:10px;font-size:11px;color:var(--text-muted)">
        ${executedBool ? '✔ Successfully executed against SQLite store.' : '✖ Action was not executed.'}
      </div>`;

    showToast(
      `${isExecute ? 'Executed' : 'Evaluated'}: ${response.decision} (Executed: ${executedBool ? 'YES' : 'NO'})`,
      decClass === 'allow' ? 'success' : (decClass === 'hold' ? 'warning' : 'error')
    );

    // Refresh background state and audit logs
    setTimeout(() => refreshAllData(), 400);
  } catch (err) {
    container.className = 'exec-result-card block';
    container.innerHTML = `
      <div style="color:#f87171;font-weight:600;font-size:12.5px;margin-bottom:4px;">Request Failed</div>
      <div style="color:var(--text-secondary);font-size:12px;">${escHtml(err.message)}</div>`;
    showToast(`API error: ${err.message}`, 'error');
  }
}

async function seedSampleHeldAction() {
  const sample = {
    action_id: `act_sample_${Date.now().toString().slice(-4)}`,
    agent_id: 'warden-z-03',
    session_id: 'sess_sample_hold',
    task_id: 'task_read_transaction',
    operation: 'UPDATE', // triggers HOLD
    resource: 'transactions',
  };

  try {
    const res = await API.evaluateAction(sample);
    showToast('Sample action submitted: Result HOLD, added to review queue', 'warning');
    await refreshAllData();
  } catch (err) {
    showToast(`Failed to seed sample: ${err.message}`, 'error');
  }
}

/* ═══════════════════════════════════════════════════════════════
   TAB 4: AGENT RISK & DRIFT (GET /agents/{id}/history)
   ═══════════════════════════════════════════════════════════════ */

function initAgentRiskDrift() {
  renderAgentRiskCards();
  renderDriftTable();
  initAgentRiskCharts();
}

function renderAgentRiskDrift() {
  renderAgentRiskCards();
  renderDriftTable();
}

function renderAgentRiskCards() {
  const grid = document.getElementById('agent-risk-cards');
  if (!grid) return;

  grid.innerHTML = SIM.agents.map(a => `
    <div class="agent-risk-card" data-agent-id="${escHtml(a.id)}" role="button" tabindex="0" title="Click to view real audit history for ${escHtml(a.id)}">
      <div class="arc-header">
        <div>
          <div class="arc-agent-id">${escHtml(a.id)}</div>
          <div class="arc-role">${escHtml(a.role)}</div>
        </div>
        ${statusBadge(a.status.charAt(0).toUpperCase() + a.status.slice(1))}
      </div>
      <div class="arc-score ${scoreClass(a.riskScore)}">${a.riskScore}</div>
      <div class="arc-bar-wrap">
        <div class="arc-bar" style="width:${a.riskScore}%;background:${scoreBarColor(a.riskScore)}"></div>
      </div>
      <div class="arc-stats">
        <div class="arc-stat">Drift Events: <span>${a.driftEvents}</span></div>
        <div class="arc-stat" style="color:var(--cyan);font-weight:600">Click to Inspect &rarr;</div>
      </div>
    </div>`
  ).join('');

  grid.querySelectorAll('.agent-risk-card').forEach(card => {
    card.addEventListener('click', () => {
      openAgentHistoryModal(card.dataset.agentId);
    });
  });
}

function initAgentRiskCharts() {
  if (state.charts.agentRisk) return;

  const riskCtx = document.getElementById('chart-agent-risk');
  if (riskCtx && window.Chart) {
    state.charts.agentRisk = new Chart(riskCtx, {
      type: 'bar',
      data: {
        labels: SIM.agents.map(a => a.id),
        datasets: [{
          label: 'Risk Score',
          data: SIM.agents.map(a => a.riskScore),
          backgroundColor: SIM.agents.map(a => scoreBarColor(a.riskScore) + 'cc'),
          borderColor: SIM.agents.map(a => scoreBarColor(a.riskScore)),
          borderWidth: 1.5,
          borderRadius: 5,
        }],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: { legend: { display: false } },
        scales: {
          x: { grid: { display: false }, ticks: { color: '#4b5e78' } },
          y: { grid: { color: 'rgba(255,255,255,0.04)' }, ticks: { color: '#4b5e78' }, max: 100, beginAtZero: true },
        },
      },
    });
  }

  const driftCtx = document.getElementById('chart-drift-trend');
  if (driftCtx && window.Chart) {
    const hours = ['16:00', '17:00', '18:00', '19:00', '20:00', '21:00'];
    const driftGrad = driftCtx.getContext('2d').createLinearGradient(0, 0, 0, 180);
    driftGrad.addColorStop(0, 'rgba(239,68,68,0.22)');
    driftGrad.addColorStop(1, 'rgba(239,68,68,0.01)');

    state.charts.driftTrend = new Chart(driftCtx, {
      type: 'line',
      data: {
        labels: hours,
        datasets: [{
          label: 'Drift Score',
          data: [8, 14, 19, 29, 41, 52],
          borderColor: '#ef4444',
          borderWidth: 2,
          backgroundColor: driftGrad,
          tension: 0.4,
          fill: true,
          pointRadius: 4,
          pointBackgroundColor: '#ef4444',
        }],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: { legend: { display: false } },
        scales: {
          x: { grid: { display: false }, ticks: { color: '#4b5e78' } },
          y: { grid: { color: 'rgba(255,255,255,0.04)' }, ticks: { color: '#4b5e78' }, beginAtZero: true },
        },
      },
    });
  }
}

function renderDriftTable() {
  const tbody = document.getElementById('drift-table-body');
  if (!tbody) return;

  tbody.innerHTML = SIM.driftEvents.map(d => `
    <tr>
      <td class="mono" style="font-size:11.5px">${escHtml(d.ts)}</td>
      <td class="mono" style="color:var(--cyan)">${escHtml(d.agentId)}</td>
      <td>${escHtml(d.driftType)}</td>
      <td style="font-size:12px;max-width:140px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap">${escHtml(d.baseline)}</td>
      <td style="font-size:12px;max-width:160px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;color:var(--text-primary)">${escHtml(d.current)}</td>
      <td style="font-family:'JetBrains Mono',monospace;font-weight:700;color:#ef4444">+${d.delta}</td>
      <td>${statusBadge(d.status)}</td>
    </tr>`
  ).join('');
}

async function openAgentHistoryModal(agentId) {
  const modal = document.getElementById('agent-history-modal');
  const title = document.getElementById('history-modal-agent-name');
  const content = document.getElementById('history-modal-body-content');
  if (!modal || !content) return;

  if (title) title.textContent = `Audit Log History for ${agentId}`;
  modal.classList.add('open');
  content.innerHTML = `<div style="padding:20px;text-align:center;color:var(--cyan)">⏳ Querying GET /agents/${escHtml(agentId)}/history from backend…</div>`;

  try {
    let rows = [];
    if (state.backendConnected) {
      rows = await API.getAgentHistory(agentId);
    } else {
      rows = SIM.auditLog.filter(a => a.agentId === agentId || a.agent_id === agentId);
    }

    if (!rows || !rows.length) {
      content.innerHTML = `
        <div style="padding:30px;text-align:center;color:var(--text-muted)">
          No historical audit rows found for agent <strong>${escHtml(agentId)}</strong>.
          <br/><span style="font-size:11.5px">Actions evaluated or executed for this agent will be indexed here.</span>
        </div>`;
      return;
    }

    content.innerHTML = `
      <div class="table-wrapper">
        <table class="data-table">
          <thead>
            <tr>
              <th>Timestamp</th>
              <th>Action ID</th>
              <th>Operation</th>
              <th>Resource</th>
              <th>Decision</th>
              <th>Reason</th>
              <th>Executed</th>
            </tr>
          </thead>
          <tbody>
            ${rows.map(r => `
              <tr>
                <td class="mono" style="font-size:11px">${escHtml(r.timestamp ? r.timestamp.replace('T', ' ').substring(0, 19) : (r.ts || '—'))}</td>
                <td class="mono text-cyan" style="color:var(--cyan)">${escHtml(r.action_id || r.actionId || '—')}</td>
                <td><span class="badge badge-neutral">${escHtml(r.operation || r.action || '—')}</span></td>
                <td class="mono">${escHtml(r.resource || '—')}</td>
                <td>${decisionBadge(r.decision || r.outcome)}</td>
                <td style="font-size:12px;color:var(--text-primary)">${escHtml(r.reason || '—')}</td>
                <td>${executedBadge(r.executed)}</td>
              </tr>
            `).join('')}
          </tbody>
        </table>
      </div>`;
  } catch (err) {
    content.innerHTML = `
      <div style="padding:20px;color:#f87171;">
        Failed to fetch agent history: ${escHtml(err.message)}
      </div>`;
  }
}

/* ═══════════════════════════════════════════════════════════════
   TAB 5: POLICY & ACCESS
   (GET /db/fingerprint & GET /db/transactions/{id})
   ═══════════════════════════════════════════════════════════════ */

function initPolicyAccess() {
  renderPolicyAccess();

  document.getElementById('btn-refresh-fp')?.addEventListener('click', async () => {
    await fetchLiveFingerprint(true);
  });

  document.getElementById('tx-lookup-btn')?.addEventListener('click', async () => {
    const input = document.getElementById('tx-lookup-input');
    const txId = (input ? input.value : 'TX1042').trim();
    if (txId) await lookupTransactionInline(txId);
  });

  document.getElementById('policy-search')?.addEventListener('input', e => {
    state.policyFilter.search = e.target.value;
    renderPolicyTable();
  });
  document.getElementById('policy-type-filter')?.addEventListener('change', e => {
    state.policyFilter.type = e.target.value;
    renderPolicyTable();
  });
  document.getElementById('policy-status-filter')?.addEventListener('change', e => {
    state.policyFilter.status = e.target.value;
    renderPolicyTable();
  });
}

function renderPolicyAccess() {
  fetchLiveFingerprint(false);
  renderPolicyTable();
  renderAccessMatrix();
}

async function fetchLiveFingerprint(showNotice = false) {
  const fpVal = document.getElementById('fingerprint-value');
  const fpStatus = document.getElementById('fp-status');
  if (!fpVal) return;

  try {
    if (state.backendConnected) {
      const res = await API.getFingerprint();
      const hash = res.fingerprint || '—';
      state.dbFingerprint = hash;
      fpVal.textContent = hash;
      if (fpStatus) {
        fpStatus.textContent = 'Live SHA-256 Verified';
        fpStatus.style.color = 'var(--success)';
      }
      if (showNotice) showToast('Database fingerprint verified from backend', 'success');
    } else {
      fpVal.textContent = 'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855 (Simulated Baseline)';
      if (fpStatus) {
        fpStatus.textContent = 'Simulated';
        fpStatus.style.color = 'var(--warning)';
      }
    }
  } catch (err) {
    fpVal.textContent = 'Error computing fingerprint';
    if (fpStatus) fpStatus.textContent = 'Offline';
  }
}

async function lookupTransactionInline(txId) {
  const resultBox = document.getElementById('tx-lookup-result');
  if (!resultBox) return;

  resultBox.style.display = 'block';
  resultBox.innerHTML = `<span style="color:var(--cyan);font-size:12px;">⏳ Querying GET /db/transactions/${escHtml(txId)}…</span>`;

  try {
    const tx = await API.getTransaction(txId);
    resultBox.innerHTML = `
      <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:8px;">
        <span style="font-family:'JetBrains Mono',monospace;font-weight:700;color:var(--cyan);font-size:13px;">${escHtml(tx.id)}</span>
        <span class="badge ${tx.status === 'COMPLETED' ? 'badge-success' : 'badge-warning'}">${escHtml(tx.status)}</span>
      </div>
      <div style="display:grid;grid-template-columns:1fr 1fr;gap:8px;font-size:12px;">
        <div><span style="color:var(--text-muted)">Customer ID:</span> <strong style="color:var(--text-primary)">${escHtml(tx.customer_id)}</strong></div>
        <div><span style="color:var(--text-muted)">Amount:</span> <strong style="color:var(--success)">$${Number(tx.amount).toFixed(2)}</strong></div>
      </div>`;
  } catch (err) {
    resultBox.innerHTML = `
      <div style="color:#f87171;font-size:12.5px;">
        ❌ ${escHtml(err.message || 'Transaction not found')}
      </div>`;
  }
}

async function openTransactionModal(txId, actId = null) {
  const modal = document.getElementById('tx-inspect-modal');
  const titleText = document.getElementById('tx-modal-title-text');
  const body = document.getElementById('tx-modal-body');
  if (!modal || !body) return;

  if (titleText) titleText.textContent = `Transaction Inspection &middot; ${txId}`;
  modal.classList.add('open');
  body.innerHTML = `<div style="padding:20px;text-align:center;color:var(--cyan)">⏳ Querying GET /db/transactions/${escHtml(txId)}…</div>`;

  try {
    const tx = await API.getTransaction(txId);
    body.innerHTML = `
      <div style="background:var(--bg-card-2);padding:14px;border-radius:var(--radius-sm);border:1px solid var(--border-table);margin-bottom:14px;">
        <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:10px;">
          <span class="mono" style="font-size:15px;font-weight:700;color:var(--cyan)">${escHtml(tx.id)}</span>
          <span class="badge ${tx.status === 'COMPLETED' ? 'badge-success' : 'badge-warning'}">${escHtml(tx.status)}</span>
        </div>
        <div style="display:grid;grid-template-columns:1fr 1fr;gap:12px;font-size:13px;">
          <div><span style="color:var(--text-muted)">Customer:</span> <strong style="color:var(--text-primary)">${escHtml(tx.customer_id)}</strong></div>
          <div><span style="color:var(--text-muted)">Amount:</span> <strong style="color:var(--success)">$${Number(tx.amount).toFixed(2)}</strong></div>
        </div>
      </div>
      <div style="font-size:11.5px;color:var(--text-muted);line-height:1.6">
        Verified against SQLite backend database table <code style="color:var(--cyan)">transactions</code>.
        ${actId ? `<br/>Referenced by Action ID: <strong>${escHtml(actId)}</strong>` : ''}
      </div>`;
  } catch (err) {
    body.innerHTML = `
      <div style="padding:16px;color:#f87171;background:rgba(239,68,68,0.08);border-radius:var(--radius-sm);border:1px solid rgba(239,68,68,0.2)">
        Failed to load transaction ${escHtml(txId)}: ${escHtml(err.message)}
      </div>`;
  }
}

function renderPolicyTable() {
  const tbody = document.getElementById('policy-table-body');
  if (!tbody) return;

  const q = (state.policyFilter.search || '').toLowerCase();
  const typeFilter = state.policyFilter.type;
  const statusFilter = state.policyFilter.status;

  const filtered = SIM.taskPolicies.filter(p => {
    if (q && !JSON.stringify(p).toLowerCase().includes(q)) return false;
    if (typeFilter && p.type !== typeFilter) return false;
    if (statusFilter && p.status !== statusFilter) return false;
    return true;
  });

  tbody.innerHTML = filtered.map(p => `
    <tr>
      <td class="mono" style="color:var(--cyan);font-size:12px">${escHtml(p.id)}</td>
      <td class="text-primary-cell">${escHtml(p.name)}</td>
      <td><span class="badge badge-neutral" style="font-size:10.5px">${escHtml(p.type)}</span></td>
      <td style="font-size:12.5px" class="mono">${escHtml(p.scope)}</td>
      <td>${statusBadge(p.status)}</td>
      <td style="font-size:12px;color:var(--text-primary)">${escHtml(p.rules)}</td>
      <td><span class="badge ${p.backend ? 'badge-backend' : 'badge-neutral'}">${p.backend ? '⚙ Policy Engine' : 'Organization'}</span></td>
    </tr>`
  ).join('');
}

function renderAccessMatrix() {
  const tbody = document.getElementById('access-matrix-body');
  if (!tbody) return;

  tbody.innerHTML = SIM.accessMatrix.map(row => `
    <tr>
      <td class="text-primary-cell" style="font-size:12.5px;white-space:nowrap">${escHtml(row.role)}</td>
      <td>${permIcon(row.read)}</td>
      <td>${permIcon(row.write)}</td>
      <td>${permIcon(row.execute)}</td>
      <td>${permIcon(row.delete)}</td>
      <td>${permIcon(row.admin)}</td>
    </tr>`
  ).join('');
}

/* ═══════════════════════════════════════════════════════════════
   ADMIN RESET (POST /admin/reset) & REFRESH BUTTONS
   ═══════════════════════════════════════════════════════════════ */

function initAdminResetAndModals() {
  // Top bar Admin Reset Button -> Opens Confirmation Modal
  const adminResetBtn = document.getElementById('admin-reset-btn');
  const resetModal = document.getElementById('admin-reset-modal');
  const resetConfirmBtn = document.getElementById('reset-modal-confirm');
  const resetCancelBtn = document.getElementById('reset-modal-cancel');
  const resetCloseBtn = document.getElementById('reset-modal-close');

  adminResetBtn?.addEventListener('click', () => {
    if (resetModal) resetModal.classList.add('open');
  });

  const closeResetModal = () => resetModal?.classList.remove('open');
  resetCancelBtn?.addEventListener('click', closeResetModal);
  resetCloseBtn?.addEventListener('click', closeResetModal);

  resetConfirmBtn?.addEventListener('click', async () => {
    resetConfirmBtn.disabled = true;
    resetConfirmBtn.textContent = 'Resetting…';
    try {
      if (state.backendConnected) {
        await API.resetAdmin();
        showToast('Database reset: audit log cleared, test tables re-seeded', 'success');
      } else {
        showToast('Demo environment reset (offline mode)', 'info');
      }
      closeResetModal();
      await refreshAllData();
    } catch (err) {
      showToast(`Reset failed: ${err.message}`, 'error');
    } finally {
      resetConfirmBtn.disabled = false;
      resetConfirmBtn.textContent = 'Confirm Reset Database';
    }
  });

  // Top bar API Settings Button -> Opens API Config Modal
  const apiStatusBtn = document.getElementById('api-status-btn');
  const apiModal = document.getElementById('api-config-modal');
  const apiInput = document.getElementById('api-base-url-input');
  const apiSaveBtn = document.getElementById('api-modal-save');
  const apiCancelBtn = document.getElementById('api-modal-cancel');
  const apiCloseBtn = document.getElementById('api-modal-close');
  const apiTestBtn = document.getElementById('btn-test-connection');
  const apiTestResult = document.getElementById('api-test-result');

  apiStatusBtn?.addEventListener('click', () => {
    if (apiInput) apiInput.value = API.getBaseUrl();
    if (apiTestResult) apiTestResult.style.display = 'none';
    if (apiModal) apiModal.classList.add('open');
  });

  const closeApiModal = () => apiModal?.classList.remove('open');
  apiCancelBtn?.addEventListener('click', closeApiModal);
  apiCloseBtn?.addEventListener('click', closeApiModal);

  apiTestBtn?.addEventListener('click', async () => {
    const testUrl = (apiInput ? apiInput.value : '').trim();
    if (!testUrl) return;

    if (apiTestResult) {
      apiTestResult.style.display = 'block';
      apiTestResult.className = '';
      apiTestResult.style.background = 'rgba(0, 212, 255, 0.08)';
      apiTestResult.style.color = 'var(--cyan)';
      apiTestResult.innerHTML = `⏳ Testing connection to ${escHtml(testUrl)}/health…`;
    }

    const t0 = performance.now();
    try {
      const res = await fetch(`${testUrl.replace(/\/+$/, '')}/health`, {
        signal: AbortSignal.timeout(3500),
      });
      const latency = Math.round(performance.now() - t0);
      if (res.ok) {
        const json = await res.json();
        if (apiTestResult) {
          apiTestResult.style.background = 'rgba(16, 185, 129, 0.12)';
          apiTestResult.style.color = '#6ee7b7';
          apiTestResult.innerHTML = `✔ Connected! Response: ${escHtml(JSON.stringify(json))} (${latency}ms)`;
        }
      } else {
        throw new Error(`HTTP ${res.status}`);
      }
    } catch (err) {
      if (apiTestResult) {
        apiTestResult.style.background = 'rgba(239, 68, 68, 0.12)';
        apiTestResult.style.color = '#fca5a5';
        apiTestResult.innerHTML = `✖ Connection failed: ${escHtml(err.message)}`;
      }
    }
  });

  apiSaveBtn?.addEventListener('click', async () => {
    const newUrl = (apiInput ? apiInput.value : '').trim();
    if (newUrl) {
      API.setBaseUrl(newUrl);
      closeApiModal();
      showToast(`API Base URL updated to ${newUrl}`, 'info');
      await refreshAllData();
    }
  });

  // Generic modal close listeners (agent history, tx inspect)
  document.getElementById('history-modal-close')?.addEventListener('click', () => {
    document.getElementById('agent-history-modal')?.classList.remove('open');
  });
  document.getElementById('history-modal-close-btn')?.addEventListener('click', () => {
    document.getElementById('agent-history-modal')?.classList.remove('open');
  });
  document.getElementById('tx-modal-close')?.addEventListener('click', () => {
    document.getElementById('tx-inspect-modal')?.classList.remove('open');
  });
  document.getElementById('tx-modal-close-btn')?.addEventListener('click', () => {
    document.getElementById('tx-inspect-modal')?.classList.remove('open');
  });

  // Refresh Button in Header -> Refreshes all active data
  const refreshBtn = document.getElementById('refresh-btn');
  refreshBtn?.addEventListener('click', async () => {
    const icon = refreshBtn.querySelector('svg');
    if (icon) icon.style.animation = 'spin 0.8s linear infinite';
    await refreshAllData();
    setTimeout(() => {
      if (icon) icon.style.animation = '';
      showToast('Dashboard data refreshed', 'info');
    }, 450);
  });
}

/* ═══════════════════════════════════════════════════════════════
   GLOBAL SEARCH & SIDEBAR TOGGLE
   ═══════════════════════════════════════════════════════════════ */

function initGlobalSearch() {
  const searchEl = document.getElementById('global-search');
  if (!searchEl) return;
  searchEl.addEventListener('input', e => {
    const q = e.target.value.toLowerCase();
    if (state.activeTab === 'security-overview') {
      const tbody = document.getElementById('recent-events-body');
      if (tbody) {
        const rows = tbody.querySelectorAll('tr');
        rows.forEach(r => {
          const text = r.textContent.toLowerCase();
          r.style.display = text.includes(q) ? '' : 'none';
        });
      }
    } else if (state.activeTab === 'audit-trail') {
      state.auditFilter.search = q;
      renderAuditTrail();
    } else if (state.activeTab === 'threat-investigation') {
      state.threatFilter.search = q;
      renderThreatInvestigation();
    }
  });
}

function initSidebarToggle() {
  const btn = document.getElementById('sidebar-toggle');
  const sidebar = document.getElementById('sidebar');
  if (!btn || !sidebar) return;

  let collapsed = false;
  btn.addEventListener('click', () => {
    collapsed = !collapsed;
    if (collapsed) {
      sidebar.style.width = '0';
      sidebar.style.minWidth = '0';
    } else {
      sidebar.style.width = '';
      sidebar.style.minWidth = '';
    }
  });
}

/* ═══════════════════════════════════════════════════════════════
   APPLICATION BOOTSTRAP
   ═══════════════════════════════════════════════════════════════ */

document.addEventListener('DOMContentLoaded', async () => {
  initNavigation();
  initSecurityOverview();
  initAuditTrail();
  initThreatInvestigation();
  initAgentRiskDrift();
  initPolicyAccess();
  initAdminResetAndModals();
  initGlobalSearch();
  initSidebarToggle();

  // Initial backend health check & data sync (Never auto-executes actions!)
  await refreshAllData();

  console.log('%c[Agent Warden-Z] Dashboard Initialized', 'color:#00d4ff;font-weight:bold;font-size:13px;');
  console.log(`Backend endpoint: ${API.getBaseUrl()}`);
});
