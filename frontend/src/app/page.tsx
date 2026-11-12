"use client";

import dynamic from "next/dynamic";
import {
  Activity,
  ArrowUpRight,
  BadgeCheck,
  Bell,
  CircleHelp,
  ClipboardList,
  Fingerprint,
  LockKeyhole,
  LogOut,
  ScanLine,
  ShieldCheck,
  Stethoscope,
  UsersRound,
  Waypoints
} from "lucide-react";
import { QRCodeSVG } from "qrcode.react";
import { FormEvent, ReactNode, useEffect, useRef, useState } from "react";
import { apiRequest, RoutingResult, signIn } from "@/lib/api";

function Scanner({ onScan, onError }: { onScan: (value: string) => void; onError: (message: string) => void }) {
  const onScanRef = useRef(onScan);
  const onErrorRef = useRef(onError);
  onScanRef.current = onScan;
  onErrorRef.current = onError;
  useEffect(() => {
    let scanner: import("html5-qrcode").Html5QrcodeScanner | undefined;
    let cancelled = false;
    void import("html5-qrcode").then(({ Html5QrcodeScanner }) => {
      if (cancelled) return;
      scanner = new Html5QrcodeScanner("identity-qr-reader", { fps: 8, qrbox: { width: 220, height: 220 } }, false);
      scanner.render((text) => {
        onScanRef.current(text);
        void scanner?.clear();
      }, (message) => {
        if (message.includes("NotAllowedError") || message.includes("NotFoundError")) {
          onErrorRef.current("Camera access is unavailable or was denied.");
        }
      });
    }).catch(() => onErrorRef.current("QR scanner could not be initialized."));
    return () => {
      cancelled = true;
      void scanner?.clear();
    };
  }, []);
  return <div id="identity-qr-reader" className="qr-reader" />;
}

const QrScanner = dynamic(() => Promise.resolve(Scanner), {
  ssr: false,
  loading: () => <div className="scanner-placeholder">Camera scanner loading…</div>
});

type RecordResult = { total: number; entry: Array<{ resource: { resourceType?: string } }> };
type IdentityResult = { verified: boolean; issuer: string; subject_ref: string; expires_at: number; envelope?: { ciphertext: string; nonce: string } };

function IconTile({ children, color = "blue" }: { children: ReactNode; color?: "blue" | "violet" | "green" }) {
  return <div className={`icon-tile ${color}`}>{children}</div>;
}

function Login({ onLogin }: { onLogin: (token: string) => void }) {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  async function submit(event: FormEvent) {
    event.preventDefault();
    setBusy(true);
    setError("");
    try {
      onLogin(await signIn(username, password));
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Sign-in failed");
    } finally {
      setBusy(false);
    }
  }

  return (
    <main className="login-shell">
      <div className="login-card">
        <div className="brand-mark"><Activity size={21} /></div>
        <p className="eyebrow">MEDICARD SECURE WORKSPACE</p>
        <h1>Clinical coordination,<br /><span>connected securely.</span></h1>
        <p className="muted">Sign in with an account provisioned by your MediCard administrator.</p>
        <form className="login-form" onSubmit={submit}>
          <label>Account<input autoComplete="username" value={username} onChange={(event) => setUsername(event.target.value)} required /></label>
          <label>Password<input type="password" autoComplete="current-password" value={password} onChange={(event) => setPassword(event.target.value)} required /></label>
          {error && <p className="error-message" role="alert">{error}</p>}
          <button className="primary-button full-width" disabled={busy}>{busy ? "Verifying…" : "Sign in securely"}<ArrowUpRight size={17} /></button>
        </form>
        <div className="login-foot"><LockKeyhole size={14} /> Short-lived access token · Protected session</div>
      </div>
      <div className="login-orbit orbit-one" /><div className="login-orbit orbit-two" />
    </main>
  );
}

