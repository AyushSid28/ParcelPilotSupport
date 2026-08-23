const headersFor = (persona) => {
  const h = { "Content-Type": "application/json", "X-Actor-Type": persona.kind };
  if (persona.account_id) h["X-Account-Id"] = persona.account_id;
  if (persona.staff_id) h["X-Staff-Id"] = persona.staff_id;
  if (persona.role) h["X-Staff-Role"] = persona.role;
  return h;
};

export async function getPersonas() {
  const res = await fetch("/personas");
  return res.json();
}

export async function getMe(persona) {
  const res = await fetch("/me", { headers: headersFor(persona) });
  return res.json();
}

export async function getOrders(persona) {
  const res = await fetch("/orders", { headers: headersFor(persona) });
  return res.json();
}

export async function getTickets(persona) {
  const res = await fetch("/tickets", { headers: headersFor(persona) });
  return res.json();
}

export async function getPulse(persona) {
  const res = await fetch("/ops/pulse", { headers: headersFor(persona) });
  return res.json();
}

export async function confirmAction(persona, id) {
  const res = await fetch(`/actions/${id}/confirm`, {
    method: "POST",
    headers: headersFor(persona),
  });
  return res.json();
}

export async function cancelAction(persona, id) {
  const res = await fetch(`/actions/${id}/cancel`, {
    method: "POST",
    headers: headersFor(persona),
  });
  return res.json();
}

export async function* streamChat(persona, messages) {
  const res = await fetch("/chat", {
    method: "POST",
    headers: headersFor(persona),
    body: JSON.stringify({ messages }),
  });
  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buf = "";
  while (true) {
    const { value, done } = await reader.read();
    if (done) break;
    buf += decoder.decode(value, { stream: true });
    const parts = buf.split("\n\n");
    buf = parts.pop() || "";
    for (const block of parts) {
      const ev = (block.match(/^event: (.+)$/m) || [])[1];
      const dataLine = (block.match(/^data: (.+)$/m) || [])[1];
      if (!ev || !dataLine) continue;
      yield { event: ev, data: JSON.parse(dataLine) };
    }
  }
}
