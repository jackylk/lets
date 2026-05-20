import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { apiRequest } from "./client";
import { useIdentity } from "../identity/useIdentity";
import type {
  AddTaskItemInput,
  AdoptGoalInput,
  AdoptTaskTreeInput,
  PatchTaskItemInput,
  ResolveNudgeInput,
  ResolveNudgeResponse,
  TaskItemDTO,
  TaskTreeResponse,
} from "./taskTreeTypes";

export function useTopicTaskTree(topicId: number) {
  const identity = useIdentity();
  return useQuery({
    queryKey: ["topics", topicId, "task-tree"],
    queryFn: () =>
      apiRequest<TaskTreeResponse>(`/api/topics/${topicId}/task-tree`, { identity }),
  });
}

export function useAdoptTaskTreeProposal(topicId: number) {
  const identity = useIdentity();
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (input: AdoptTaskTreeInput) =>
      apiRequest<TaskTreeResponse>(`/api/topics/${topicId}/task-tree`, {
        method: "POST",
        body: input,
        identity,
      }),
    onSuccess: () =>
      qc.invalidateQueries({ queryKey: ["topics", topicId, "task-tree"] }),
  });
}

export function useAdoptGoalProposal(topicId: number) {
  const identity = useIdentity();
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (input: AdoptGoalInput) =>
      apiRequest<TaskTreeResponse>(`/api/topics/${topicId}/goal`, {
        method: "POST",
        body: input,
        identity,
      }),
    onSuccess: () =>
      qc.invalidateQueries({ queryKey: ["topics", topicId, "task-tree"] }),
  });
}

export function useAddTaskItem(topicId: number) {
  const identity = useIdentity();
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (input: AddTaskItemInput) =>
      apiRequest<TaskItemDTO>(`/api/task-items`, {
        method: "POST",
        body: input,
        identity,
      }),
    onSuccess: () =>
      qc.invalidateQueries({ queryKey: ["topics", topicId, "task-tree"] }),
  });
}

export function useUpdateTaskItem(topicId: number) {
  const identity = useIdentity();
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, ...input }: PatchTaskItemInput & { id: number }) =>
      apiRequest<TaskItemDTO>(`/api/task-items/${id}`, {
        method: "PATCH",
        body: input,
        identity,
      }),
    onSuccess: () =>
      qc.invalidateQueries({ queryKey: ["topics", topicId, "task-tree"] }),
  });
}

export function useResolveNudge(topicId: number) {
  const identity = useIdentity();
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, ...input }: ResolveNudgeInput & { id: number }) =>
      apiRequest<ResolveNudgeResponse>(`/api/nudges/${id}/resolve`, {
        method: "POST",
        body: input,
        identity,
      }),
    onSuccess: () =>
      qc.invalidateQueries({ queryKey: ["topics", topicId, "messages"] }),
  });
}
