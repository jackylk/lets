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
    const activeItem = seed.taskItems.find(
      (i) =>
        i.status === "active" &&
        seed.taskTrees.find((t) => t.id === i.task_tree_id)?.topic_id === topicId,
    );
    const lastNudge = seed.driftNudges
      .filter((n) => n.topic_id === topicId)
      .sort((a, b) => b.id - a.id)[0];
    const lastNudgeMsg = lastNudge
      ? seed.messages.find((m) => m.id === lastNudge.nudge_message_id)
      : null;
    const messagesAfterNudge = lastNudge
      ? messages.filter((m) => m.id > lastNudge.nudge_message_id).length
      : messages.length;
    return HttpResponse.json({
      messages,
      drift_context: {
        // Topic mode is not part of TopicDTO yet on the frontend; mock as
        // "actionable" for topic 1 to exercise the drift UI in dev.
        topic_mode: topicId === 1 ? "actionable" : "exploratory",
        active_task: activeItem
          ? { id: activeItem.id, title: activeItem.title }
          : null,
        last_nudge_at: lastNudgeMsg?.created_at ?? null,
        last_nudge_message_id: lastNudge?.nudge_message_id ?? null,
        last_nudge_resolved_by: lastNudge?.resolved_by ?? null,
        messages_since_last_nudge: messagesAfterNudge,
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

  http.get("/api/topics/:id/task-tree", ({ params }) => {
    const topicId = Number(params.id);
    const tree = seed.taskTrees.find((t) => t.topic_id === topicId) ?? null;
    const items = tree ? seed.taskItems.filter((i) => i.task_tree_id === tree.id) : [];
    return HttpResponse.json({ tree, items });
  }),

  http.post("/api/topics/:id/task-tree", async ({ params, request }) => {
    const topicId = Number(params.id);
    const body = (await request.json()) as { proposal_message_id: number };
    const proposal = seed.messages.find((m) => m.id === body.proposal_message_id);
    if (!proposal || proposal.type !== "task_tree_proposal") {
      return new HttpResponse(JSON.stringify({ detail: "proposal not found" }), {
        status: 400,
      });
    }
    let tree = seed.taskTrees.find((t) => t.topic_id === topicId);
    if (!tree) {
      tree = {
        id: seed.taskTrees.length + 1,
        topic_id: topicId, goal_artifact_id: null, goal_spec_text: null,
        version: 1,
        approved_at: new Date().toISOString(),
        approved_by_human_id: 1,
        proposal_message_id: body.proposal_message_id,
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString(),
      };
      seed.taskTrees.push(tree);
    } else {
      tree.version += 1;
      tree.proposal_message_id = body.proposal_message_id;
      tree.updated_at = new Date().toISOString();
    }
    seed.taskItems = seed.taskItems.filter((i) => i.task_tree_id !== tree!.id);
    const meta = (proposal.metadata ?? {}) as { items?: Array<{title:string;parent_index?:number}> };
    const propItems = meta.items ?? [];
    const newIds: number[] = [];
    for (let i = 0; i < propItems.length; i++) {
      const id = seed.taskItems.length + i + 100;
      newIds.push(id);
      seed.taskItems.push({
        id, task_tree_id: tree.id, parent_item_id: null,
        title: propItems[i]!.title,
        owner_human_id: null, owner_agent_instance_id: null,
        status: "pending", position: i,
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString(),
      });
    }
    for (let i = 0; i < propItems.length; i++) {
      const idx = propItems[i]!.parent_index;
      if (idx !== undefined && idx >= 0 && idx < newIds.length) {
        const item = seed.taskItems.find((it) => it.id === newIds[i]);
        if (item) item.parent_item_id = newIds[idx] ?? null;
      }
    }
    const items = seed.taskItems.filter((it) => it.task_tree_id === tree.id);
    return HttpResponse.json({ tree, items }, { status: 201 });
  }),

  http.post("/api/topics/:id/goal", async ({ params, request }) => {
    const topicId = Number(params.id);
    const body = (await request.json()) as {
      goal_proposal_message_id?: number;
      spec_text?: string;
      artifact_id?: number | null;
    };
    let specText = body.spec_text ?? null;
    let artifactId = body.artifact_id ?? null;
    if (body.goal_proposal_message_id) {
      const prop = seed.messages.find((m) => m.id === body.goal_proposal_message_id);
      if (prop) {
        const meta = (prop.metadata ?? {}) as { spec_text?: string; artifact_id?: number };
        specText = specText ?? meta.spec_text ?? prop.body;
        artifactId = artifactId ?? meta.artifact_id ?? null;
      }
    }
    let tree = seed.taskTrees.find((t) => t.topic_id === topicId);
    if (!tree) {
      tree = {
        id: seed.taskTrees.length + 1, topic_id: topicId,
        goal_artifact_id: artifactId, goal_spec_text: specText,
        version: 1, approved_at: new Date().toISOString(),
        approved_by_human_id: 1, proposal_message_id: body.goal_proposal_message_id ?? null,
        created_at: new Date().toISOString(), updated_at: new Date().toISOString(),
      };
      seed.taskTrees.push(tree);
    } else {
      tree.goal_artifact_id = artifactId;
      tree.goal_spec_text = specText;
      tree.updated_at = new Date().toISOString();
    }
    const items = seed.taskItems.filter((it) => it.task_tree_id === tree!.id);
    return HttpResponse.json({ tree, items }, { status: 201 });
  }),

  http.post("/api/task-items", async ({ request }) => {
    const body = (await request.json()) as {
      task_tree_id: number; title: string; parent_item_id?: number | null;
      owner_human_id?: number | null; owner_agent_instance_id?: number | null;
    };
    const siblings = seed.taskItems.filter(
      (i) => i.task_tree_id === body.task_tree_id && i.parent_item_id === (body.parent_item_id ?? null),
    );
    const item = {
      id: seed.taskItems.length + 1000,
      task_tree_id: body.task_tree_id,
      parent_item_id: body.parent_item_id ?? null,
      title: body.title,
      owner_human_id: body.owner_human_id ?? null,
      owner_agent_instance_id: body.owner_agent_instance_id ?? null,
      status: "pending" as const,
      position: siblings.length,
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
    };
    seed.taskItems.push(item);
    return HttpResponse.json(item, { status: 201 });
  }),

  http.patch("/api/task-items/:id", async ({ params, request }) => {
    const id = Number(params.id);
    const body = (await request.json()) as { status?: "pending"|"active"|"done"; title?: string };
    const item = seed.taskItems.find((i) => i.id === id);
    if (!item) return new HttpResponse(null, { status: 404 });
    if (body.status) item.status = body.status;
    if (body.title) item.title = body.title;
    item.updated_at = new Date().toISOString();
    return HttpResponse.json(item);
  }),

  http.post("/api/nudges/:id/resolve", async ({ params, request }) => {
    const id = Number(params.id);
    const body = (await request.json()) as { resolved_by: "moved_to_topic"|"returned"|"dismissed"; spinoff_title?: string };
    const nudge = seed.driftNudges.find((n) => n.id === id);
    if (!nudge) return new HttpResponse(null, { status: 404 });
    nudge.resolved_by = body.resolved_by;
    nudge.resolved_at = new Date().toISOString();
    if (body.resolved_by === "moved_to_topic") {
      if (!body.spinoff_title) {
        return new HttpResponse(JSON.stringify({ detail: "spinoff_title required" }), { status: 400 });
      }
      const newTopicId = seed.topics.length + 1;
      seed.topics.push({
        id: newTopicId,
        slug: `spinoff-${newTopicId}`,
        title: body.spinoff_title,
        project_id: seed.topics.find((t) => t.id === nudge.topic_id)?.project_id ?? null,
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString(),
      });
      nudge.resolved_to_topic_id = newTopicId;
    }
    return HttpResponse.json({
      id: nudge.id, topic_id: nudge.topic_id,
      resolved_by: nudge.resolved_by, resolved_to_topic_id: nudge.resolved_to_topic_id,
      resolved_at: nudge.resolved_at,
    });
  }),
];
