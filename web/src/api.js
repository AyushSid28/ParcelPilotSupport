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

function parseBlock(block) {
  const ev = (block.match(/^event: (.+)$/m) || [])[1];
  const dataLines = [...block.matchAll(/^data: (.*)$/gm)].map((m) => m[1]);
  if (!ev || !dataLines.length) return null;
  return { event: ev, data: JSON.parse(dataLines.join("")) };
}

export async function* streamChat(persona, messages) {
  const res = await fetch("/chat", {
    method: "POST",
    headers: headersFor(persona),
    body: JSON.stringify({ messages }),
  });
  if (!res.ok) {
    const text = await res.text();
    yield { event: "error", data: { message: text || res.statusText } };
    return;
  }
  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buf = "";
  while (true) {
    const { value, done } = await reader.read();
    buf += decoder.decode(value || new Uint8Array(), { stream: !done });
    if (done) {
      for (const block of buf.split("\n\n")) {
        const parsed = parseBlock(block);
        if (parsed) yield parsed;
      }
      break;
    }
    const parts = buf.split("\n\n");
    buf = parts.pop() || "";
    for (const block of parts) {
      const parsed = parseBlock(block);
      if (parsed) yield parsed;
    }
  }
}
