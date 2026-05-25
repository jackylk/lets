import { http, HttpResponse } from "msw";
import { makeSeed, type SeedState } from "./seed";
import type {
  AttachmentDTO,
  IdentityDTO,
  MessageDTO,
  PostMessageInput,
  TokenRowDTO,
} from "../api/types";

type TokenRow = TokenRowDTO;

let seed: SeedState = makeSeed();

export function resetFixtures() { seed = makeSeed(); }

export const handlers = [
  http.get("/api/context", () =>
    HttpResponse.json({
      project: { name: "Let's", description: "Track F mock workspace" },
      auth: { dev_login_enabled: false, github_configured: true },
    }),
  ),

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
            role, device_label: device, display_name: null, human_id: humanRow.id,
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

  http.get("/api/topics/:id/attachments", ({ params }) => {
    const topicId = Number(params.id);
    const slot = seed as unknown as { fixtureAttachments?: AttachmentDTO[] };
    return HttpResponse.json(
      (slot.fixtureAttachments ?? []).filter((attachment) => attachment.topic_id === topicId),
    );
  }),

  http.post("/api/topics/:id/attachments", async ({ params, request }) => {
    const topicId = Number(params.id);
    const url = new URL(request.url);
    const filename = url.searchParams.get("filename") || "attachment";
    const mimeType = request.headers.get("content-type") || "application/octet-stream";
    const body = await request.arrayBuffer();
    const slot = seed as unknown as { fixtureAttachments?: AttachmentDTO[] };
    const attachments = (slot.fixtureAttachments ??= []);
    const id = attachments.length + 1;
    const row: AttachmentDTO = {
      id,
      workspace_id: 1,
      topic_id: topicId,
      message_id: null,
      uploaded_by_human_id: 1,
      kind: mimeType.startsWith("image/") ? "image" : "file",
      filename,
      mime_type: mimeType,
      byte_size: body.byteLength,
      sha256: `mock-sha-${id}`,
      storage_backend: "local_volume",
      storage_key: `mock/topic-${topicId}/attachment-${id}`,
      download_url: `/api/attachments/${id}/download`,
      created_at: new Date().toISOString(),
    };
    attachments.push(row);
    return HttpResponse.json(row, { status: 200 });
  }),

  http.get("/api/attachments/:id/download", ({ params }) => {
    const slot = seed as unknown as { fixtureAttachments?: AttachmentDTO[] };
    const attachment = (slot.fixtureAttachments ?? []).find((row) => row.id === Number(params.id));
    if (!attachment) return new HttpResponse(null, { status: 404 });
    return new HttpResponse("mock attachment", {
      headers: { "Content-Type": attachment.mime_type },
    });
  }),

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
    const body = (await request.json()) as {
      label: string; role: string; device_label: string; model?: string | null;
    };
    const slot = seed as unknown as { fixtureTokens?: TokenRow[] };
    const tokens = (slot.fixtureTokens ??= []);
    const id = tokens.length + 1;
    const row: TokenRow = {
      id, label: body.label, human_id: 1,
      agent_instance_id: 100 + id,
      agent_instance: {
        id: 100 + id,
        role: body.role,
        device_label: body.device_label,
        model: body.model ?? null,
      },
      created_at: new Date().toISOString(),
      last_used_at: null, revoked_at: null,
    };
    tokens.push(row);
    return HttpResponse.json(
      {
        id, value: `lets_${Math.random().toString(36).slice(2, 10)}`,
        label: body.label,
        agent_instance: {
          id: row.agent_instance_id,
          role: body.role,
          device_label: body.device_label,
          model: body.model ?? null,
        },
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

  http.patch("/api/agent-instances/:id", async ({ params, request }) => {
    const body = (await request.json()) as { model?: string; display_name?: string };
    const agentId = Number(params.id);
    const seeded = seed.agentInstances.find((a) => a.id === agentId);
    if (seeded) {
      const withModel = seeded as typeof seeded & { model?: string | null };
      if (body.model !== undefined) withModel.model = body.model;
      if (body.display_name !== undefined) seeded.display_name = body.display_name;
      return HttpResponse.json({
        id: seeded.id,
        role: seeded.role,
        device_label: seeded.device_label,
        model: withModel.model ?? null,
        display_name: seeded.display_name,
      });
    }
    const slot = seed as unknown as { fixtureTokens?: TokenRow[] };
    for (const t of slot.fixtureTokens ?? []) {
      if (t.agent_instance?.id === agentId) {
        if (body.model !== undefined) t.agent_instance.model = body.model;
        return HttpResponse.json(t.agent_instance);
      }
    }
    return new HttpResponse(null, { status: 404 });
  }),

  http.get("/auth/me", () =>
    HttpResponse.json({
      human: {
        id: 1, name: "Neo", github_login: "neo",
        avatar_url: "https://avatars.example/neo.png",
        is_guest: false,
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

  // ---- workspace-membership plan (workspaces, members, invites)
  http.get("/api/workspaces", () =>
    HttpResponse.json([
      {
        id: 1, slug: "my-workspace", name: "我的工作区", description: null,
        owner_human_id: 1, is_private: true, my_role: "owner",
        created_at: "2026-01-01T00:00:00Z", updated_at: "2026-01-01T00:00:00Z",
      },
    ]),
  ),
  http.post("/api/workspaces", () =>
    HttpResponse.json({
      id: 2, slug: "user-auth", name: "User Auth", description: null,
      owner_human_id: 1, is_private: true, my_role: "owner",
      created_at: "2026-01-01T00:00:00Z", updated_at: "2026-01-01T00:00:00Z",
    }),
  ),
  http.patch("/api/workspaces/:id", async ({ params, request }) => {
    const body = (await request.json()) as { name?: string };
    return HttpResponse.json({
      id: Number(params.id), slug: "my-workspace",
      name: body.name ?? "我的工作区", description: null,
      owner_human_id: 1, is_private: true, my_role: "owner",
      created_at: "2026-01-01T00:00:00Z", updated_at: new Date().toISOString(),
    });
  }),
  http.delete("/api/workspaces/:id", () => new HttpResponse(null, { status: 204 })),
  http.get("/api/workspaces/:id/members", () =>
    HttpResponse.json([
      {
        kind: "human", id: 1, name: "Neo", email: null, avatar_url: null,
        role: "owner", joined_at: "2026-01-01T00:00:00Z",
      },
    ]),
  ),
  http.post("/api/workspaces/:id/invites", ({ params }) =>
    HttpResponse.json({
      id: 1, token: "mock-token-abc",
      join_url: `http://localhost/join/mock-token-abc`,
      created_at: "2026-01-01T00:00:00Z",
    }, { status: 201 }),
  ),
  http.post("/api/invites/:token/accept", () =>
    HttpResponse.json({ workspace_id: 1 }),
  ),
  http.post("/api/invites/:token/accept-guest", async ({ request }) => {
    const body = (await request.json()) as { name?: string };
    return HttpResponse.json({
      workspace_id: 1,
      human: { id: 2, name: body.name ?? "Guest", is_guest: true },
    });
  }),
  http.get("/api/workspaces/:id/topics", ({ request }) => {
    const url = new URL(request.url);
    const archived = url.searchParams.get("archived") === "true";
    return HttpResponse.json(
      seed.topics.filter((t) => archived ? t.archived_at : !t.archived_at),
    );
  }),

  // ---- v1.5 chrome (projects, single topic, participants, artifacts, git, attention)
  http.get("/api/projects", () =>
    HttpResponse.json([
      {
        id: 1, slug: "lets-mock", name: "Let's",
        description: "Track F mock workspace",
        owner_human_id: 1, repo_path: null,
        created_at: "2026-05-19T09:00:00Z",
        updated_at: "2026-05-19T09:00:00Z",
      },
    ]),
  ),
  http.get("/api/projects/:id", ({ params }) =>
    HttpResponse.json({
      id: Number(params.id), slug: "lets-mock", name: "Let's",
      description: "Track F mock workspace",
      owner_human_id: 1, repo_path: null,
      created_at: "2026-05-19T09:00:00Z",
      updated_at: "2026-05-19T09:00:00Z",
    }),
  ),
  http.get("/api/projects/:id/topics", () => HttpResponse.json(seed.topics)),
  http.get("/api/projects/:id/git-status", () =>
    new HttpResponse(JSON.stringify({ detail: "project has no repo_path" }), {
      status: 404,
    }),
  ),
  http.get("/api/topics/:id", ({ params }) => {
    const topic = seed.topics.find((t) => t.id === Number(params.id));
    if (!topic)
      return new HttpResponse(JSON.stringify({ detail: "topic not found" }), {
        status: 404,
      });
    return HttpResponse.json(topic);
  }),
  http.patch("/api/topics/:id", async ({ params, request }) => {
    const topic = seed.topics.find((t) => t.id === Number(params.id));
    if (!topic)
      return new HttpResponse(JSON.stringify({ detail: "topic not found" }), {
        status: 404,
      });
    const body = (await request.json()) as {
      title?: string;
      agent_intervention_mode?: "auto" | "mentions" | "silent";
      shared_context_mode?: "topic_only" | "topic_with_files";
    };
    if (body.title !== undefined) topic.title = body.title;
    if (body.agent_intervention_mode !== undefined) {
      topic.agent_intervention_mode = body.agent_intervention_mode;
    }
    if (body.shared_context_mode !== undefined) {
      topic.shared_context_mode = body.shared_context_mode;
    }
    topic.updated_at = new Date().toISOString();
    return HttpResponse.json(topic);
  }),
  http.post("/api/topics/:id/archive", ({ params }) => {
    const topic = seed.topics.find((t) => t.id === Number(params.id));
    if (!topic)
      return new HttpResponse(JSON.stringify({ detail: "topic not found" }), {
        status: 404,
      });
    topic.archived_at = topic.archived_at ?? new Date().toISOString();
    topic.updated_at = topic.archived_at;
    return HttpResponse.json(topic);
  }),
  http.post("/api/topics/:id/restore", ({ params }) => {
    const topic = seed.topics.find((t) => t.id === Number(params.id));
    if (!topic)
      return new HttpResponse(JSON.stringify({ detail: "topic not found" }), {
        status: 404,
      });
    topic.archived_at = null;
    topic.updated_at = new Date().toISOString();
    return HttpResponse.json(topic);
  }),
  http.get("/api/topics/:id/participants", ({ params }) => {
    const topicId = Number(params.id);
    const msgs = seed.messages.filter((m) => m.topic_id === topicId);
    const humanIds = new Set<number>();
    const agentIds = new Set<number>();
    for (const m of msgs) {
      if (m.actor_id === null) continue;
      if (m.actor_type === "human") humanIds.add(m.actor_id);
      else if (m.actor_type === "agent") agentIds.add(m.actor_id);
    }
    return HttpResponse.json({
      can_manage: true,
      is_public: false,
      humans: seed.humans
        .filter((h) => humanIds.has(h.id))
        .map((h) => ({ id: h.id, name: h.name, email: null })),
      agents: seed.agentInstances
        .filter((a) => agentIds.has(a.id))
        .map((a) => ({
          id: a.id, role: a.role, device_label: a.device_label, display_name: a.display_name,
          human_name: seed.humans.find((h) => h.id === a.human_id)?.name ?? "",
        })),
    });
  }),
  http.get("/api/artifacts", ({ request }) => {
    const url = new URL(request.url);
    const topicId = Number(url.searchParams.get("topic_id"));
    // Return a single mock artifact for the default topic so the panel
    // renders something in fixture demos.
    if (topicId === 1) {
      return HttpResponse.json([
        {
          id: 1, slug: "ai-memory-talk.pptx", type: "doc",
          backend: "git", backend_ref: "ai-memory-talk.pptx",
          title: "AI memory talk", topic_id: 1,
          current_version_id: 3,
          created_at: "2026-05-19T09:31:00Z",
          updated_at: "2026-05-19T10:00:00Z",
          versions: ["v0", "v1", "v2"].map((label, i) => ({
            id: i + 1, artifact_id: 1, version_label: label,
            backend_revision_id: `mock${i.toString().padStart(8, "0")}`,
            created_by_human_id: null, created_by_agent_instance_id: null,
            summary: `version ${label}`,
            preview_uri: null,
            created_at: `2026-05-19T09:${30 + i * 5}:00Z`,
          })),
        },
      ]);
    }
    return HttpResponse.json([]);
  }),
  http.get("/api/agents/online", () => HttpResponse.json([])),
  http.get("/api/agents/:id", ({ params }) => {
    const agentId = Number(params.id);
    const agent = seed.agentInstances.find((a) => a.id === agentId);
    if (!agent) return new HttpResponse(null, { status: 404 });
    const withModel = agent as typeof agent & { model?: string | null };
    const owner = seed.humans.find((h) => h.id === agent.human_id);
    return HttpResponse.json({
      agent_instance_id: agent.id,
      role: agent.role,
      device_label: agent.device_label,
      model: withModel.model ?? (agent.role === "claude" ? "haiku" : null),
      display_name: agent.display_name,
      paused_at: null,
      deleted_at: null,
      human_id: agent.human_id,
      human_name: owner?.name ?? "Neo",
      last_seen_at: null,
      is_online: 0,
      created_at: "2026-01-01T00:00:00Z",
      workspaces: [
        {
          id: 1,
          slug: "my-workspace",
          name: "我的工作区",
          joined_at: "2026-01-01T00:00:00Z",
        },
      ],
      stats: {
        message_count: 0,
        topic_count: 0,
        input_tokens: 0,
        output_tokens: 0,
      },
      recent_topics: [],
      usage_started_at: "2026-05-22",
      quota: null,
    });
  }),
  http.get("/api/agent-instances", () => HttpResponse.json([])),
  http.post("/api/projects/:id/topics", async ({ params, request }) => {
    const body = (await request.json()) as { slug: string; title: string };
    const topic = {
      id: seed.topics.length + 100,
      slug: body.slug, title: body.title,
      project_id: Number(params.id),
      agent_intervention_mode: "auto" as const,
      shared_context_mode: "topic_with_files" as const,
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
    };
    seed.topics.push(topic);
    return HttpResponse.json(topic, { status: 200 });
  }),
  http.get("/api/attention", () =>
    HttpResponse.json({ needs_decision: [], mentioned_questions: [], suggestions: [] }),
  ),

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
    const meta = (proposal.metadata ?? {}) as {
      items?: Array<{
        title: string;
        parent_index?: number;
        summary?: string | null;
        linked_message_id?: number | null;
        deliverable_artifact_id?: number | null;
      }>;
    };
    const propItems = meta.items ?? [];
    const newIds: number[] = [];
    for (let i = 0; i < propItems.length; i++) {
      const id = seed.taskItems.length + i + 100;
      newIds.push(id);
      seed.taskItems.push({
        id, task_tree_id: tree.id, parent_item_id: null,
        title: propItems[i]!.title,
        summary: propItems[i]!.summary ?? null,
        linked_message_id: propItems[i]!.linked_message_id ?? null,
        deliverable_artifact_id: propItems[i]!.deliverable_artifact_id ?? null,
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
      summary?: string | null; linked_message_id?: number | null; deliverable_artifact_id?: number | null;
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
      summary: body.summary ?? null,
      linked_message_id: body.linked_message_id ?? null,
      deliverable_artifact_id: body.deliverable_artifact_id ?? null,
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
    const body = (await request.json()) as {
      status?: "pending"|"active"|"done";
      title?: string;
      summary?: string | null;
      linked_message_id?: number | null;
      deliverable_artifact_id?: number | null;
    };
    const item = seed.taskItems.find((i) => i.id === id);
    if (!item) return new HttpResponse(null, { status: 404 });
    if (body.status) item.status = body.status;
    if (body.title) item.title = body.title;
    if (body.summary !== undefined) item.summary = body.summary;
    if (body.linked_message_id !== undefined) item.linked_message_id = body.linked_message_id;
    if (body.deliverable_artifact_id !== undefined) item.deliverable_artifact_id = body.deliverable_artifact_id;
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
