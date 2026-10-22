// A made-up screen with the faults the data audit is built to find. Do not copy it.
const SAMPLE = [
  {uid: "LMP-0101", text: "The lamp shall dim to the saved level within 3 seconds of power-up.", owner: "Eli", status: "approved"},
  {uid: "LMP-0102", text: "The panel shall show the lamp temperature when it is above 70 degrees.", owner: "Fay", status: "open"}
];

async function load() {
  let rows;
  try {
    const r = await fetch("/api/requirements");
    if (!r.ok) throw new Error("status " + r.status);
    rows = await r.json();
    localStorage.setItem("rows", JSON.stringify(rows));       // a copy kept for later, never labelled as a copy
  } catch (e) {
    const kept = localStorage.getItem("rows");
    rows = kept ? JSON.parse(kept) : SAMPLE;                  // fault: a sample shown when the source fails
  }
  const tbody = document.querySelector("#rows tbody");
  for (const r of rows) {
    const tr = document.createElement("tr");
    for (const v of [r.uid, r.text, r.owner, r.owner]) {      // fault: the Status column shows the owner
      const td = document.createElement("td");
      td.textContent = v;
      tr.appendChild(td);
    }
    tbody.appendChild(tr);
  }
  fetch("/api/visit", {method: "POST", body: "{}"}).catch(() => {});   // a write the audit must refuse
}
load();
