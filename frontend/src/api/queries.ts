import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useIdentity } from "../identity/useIdentity";
import { apiRequest } from "./client";
import type {
  IdentityDTO, MessageDTO, TopicDTO, PostMessageInput,
  TokenRowDTO, CreateTokenInput, CreateTokenResponseDTO,
  ProjectDTO, ParticipantsDTO, GitStatusDTO, OnlineAgentDTO,
  AgentInstanceRowDTO,
  AttentionDTO, ArtifactDTO,
  Workspace, WorkspaceMember, WorkspaceInvite,
} from "./types";
import type { DriftContextDTO } from "./taskTreeTypes";

export { useSession as useSessionMe } from "../auth/useSession";

// ---------------------------------------------------------------------------
// v1.5 chrome queries — projects, topics, participants, git, attention,
// artifacts-by-topic, online agents. All read-only.
// ---------------------------------------------------------------------------

export function useProjects() {
  const identity = useIdentity();
  return useQuery({
    queryKey: ["projects"],
    queryFn: () => apiRequest<ProjectDTO[]>("/api/projects", { identity }),
  });
}

export function useProject(projectId: number | null) {
  const identity = useIdentity();
  return useQuery({
    queryKey: ["projects", projectId],
    queryFn: () => apiRequest<ProjectDTO>(`/api/projects/${projectId}`, { identity }),
    enabled: projectId !== null,
  });
}

export function useProjectTopics(projectId: number | null) {
  const identity = useIdentity();
  return useQuery({
    queryKey: ["projects", projectId, "topics"],
    queryFn: () => apiRequest<TopicDTO[]>(`/api/projects/${projectId}/topics`, { identity }),
    enabled: projectId !== null,
  });
}

export function useTopic(topicId: number | null) {
  const identity = useIdentity();
  return useQuery({
    queryKey: ["topics", topicId, "info"],
    queryFn: () => apiRequest<TopicDTO>(`/api/topics/${topicId}`, { identity }),
    enabled: topicId !== null,
  });
}

export function useTopicParticipants(topicId: number | null) {
  const identity = useIdentity();
  return useQuery({
    queryKey: ["topics", topicId, "participants"],
    queryFn: () =>
      apiRequest<ParticipantsDTO>(`/api/topics/${topicId}/participants`, { identity }),
    enabled: topicId !== null,
  });
}

export function useArtifactsByTopic(topicId: number | null) {
  const identity = useIdentity();
  return useQuery({
    queryKey: ["artifacts", "by-topic", topicId],
    queryFn: () =>
      apiRequest<ArtifactDTO[]>(`/api/artifacts?topic_id=${topicId}`, { identity }),
    enabled: topicId !== null,
  });
}

export function useProjectGitStatus(projectId: number | null) {
  const identity = useIdentity();
  return useQuery({
    queryKey: ["projects", projectId, "git-status"],
    queryFn: () =>
      apiRequest<GitStatusDTO>(`/api/projects/${projectId}/git-status`, { identity }),
    enabled: projectId !== null,
    retry: false,  // 404 when project has no repo_path; not worth retrying
  });
}

export function useAgentsOnline() {
  const identity = useIdentity();
  return useQuery({
    queryKey: ["agents", "online"],
    queryFn: () => apiRequest<OnlineAgentDTO[]>("/api/agents/online", { identity }),
    refetchInterval: 30_000,
  });
}

export function useAllAgents() {
  const identity = useIdentity();
  return useQuery({
    queryKey: ["agent-instances"],
    queryFn: () =>
      apiRequest<AgentInstanceRowDTO[]>("/api/agent-instances", { identity }),
    refetchInterval: 15_000,
  });
}

export function useAttention(humanId: number | null) {
  const identity = useIdentity();
  return useQuery({
    queryKey: ["attention", humanId],
    queryFn: () => apiRequest<AttentionDTO>(`/api/attention?human_id=${humanId}`, { identity }),
    enabled: humanId !== null,
    refetchInterval: 30_000,
  });
}

export function useIdentityMe() {
  const identity = useIdentity();
  return useQuery({
    queryKey: ["identity.me", identity.humanName, identity.agentRole, identity.deviceLabel],
    queryFn: () => apiRequest<IdentityDTO>("/api/identity/me", { identity }),
    enabled: identity.humanName !== null,
  });
}

export function useTopics() {
  const identity = useIdentity();
  return useQuery({
    queryKey: ["topics"],
    queryFn: () => apiRequest<TopicDTO[]>("/api/topics", { identity }),
  });
}

