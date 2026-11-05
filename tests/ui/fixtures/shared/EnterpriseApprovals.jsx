"use client";
import { useMemo, useState } from "react";
import "./enterprise.css";

const INITIAL = [
  { id: "INV-1042", vendor: "Nusa Supply", amount: 18750000, age: "3d 4h", status: "pending", risk: true },
  { id: "INV-1043", vendor: "Sinar Logistics", amount: 9200000, age: "1d 2h", status: "pending", risk: false },
  { id: "INV-1044", vendor: "Karya Digital", amount: 12400000, age: "5d 1h", status: "pending", risk: true },
  { id: "INV-1045", vendor: "Mitra Energi", amount: 8400000, age: "2h", status: "pending", risk: false },
  { id: "INV-1039", vendor: "Nusa Supply", amount: 6100000, age: "—", status: "approved", risk: false },
  { id: "INV-1038", vendor: "Sinar Logistics", amount: 3700000, age: "—", status: "rejected", risk: false },
];

function money(value) { return "Rp " + value.toLocaleString("id-ID"); }

export default function EnterpriseApprovals() {
  const [records, setRecords] = useState(INITIAL);
  const [selected, setSelected] = useState(new Set());
  const [search, setSearch] = useState("");
  const [status, setStatus] = useState("");
  const [mode, setMode] = useState("ready");
  const [notice, setNotice] = useState("Ready");

  const visible = useMemo(() => records.filter((record) => {
    const text = (record.id + " " + record.vendor).toLowerCase();
    return (!search || text.includes(search.toLowerCase())) && (!status || record.status === status);
  }), [records, search, status]);

  function toggle(id) {
    const next = new Set(selected);
    next.has(id) ? next.delete(id) : next.add(id);
    setSelected(next);
  }
  function approve(record) {
    setRecords((items) => items.map((item) => item.id === record.id ? { ...item, status: "approved" } : item));
    setNotice(record.id + " approved.");
  }
  function bulk(nextStatus) {
    const count = selected.size;
    setRecords((items) => items.map((item) => selected.has(item.id) ? { ...item, status: nextStatus } : item));
    setSelected(new Set());
    setNotice(count + " records " + nextStatus + ".");
  }
  function reset() {
    setMode("ready"); setSearch(""); setStatus(""); setSelected(new Set()); setNotice("Ready");
  }

  return (
    <main className="ea-shell">
      <header className="ea-header">
        <div><h1>Approvals workspace</h1><p className="ea-muted">Review payment exceptions before they reach the ledger.</p></div>
        <div className="ea-muted">As of 14:00 WIB</div>
      </header>
      <section className="ea-stats" aria-label="Approval summary">
        <div className="ea-card ea-stat"><span>Pending</span><strong>{records.filter((r) => r.status === "pending").length}</strong></div>
        <div className="ea-card ea-stat"><span>Amount at risk</span><strong>{money(records.filter((r) => r.status === "pending").reduce((sum, r) => sum + r.amount, 0))}</strong></div>
        <div className="ea-card ea-stat"><span>SLA breaches</span><strong>1</strong></div>
      </section>
      <section className="ea-card" aria-labelledby="ea-queue-title">
        <div className="ea-toolbar">
          <label>Search records<input type="search" value={search} onChange={(e) => setSearch(e.target.value)} placeholder="Invoice or vendor" /></label>
          <label>Status<select value={status} onChange={(e) => setStatus(e.target.value)}><option value="">All statuses</option><option value="pending">Pending</option><option value="approved">Approved</option><option value="rejected">Rejected</option></select></label>
          <button type="button" onClick={() => { setSearch(""); setStatus(""); setNotice("Filters cleared."); }}>Clear filters</button>
          <button type="button" onClick={() => setMode("loading")}>Load loading state</button>
          <button type="button" onClick={() => setMode("empty")}>Load empty state</button>
          <button type="button" onClick={() => setMode("error")}>Load error state</button>
          <button type="button" className="ea-primary" onClick={reset}>Reset</button>
        </div>
        <div className="ea-sr" role="status" aria-live="polite">{notice}</div>
        {mode === "loading" && <div className="ea-state"><h2>Loading approvals…</h2><p className="ea-muted">Fetching the latest review queue.</p></div>}
        {mode === "empty" && <div className="ea-state"><h2>No approvals match</h2><p className="ea-muted">Clear the filters or wait for new exceptions.</p></div>}
        {mode === "error" && <div className="ea-state" role="alert"><h2>Approvals could not load</h2><p className="ea-muted">The queue service is unavailable. Retry or keep the last known view.</p><button type="button" onClick={() => setMode("ready")}>Retry</button></div>}
        {mode === "ready" && <>
          {visible.length === 0 ? <div className="ea-state"><h2>No approvals match</h2><p className="ea-muted">Clear the filters or wait for new exceptions.</p></div> : <div className="ea-table-wrap"><table className="ea-table" aria-describedby="ea-queue-title"><caption id="ea-queue-title">Pending payment exceptions</caption><thead><tr><th scope="col">Select</th><th scope="col">Invoice</th><th scope="col">Vendor</th><th scope="col" className="ea-num">Amount</th><th scope="col">Age</th><th scope="col">Status</th><th scope="col">Action</th></tr></thead><tbody>
            {visible.map((record) => <tr key={record.id} tabIndex={0} aria-selected={selected.has(record.id)}>
              <td data-label="Select"><input className="ea-check" type="checkbox" checked={selected.has(record.id)} onChange={() => toggle(record.id)} aria-label={"Select " + record.id} /></td>
              <td data-label="Invoice"><strong>{record.id}</strong>{record.risk ? <> <span className="ea-pill pending">Risk</span></> : null}</td>
              <td data-label="Vendor">{record.vendor}</td>
              <td data-label="Amount" className="ea-num">{money(record.amount)}</td>
              <td data-label="Age">{record.age}</td>
              <td data-label="Status"><span className={"ea-pill " + record.status}>{record.status}</span></td>
              <td data-label="Action"><button className="ea-approve" type="button" disabled={record.status !== "pending"} onClick={() => approve(record)}>Approve</button></td>
            </tr>)}
          </tbody></table></div>}
          {selected.size > 0 && <div className="ea-bulk"><span role="status">{selected.size} selected</span><div><button className="ea-primary" type="button" onClick={() => bulk("approved")}>Approve selected</button><button className="ea-danger" type="button" onClick={() => bulk("rejected")}>Reject selected</button></div></div>}
        </>}
      </section>
    </main>
  );
}
