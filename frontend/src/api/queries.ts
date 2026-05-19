import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useIdentity } from "../identity/useIdentity";
import { apiRequest } from "./client";
import type {
  IdentityDTO, MessageDTO, TopicDTO, PostMessageInput,
  TokenRowDTO, CreateTokenInput, CreateTokenResponseDTO,
} from "./types";

export { useSession as useSessionMe } from "../auth/useSession";

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

export function useTopicMessages(topicId: number) {
  const identity = useIdentity();
  return useQuery({
    queryKey: ["topics", topicId, "messages"],
    queryFn: () => apiRequest<MessageDTO[]>(`/api/topics/${topicId}/messages`, { identity }),
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