export interface TopicMessagesResponse {
  messages: MessageDTO[];
  drift_context: DriftContextDTO;
}

export function useTopicMessages(topicId: number) {
  const identity = useIdentity();
  return useQuery({
    queryKey: ["topics", topicId, "messages"],
    queryFn: () => apiRequest<TopicMessagesResponse>(`/api/topics/${topicId}/messages`, { identity }),
  });
}

export function usePostMessage(topicId: number) {
  const identity = useIdentity();
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (input: PostMessageInput) =>
      apiRequest<MessageDTO>("/api/messages", { method: "POST", body: input, identity }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["topics", topicId, "messages"] }),
  });
}

export function useMyTokens() {
  const identity = useIdentity();
  return useQuery({
    queryKey: ["tokens"],
    queryFn: () => apiRequest<TokenRowDTO[]>("/api/tokens", { identity }),
  });
}

export function useCreateToken() {
  const identity = useIdentity();
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (input: CreateTokenInput) =>
      apiRequest<CreateTokenResponseDTO>("/api/tokens", {
        method: "POST", body: input, identity,
      }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["tokens"] }),
  });
}

export function useRevokeToken() {
  const identity = useIdentity();
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: number) =>
      apiRequest<null>(`/api/tokens/${id}`, { method: "DELETE", identity }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["tokens"] }),
  });
}

export function useUpdateAgentModel() {
  const identity = useIdentity();
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ agentInstanceId, model }: { agentInstanceId: number; model: string }) =>
      apiRequest<{ id: number; role: string; device_label: string; model: string | null }>(
        `/api/agent-instances/${agentInstanceId}`,
        { method: "PATCH", body: { model }, identity },
      ),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["tokens"] });
      qc.invalidateQueries({ queryKey: ["agent-instances"] });
    },
  });
}

// ---------------------------------------------------------------------------
// Workspace hooks (workspace-membership plan)
// ---------------------------------------------------------------------------

export function useWorkspaces() {
  const identity = useIdentity();
  return useQuery({
    queryKey: ["workspaces"],
    queryFn: () => apiRequest<Workspace[]>("/api/workspaces", { identity }),
  });
}

export function useCreateWorkspace() {
  const identity = useIdentity();
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (name: string) =>
      apiRequest<Workspace>("/api/workspaces", { method: "POST", body: { name }, identity }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["workspaces"] });
    },
  });
}

export function useRenameWorkspace() {
  const identity = useIdentity();
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, name }: { id: number; name: string }) =>
      apiRequest<Workspace>(`/api/workspaces/${id}`, { method: "PATCH", body: { name }, identity }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["workspaces"] }),
  });
}

export function useDeleteWorkspace() {
  const identity = useIdentity();
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: number) =>
      apiRequest<null>(`/api/workspaces/${id}`, { method: "DELETE", identity }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["workspaces"] }),
  });
}

export function useWorkspaceMembers(workspaceId: number | null) {
  const identity = useIdentity();
  return useQuery({
    queryKey: ["workspace-members", workspaceId],
    enabled: workspaceId != null,
    queryFn: () =>
      apiRequest<WorkspaceMember[]>(`/api/workspaces/${workspaceId}/members`, { identity }),
  });
}

export function useCreateInvite() {
  const identity = useIdentity();
  return useMutation({
    mutationFn: (workspaceId: number) =>
      apiRequest<WorkspaceInvite>(`/api/workspaces/${workspaceId}/invites`, {
        method: "POST", body: {}, identity,
      }),
  });
}

export function useTopicsInWorkspace(workspaceId: number | null) {
  const identity = useIdentity();
  return useQuery({
    queryKey: ["workspace-topics", workspaceId],
    enabled: workspaceId != null,
    queryFn: () =>
      apiRequest<TopicDTO[]>(`/api/workspaces/${workspaceId}/topics`, { identity }),
  });
}

export function useMoveTopic() {
  const identity = useIdentity();
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ topicId, workspaceId }: { topicId: number; workspaceId: number }) =>
      apiRequest<TopicDTO>(`/api/topics/${topicId}`, {
        method: "PATCH", body: { workspace_id: workspaceId }, identity,
      }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["workspace-topics"] }),
  });
}

export function useLogout() {
  const identity = useIdentity();
  const qc = useQueryClient();
  return useMutation({
    mutationFn: () =>
      apiRequest<null>("/api/auth/logout", { method: "POST", body: {}, identity }),
    onSuccess: () => {
      qc.clear();
      // Send the user back to the public root; SessionGate will surface LoginPage.
      window.location.href = "/";
    },
  });
}
