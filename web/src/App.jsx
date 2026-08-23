import { useEffect, useMemo, useRef, useState } from "react";
import {
  cancelAction,
  confirmAction,
  getMe,
  getOrders,
  getPersonas,
  getPulse,
  getTickets,
  streamChat,
} from "./api";

const STARTERS = {
  "ACCT-001": [
    "Can I cancel ORD-1001 without a fee? Explain why.",
    "Can we cancel ORD-1002?",
  ],
  "ACCT-002": [
    "Can I cancel ORD-2001 without a fee?",
    "Pickup is late on ORD-2002 and the carrier accepted fault. Credit?",
  ],
  "ACCT-003": ["Can I cancel ORD-3001? Any fee?", "How do we change the billing contact?"],
  "ACCT-004": ["Can I cancel ORD-4001?", "We may have exposed an API key. What should we do?"],
  staff: [
    "What needs attention right now?",
    "TKT-505 — have we breached SLA?",
    "Can LumenWorks cancel ORD-2001 without a fee?",
    "Beacon wants to change the billing contact.",
  ],
};

const TOOL_LINE = {
  assess_cancellation: "Checking cancellation rules…",
  assess_failed_pickup_credit: "Checking service credit…",
  classify_severity_and_sla: "Checking SLA…",
  get_ops_pulse: "Scanning open issues…",
  search_documents: "Reading policy…",
  get_order: "Looking up the shipment…",
  get_account: "Looking up the account…",
  get_ticket: "Looking up the ticket…",
  propose_escalation: "Preparing an escalation…",
  propose_task: "Preparing a task…",
  propose_ticket_update: "Preparing a ticket update…",
};

function statusLine(tools) {
  const last = [...tools].reverse().find((t) => t.state === "running") || tools[tools.length - 1];
  if (!last) return "Working…";
  return TOOL_LINE[last.name] || "Working…";
}