export default function Home() {
  const [token, setToken] = useState("");
  const [patientId, setPatientId] = useState("");
  const [records, setRecords] = useState<RecordResult | null>(null);
  const [route, setRoute] = useState<RoutingResult | null>(null);
  const [identityInput, setIdentityInput] = useState("");
  const [identity, setIdentity] = useState<IdentityResult | null>(null);
  const [qrEnvelope, setQrEnvelope] = useState("");
  const [routeFlags, setRouteFlags] = useState({ red_flag: false, urgent_review: false, routine_review: true });
  const [landmarks, setLandmarks] = useState("");
  const [scannerOpen, setScannerOpen] = useState(false);
  const [busy, setBusy] = useState("");
  const [error, setError] = useState("");

  if (!token) return <Login onLogin={setToken} />;

  async function runAction(action: string, operation: () => Promise<void>) {
    setBusy(action);
    setError("");
    try {
      await operation();
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "The request failed");
    } finally {
      setBusy("");
    }
  }

  function lookup(event: FormEvent) {
    event.preventDefault();
    void runAction("records", async () => {
      const result = await apiRequest<RecordResult>(`/clinical/records/${encodeURIComponent(patientId)}`, token, undefined, "GET");
      setRecords(result);
    });
  }

  function routeCase(event: FormEvent) {
    event.preventDefault();
    void runAction("routing", async () => {
      const body: Record<string, unknown> = { ...routeFlags };
      if (landmarks.trim()) body.mobility_observations = JSON.parse(landmarks);
      setRoute(await apiRequest<RoutingResult>("/clinical/route", token, body));
    });
  }

  function verifyIdentity(envelopeText = identityInput) {
    void runAction("identity", async () => {
      const envelope = JSON.parse(envelopeText);
      const result = await apiRequest<IdentityResult>("/identity/verify", token, { envelope });
      setIdentity(result);
      setQrEnvelope(JSON.stringify(envelope));
      setIdentityInput(envelopeText);
    });
  }

  function createIdentityQr() {
    void runAction("identity", async () => {
      const credential = JSON.parse(identityInput);
      const result = await apiRequest<IdentityResult>("/identity/qr", token, { credential });
      if (!result.envelope) throw new Error("The verified credential did not produce an encrypted QR envelope");
      const serialized = JSON.stringify(result.envelope);
      setQrEnvelope(serialized);
      setIdentity(result);
      setIdentityInput(serialized);
    });
  }

  function signOut() {
    setToken("");
    setPatientId("");
    setRecords(null);
    setIdentityInput("");
    setIdentity(null);
    setQrEnvelope("");
    setRoute(null);
    setLandmarks("");
    setError("");
  }

  return (
    <main className="app-shell">
      <aside className="sidebar">
        <a className="brand" href="#"><span className="brand-mark"><Activity size={20} /></span><span>MediCard<small>CARE NETWORK</small></span></a>
        <div className="workspace-label">WORKSPACE</div>
        <nav className="nav-links" aria-label="Main navigation">
          <a className="nav-link active" href="#overview"><Activity size={17} />Overview</a>
          <a className="nav-link" href="#records"><ClipboardList size={17} />Clinical records</a>
          <a className="nav-link" href="#identity"><Fingerprint size={17} />Sovereign identity</a>
          <a className="nav-link" href="#routing"><Waypoints size={17} />Clinical routing</a>
        </nav>
        <div className="sidebar-bottom">
          <div className="security-status"><span className="status-dot" /><span><b>Secure session</b><small>Token held in memory</small></span></div>
          <button className="nav-link logout" onClick={signOut}><LogOut size={17} />Sign out</button>
          <div className="sidebar-help"><CircleHelp size={16} /><span>Need assistance?<small>Contact your administrator</small></span></div>
        </div>
      </aside>

      <section className="main-content">
        <header className="topbar">
          <div className="breadcrumbs">Workspace <span>/</span> <b>Overview</b></div>
          <div className="topbar-actions"><span className="environment-pill"><span />Protected environment</span><button aria-label="Notifications" className="icon-button"><Bell size={18} /></button><div className="avatar">MC</div></div>
        </header>

        <div className="content-wrap" id="overview">
          <div className="welcome-row">
            <div><p className="eyebrow">THURSDAY, NOVEMBER 12</p><h1>Clinical workspace</h1><p className="muted">A secure view of connected care workflows.</p></div>
            <div className="date-chip"><span className="live-dot" /> Systems operational</div>
          </div>

          <div className="notice-banner"><ShieldCheck size={18} /><p><b>Clinician-reviewed decision support.</b> Routing is administrative only and does not provide a diagnosis or treatment recommendation.</p><BadgeCheck size={17} className="notice-check" /></div>

          {error && <div className="error-banner" role="alert">{error}</div>}

          <div className="overview-grid">
            <article className="metric-card"><div className="metric-top"><IconTile><UsersRound size={18} /></IconTile><span className="metric-tag">FHIR R4</span></div><div className="metric-value">Connected</div><div className="metric-caption">Interoperable record exchange</div><div className="metric-foot"><span className="tiny-check">✓</span> Bundle validation enabled</div></article>
            <article className="metric-card"><div className="metric-top"><IconTile color="violet"><Fingerprint size={18} /></IconTile><span className="metric-tag">SSI</span></div><div className="metric-value">Patient-led</div><div className="metric-caption">Issuer-signed credentials</div><div className="metric-foot"><span className="tiny-check">✓</span> Encrypted QR envelopes</div></article>
            <article className="metric-card"><div className="metric-top"><IconTile color="green"><Waypoints size={18} /></IconTile><span className="metric-tag">ROUTING</span></div><div className="metric-value">Explainable</div><div className="metric-caption">Clinician review queues</div><div className="metric-foot"><span className="tiny-check">✓</span> No automated diagnosis</div></article>
          </div>

          <div className="section-heading"><div><p className="eyebrow">CARE OPERATIONS</p><h2>Connected workflows</h2></div><span className="section-note"><LockKeyhole size={14} /> Patient data is encrypted at rest</span></div>
          <div className="workspace-grid">
            <article className="panel records-panel" id="records">
              <div className="panel-heading"><IconTile><ClipboardList size={18} /></IconTile><div><h3>Clinical records</h3><p>Retrieve an encrypted FHIR record by patient resource ID.</p></div></div>
              <form className="inline-form" onSubmit={lookup}>
                <label className="sr-only" htmlFor="patient-id">FHIR Patient resource ID</label>
                <input id="patient-id" placeholder="Enter FHIR Patient resource ID" value={patientId} onChange={(event) => setPatientId(event.target.value)} required maxLength={128} />
                <button className="primary-button" disabled={busy === "records"}>{busy === "records" ? "Searching…" : "Search"}<ArrowUpRight size={15} /></button>
              </form>
              {records && <div className="result-box"><div className="result-title"><span className="result-icon"><ClipboardList size={15} /></span><b>{records.total} record bundle{records.total === 1 ? "" : "s"} found</b></div><p>{records.entry.map((item) => item.resource.resourceType ?? "FHIR resource").join(" · ") || "No resources returned"}</p><small>Protected resource content is not rendered in this dashboard.</small></div>}
              <div className="panel-foot"><LockKeyhole size={14} /> Access requires the <code>records:read</code> scope</div>
            </article>

            <article className="panel identity-panel" id="identity">
              <div className="panel-heading"><IconTile color="violet"><Fingerprint size={18} /></IconTile><div><h3>Sovereign identity</h3><p>Verify a trusted issuer's encrypted QR credential.</p></div></div>
              <label className="field-label" htmlFor="credential-envelope">Issuer-signed credential JSON or encrypted QR envelope</label>
              <textarea id="credential-envelope" className="credential-input" placeholder='{"issuer":"…","subject":"…","expires_at":…,"signature":"…"}' value={identityInput} onChange={(event) => setIdentityInput(event.target.value)} />
              <div className="identity-actions"><button className="secondary-button" onClick={createIdentityQr} disabled={!identityInput.trim() || busy === "identity"}><Fingerprint size={15} />Create encrypted QR</button><button className="secondary-button" onClick={() => verifyIdentity()} disabled={!identityInput.trim() || busy === "identity"}><ScanLine size={15} />Verify envelope</button><button className="text-button" onClick={() => { setIdentityInput(""); setQrEnvelope(""); setIdentity(null); }}>Clear</button></div>
              {qrEnvelope && <div className="qr-preview"><QRCodeSVG value={qrEnvelope} size={86} bgColor="#ffffff" fgColor="#08111f" level="M" /><span><b>Encrypted credential QR</b><small>Issuer signature verified · Scan to verify again</small></span></div>}
              <details className="scanner-details" onToggle={(event) => setScannerOpen(event.currentTarget.open)}><summary><ScanLine size={14} /> Scan a QR with this device</summary>{scannerOpen && <QrScanner onScan={(value) => verifyIdentity(value)} onError={setError} />}</details>
              {identity && <div className="verified-result"><BadgeCheck size={17} /><span><b>Credential verified</b><small>Issuer: {identity.issuer} · Expires {new Date(identity.expires_at * 1000).toLocaleString()}</small></span></div>}
              <div className="panel-foot"><ShieldCheck size={14} /> Signature, issuer, and expiry are checked server-side</div>
            </article>

            <article className="panel routing-panel" id="routing">
              <div className="panel-heading"><IconTile color="green"><Stethoscope size={18} /></IconTile><div><h3>Clinical review routing</h3><p>Send explicit clinician-entered flags to the review workflow.</p></div></div>
              <form onSubmit={routeCase}>
                <div className="flag-list">
                  <label className="check-row"><input type="checkbox" checked={routeFlags.red_flag} onChange={(event) => setRouteFlags({ ...routeFlags, red_flag: event.target.checked })} /><span><b>Immediate review flag</b><small>Submitted by a clinician; not inferred by AI.</small></span></label>
                  <label className="check-row"><input type="checkbox" checked={routeFlags.urgent_review} onChange={(event) => setRouteFlags({ ...routeFlags, urgent_review: event.target.checked })} /><span><b>Urgent review requested</b><small>Prioritizes a clinician review queue.</small></span></label>
                  <label className="check-row"><input type="checkbox" checked={routeFlags.routine_review} onChange={(event) => setRouteFlags({ ...routeFlags, routine_review: event.target.checked })} /><span><b>Routine review requested</b><small>Routes for standard clinician follow-up.</small></span></label>
                </div>
                <label className="field-label" htmlFor="landmarks">Optional normalized movement landmarks (JSON)</label>
                <textarea id="landmarks" className="landmark-input" placeholder='[{"x":0.2,"y":0.3},{"x":0.5,"y":0.4},{"x":0.8,"y":0.2}]' value={landmarks} onChange={(event) => setLandmarks(event.target.value)} />
                <button className="primary-button route-button" disabled={busy === "routing"}>{busy === "routing" ? "Routing…" : "Create review route"}<ArrowUpRight size={15} /></button>
              </form>
              {route && <div className={`routing-result ${route.priority}`}><div className="routing-result-top"><span><span className="live-dot" />{route.priority} priority</span><b>{route.route.replaceAll("_", " ")}</b></div><p>{route.reasons.join(", ").replaceAll("_", " ")}</p>{route.biomechanics && <small>Geometry only: {route.biomechanics.landmark_count} landmarks · path length {route.biomechanics.normalized_path_length}</small>}<div className="result-disclaimer">No diagnosis generated · clinician review required</div></div>}
              <div className="panel-foot"><Activity size={14} /> Transparent rules · no trained diagnostic model</div>
            </article>
          </div>
          <footer className="page-footer"><span>MEDICARD · SECURE CARE COORDINATION</span><span>For authorized clinical operations only</span></footer>
        </div>
      </section>
    </main>
  );
}
