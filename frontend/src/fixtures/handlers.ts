import { http, HttpResponse } from "msw";
import { makeSeed, type SeedState } from "./seed";
import type { MessageDTO, PostMessageInput, IdentityDTO } from "../api/types";

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
    return HttpResponse.json(messages);
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
];