export default function App() {
  const [personas, setPersonas] = useState([]);
  const [persona, setPersona] = useState(null);
  const [me, setMe] = useState(null);
  const [tab, setTab] = useState("chat");
  const [orders, setOrders] = useState([]);
  const [tickets, setTickets] = useState([]);
  const [pulse, setPulse] = useState([]);
  const [messages, setMessages] = useState([]);
  const [draft, setDraft] = useState("");
  const [busy, setBusy] = useState(false);
  const [tools, setTools] = useState([]);
  const [proposal, setProposal] = useState(null);
  const [error, setError] = useState("");
  const logRef = useRef(null);

  useEffect(() => {
    getPersonas().then((d) => {
      setPersonas(d.personas);
      setPersona(d.personas[0]);
    });
  }, []);

  useEffect(() => {
    if (!persona) return;
    setMessages([]);
    setTools([]);
    setProposal(null);
    setError("");
    getMe(persona).then(setMe);
    getOrders(persona).then((d) => setOrders(d.orders || []));
    getTickets(persona).then((d) => setTickets(d.tickets || []));
    if (persona.kind === "staff") getPulse(persona).then((d) => setPulse(d.issues || []));
    else setPulse([]);
  }, [persona]);

  useEffect(() => {
    logRef.current?.scrollTo(0, logRef.current.scrollHeight);
  }, [messages, tools]);

  const staff = persona?.kind === "staff";
  const starters = useMemo(() => {
    if (staff) return STARTERS.staff;
    return STARTERS[persona?.account_id] || [];
  }, [staff, persona]);

  async function send(text) {
    const content = (text ?? draft).trim();
    if (!content || busy || !persona) return;
    const next = [...messages, { role: "user", content }];
    setMessages(next);
    setDraft("");
    setBusy(true);
    setError("");
    setTools([]);
    let final = "";
    let sources = [];
    try {
      for await (const ev of streamChat(persona, next)) {
        if (ev.event === "tool_start") setTools((t) => [...t, { name: ev.data.name, state: "running" }]);
        if (ev.event === "tool_end") {
          setTools((t) => t.map((x) => (x.name === ev.data.name && x.state === "running" ? { ...x, state: "done" } : x)));
          const result = ev.data.result || {};
          const extra = (result.policy_basis || []).filter(Boolean);
          if (extra.length) {
            sources = [...new Set([...sources, ...extra])];
          }
        }
        if (ev.event === "proposal") setProposal(ev.data);
        if (ev.event === "final") final = ev.data.text;
        if (ev.event === "error") setError(ev.data.message);
      }
      if (final) {
        setMessages([...next, { role: "assistant", content: final, sources }]);
      }
    } catch (e) {
      setError(String(e));
    } finally {
      setBusy(false);
    }
  }

  async function onConfirm() {
    if (!proposal) return;
    const out = await confirmAction(persona, proposal.proposal_id);
    setProposal(null);
    setMessages((m) => [...m, { role: "assistant", content: `Confirmed. ${JSON.stringify(out)}` }]);
  }

  async function onCancel() {
    if (!proposal) return;
    await cancelAction(persona, proposal.proposal_id);
    setProposal(null);
  }

  return (
    <div className="shell">
      <aside>
        <p className="kicker">ParcelPilot</p>
        <h1>Support Copilot</h1>
        <p className="clock">Snapshot 16 Aug 2026, 11:00 IST</p>
        <label>
          Acting as
          <select
            value={persona?.id || ""}
            onChange={(e) => setPersona(personas.find((p) => p.id === e.target.value))}
          >
            {personas.map((p) => (
              <option key={p.id} value={p.id}>
                {p.label}
              </option>
            ))}
          </select>
        </label>
        {me?.account && (
          <div className="chip">
            {me.account.account_name}
            <span>{me.account.plan}</span>
          </div>
        )}
        {staff && (
          <div className="tabs">
            <button className={tab === "chat" ? "on" : ""} onClick={() => setTab("chat")}>
              Chat
            </button>
            <button className={tab === "pulse" ? "on" : ""} onClick={() => setTab("pulse")}>
              Ops Pulse
            </button>
          </div>
        )}
        <h2>Visible records</h2>
        <ul className="records">
          {orders.map((o) => (
            <li key={o.order_id}>
              <button onClick={() => send(`Look up ${o.order_id} and tell me the cancellation and credit position.`)}>
                {o.order_id} · {o.status}
              </button>
            </li>
          ))}
        </ul>
        <ul className="records">
          {tickets
            .filter((t) => t.status === "open")
            .map((t) => (
              <li key={t.ticket_id}>
                <button onClick={() => send(`Investigate ${t.ticket_id}: ${t.subject}`)}>
                  {t.ticket_id} · {t.subject}
                </button>
              </li>
            ))}
        </ul>
      </aside>

      <main>
        {staff && tab === "pulse" ? (
          <Pulse
            issues={pulse}
            onAsk={(q) => {
              setTab("chat");
              send(q);
            }}
          />
        ) : (
          <>
            <div className="log" ref={logRef}>
              {messages.length === 0 && (
                <div className="empty">
                  <p>Starters for this login. Left rail lists the orders you can actually see.</p>
                  {starters.map((s) => (
                    <button key={s} className="ghost" onClick={() => send(s)}>
                      {s}
                    </button>
                  ))}
                </div>
              )}
              {messages.map((m, i) => (
                <article key={i} className={m.role}>
                  <span>{m.role === "user" ? "You" : "Answer"}</span>
                  <pre>{m.content}</pre>
                  {m.sources?.length > 0 && staff && (
                    <p className="cites">
                      <em>Sources</em>
                      {m.sources.map((c) => (
                        <span key={c}>{c.replace(/\.pdf$/i, "").replace(/_/g, " ")}</span>
                      ))}
                    </p>
                  )}
                </article>
              ))}
              {busy && <p className="working">{statusLine(tools)}</p>}
              {proposal && (
                <div className="confirm">
                  <p>
                    {proposal.action_type === "task"
                      ? "This will create a follow-up task."
                      : proposal.action_type === "escalation"
                        ? "This will create an escalation."
                        : proposal.action_type === "ticket_update"
                          ? "This will update the ticket."
                          : `This will run ${proposal.action_type}.`}{" "}
                    Nothing is written until you confirm.
                  </p>
                  <pre>{JSON.stringify(proposal.payload, null, 2)}</pre>
                  <button onClick={onConfirm}>Confirm</button>
                  <button className="ghost" onClick={onCancel}>
                    Cancel
                  </button>
                </div>
              )}
              {error && <p className="err">{error}</p>}
            </div>
            <form
              onSubmit={(e) => {
                e.preventDefault();
                send();
              }}
            >
              <input
                value={draft}
                disabled={busy}
                onChange={(e) => setDraft(e.target.value)}
                placeholder={busy ? "Working…" : "Ask about an order, ticket, credit, or SLA"}
              />
              <button disabled={busy || !draft.trim()}>Send</button>
            </form>
          </>
        )}
      </main>
    </div>
  );
}

function Pulse({ issues, onAsk }) {
  if (!issues.length) return <p className="empty">No pulse issues. Check staff role headers.</p>;
  return (
    <div className="pulse">
      <h2>Needs attention</h2>
      {issues.map((i) => (
        <article key={i.id} data-sev={i.severity}>
          <header>
            <b>{i.severity}</b> {i.account_name}
          </header>
          <p>{i.title}</p>
          <p className="meta">{i.evidence_ids.join(" · ")}</p>
          <button className="ghost" onClick={() => onAsk(`Investigate: ${i.title}. Evidence: ${i.evidence_ids.join(", ")}`)}>
            Open in chat
          </button>
        </article>
      ))}
    </div>
  );
}
