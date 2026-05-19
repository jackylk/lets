import { http, HttpResponse } from "msw";
import { makeSeed, type SeedState } from "./seed";
import type { MessageDTO, PostMessageInput, IdentityDTO, TokenRowDTO } from "../api/types";

type TokenRow = TokenRowDTO;

let seed: SeedState = makeSeed();

export function resetFixtures() { seed = makeSeed(); }

export const handlers = [
  http.get("/api/identity/me", ({ request }) => {
    const human = request.headers.get("X-Lets-Human") ?? "Neo";
    const role = request.headers.get("X-Lets-Agent-Role");
    const device = request.headers.get("X-Lets-Device");
    const humanRow =
      seed.humans.find((h) => h.name === human) ??
      (() => {
        const row = { id: seed.humans.length + 1, name: human };
        seed.humans.push(row);
        return row;
      })();
    const out: IdentityDTO = { human: humanRow };
    if (role && device) {
      const instance =
        seed.agentInstances.find(
          (a) => a.role === role && a.device_label === device && a.human_id === humanRow.id,
        ) ??
        (() => {
          const row = {
            id: 100 + seed.agentInstances.length,
            role, device_label: device, human_id: humanRow.id,
          };
          seed.agentInstances.push(row);
          return row;
        })();
      out.agent_instance = {
        id: instance.id, role: instance.role, device_label: instance.device_label,
      };
    }
    return HttpResponse.json(out);
  }),

  http.get("/api/topics", () => HttpResponse.json(seed.topics)),

  http.get("/api/topics/:id/messages", ({ params, request }) => {
    const url = new URL(request.url);
    const types = url.searchParams.getAll("type");
    const topicId = Number(params.id);
    let messages = seed.messages.filter((m) => m.topic_id === topicId);
    if (types.length) messages = messages.filter((m) => types.includes(m.type));
    return HttpResponse.json({
      messages,
      drift_context: {
        topic_mode: "exploratory",
        active_task: null,
        last_nudge_at: null,
        last_nudge_message_id: null,
        last_nudge_resolved_by: null,
        messages_since_last_nudge: messages.length,
      },
    });
  }),

  http.post("/api/messages", async ({ request }) => {
    const body = (await request.json()) as PostMessageInput;
    const msg: MessageDTO = {
      id: seed.messages.length + 100,
      topic_id: body.topic_id,
      type: body.type,
      actor_type: body.actor_type,
      actor_id: body.actor_id,
      body: body.body,
      metadata: body.metadata ?? {},
      ref_event_id: body.ref_event_id ?? null,
      created_at: new Date().toISOString(),
    };
    seed.messages.push(msg);
    return HttpResponse.json(msg, { status: 201 });
  }),

  http.get("/api/tokens", () => {
    return HttpResponse.json(
      (seed as unknown as { fixtureTokens?: TokenRow[] }).fixtureTokens ?? [],
    );
  }),

  http.post("/api/tokens", async ({ request }) => {
    const body = (await request.json()) as { label: string; role: string; device_label: string };
    const slot = seed as unknown as { fixtureTokens?: TokenRow[] };
    const tokens = (slot.fixtureTokens ??= []);
    const id = tokens.length + 1;
    const row: TokenRow = {
      id, label: body.label, human_id: 1,
      agent_instance_id: 100 + id,
      agent_instance: { id: 100 + id, role: body.role, device_label: body.device_label },
      created_at: new Date().toISOString(),
      last_used_at: null, revoked_at: null,
    };
    tokens.push(row);
    return HttpResponse.json(
      {
        id, value: `lets_${Math.random().toString(36).slice(2, 10)}`,
        label: body.label,
        agent_instance: { id: row.agent_instance_id, role: body.role, device_label: body.device_label },
      },
      { status: 201 },
    );
  }),

  http.delete("/api/tokens/:id", ({ params }) => {
    const slot = seed as unknown as { fixtureTokens?: TokenRow[] };
    const tokens = (slot.fixtureTokens ??= []);
    const t = tokens.find((x) => x.id === Number(params.id));
    if (t) t.revoked_at = new Date().toISOString();
    return new HttpResponse(null, { status: 204 });
  }),

  http.get("/auth/me", () =>
    HttpResponse.json({
      human: {
        id: 1, name: "Neo", github_login: "neo",
        avatar_url: "https://avatars.example/neo.png",
      },
    }),
  ),

  http.post("/auth/logout", () => new HttpResponse(null, { status: 204 })),

  http.get("/api/topics/:id/stream", () => {
    const stream = new ReadableStream({
      start(controller) {
        controller.enqueue(new TextEncoder().encode(": keepalive\n\n"));
        controller.close();
      },
    });
    return new HttpResponse(stream, {
      headers: { "Content-Type": "text/event-stream" },
    });
  }),
];
