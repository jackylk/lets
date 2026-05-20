export interface TaskTreeDTO {
  id: number;
  topic_id: number;
  goal_artifact_id: number | null;
  goal_spec_text: string | null;
  version: number;
  approved_at: string;
  approved_by_human_id: number | null;
  proposal_message_id: number | null;
  created_at: string;
  updated_at: string;
}

export interface TaskItemDTO {
  id: number;
  task_tree_id: number;
  parent_item_id: number | null;
  title: string;
  owner_human_id: number | null;
  owner_agent_instance_id: number | null;
  status: "pending" | "active" | "done";
  position: number;
  created_at: string;
  updated_at: string;
}

export interface TaskTreeResponse {
  tree: TaskTreeDTO | null;
  items: TaskItemDTO[];
}

export interface DriftContextDTO {
  topic_mode: "exploratory" | "actionable";
  active_task: { id: number; title: string } | null;
  last_nudge_at: string | null;
  last_nudge_message_id: number | null;
  last_nudge_resolved_by: "moved_to_topic" | "returned" | "dismissed" | null;
  messages_since_last_nudge: number;
}

export interface AddTaskItemInput {
  task_tree_id: number;
  title: string;
  parent_item_id?: number | null;
  owner_human_id?: number | null;
  owner_agent_instance_id?: number | null;
}

export interface PatchTaskItemInput {
  status?: "pending" | "active" | "done";
  title?: string;
}

export interface AdoptTaskTreeInput {
  proposal_message_id: number;
}

export interface AdoptGoalInput {
  goal_proposal_message_id?: number;
  artifact_id?: number | null;
  spec_text?: string | null;
}

export type NudgeResolution = "moved_to_topic" | "returned" | "dismissed";

export interface ResolveNudgeInput {
  resolved_by: NudgeResolution;
  spinoff_title?: string;
}

export interface ResolveNudgeResponse {
  id: number;
  topic_id: number;
  resolved_by: NudgeResolution;
  resolved_to_topic_id: number | null;
  resolved_at: string;
}
