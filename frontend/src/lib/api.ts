const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

async function fetchAPI<T>(
  endpoint: string,
  options?: RequestInit
): Promise<T> {
  const response = await fetch(`${API_URL}${endpoint}`, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...options?.headers,
    },
  });

  if (!response.ok) {
    throw new Error(`API error: ${response.status}`);
  }

  return response.json();
}

export interface Project {
  id: number;
  name: string;
  description: string | null;
  repository_url: string | null;
  status: string;
  created_at: string;
  updated_at: string;
}

export interface Task {
  id: number;
  title: string;
  description: string | null;
  task_type: string;
  status: string;
  project_id: number;
  assigned_agent: string | null;
  error_message: string | null;
  created_at: string;
  updated_at: string;
  completed_at: string | null;
}

export interface Agent {
  id: number;
  name: string;
  agent_type: string;
  status: string;
  current_task_id: number | null;
  capabilities: string;
  restrictions: string;
  created_at: string;
  last_active_at: string | null;
}

export interface Workflow {
  id: number;
  name: string;
  project_id: number;
  status: string;
  current_step: string | null;
  created_at: string;
  updated_at: string;
  completed_at: string | null;
}

export const api = {
  projects: {
    list: () => fetchAPI<Project[]>("/projects/"),
    get: (id: number) => fetchAPI<Project>(`/projects/${id}`),
    create: (data: { name: string; description?: string }) =>
      fetchAPI<Project>("/projects/", {
        method: "POST",
        body: JSON.stringify(data),
      }),
    update: (id: number, data: Partial<Project>) =>
      fetchAPI<Project>(`/projects/${id}`, {
        method: "PATCH",
        body: JSON.stringify(data),
      }),
    delete: (id: number) =>
      fetchAPI<{ message: string }>(`/projects/${id}`, { method: "DELETE" }),
    start: (id: number, requirements: string) =>
      fetchAPI<{ status: string; project_id: number; plan: unknown }>(
        `/projects/${id}/start?requirements=${encodeURIComponent(requirements)}`,
        { method: "POST" }
      ),
    executeNext: (id: number) =>
      fetchAPI<{ status: string; message?: string }>(
        `/projects/${id}/execute-next`,
        { method: "POST" }
      ),
    rollback: (id: number) =>
      fetchAPI<{ status: string; message: string }>(
        `/projects/${id}/rollback`,
        { method: "POST" }
      ),
    status: (id: number) =>
      fetchAPI<{ project: Project; tasks: unknown; workflows: unknown }>(
        `/projects/${id}/status`
      ),
  },
  tasks: {
    list: (projectId?: number) =>
      fetchAPI<Task[]>(
        `/tasks/${projectId ? `?project_id=${projectId}` : ""}`
      ),
    get: (id: number) => fetchAPI<Task>(`/tasks/${id}`),
    create: (data: {
      title: string;
      task_type: string;
      project_id: number;
      description?: string;
    }) =>
      fetchAPI<Task>("/tasks/", {
        method: "POST",
        body: JSON.stringify(data),
      }),
  },
  agents: {
    list: () => fetchAPI<Agent[]>("/agents/"),
    types: () =>
      fetchAPI<{ type: string; name: string; description: string }[]>(
        "/agents/types"
      ),
    get: (type: string) => fetchAPI<Agent>(`/agents/${type}`),
    capabilities: (type: string) =>
      fetchAPI<{ capabilities: string[]; restrictions: string[] }>(
        `/agents/${type}/capabilities`
      ),
  },
  workflows: {
    list: (projectId?: number) =>
      fetchAPI<Workflow[]>(
        `/workflows/${projectId ? `?project_id=${projectId}` : ""}`
      ),
    get: (id: number) => fetchAPI<Workflow>(`/workflows/${id}`),
    status: (id: number) =>
      fetchAPI<{ workflow_id: number; workflow_status: string; steps: unknown[] }>(
        `/workflows/${id}/status`
      ),
  },
  quality: {
    uxRules: () =>
      fetchAPI<{
        rules: { id: string; rule: string; required: boolean }[];
        criteria: { id: string; name: string; description: string; weight: number }[];
        threshold: number;
      }>("/quality/ux/rules"),
    designSystem: () =>
      fetchAPI<{
        tokens: { spacing: Record<string, number>; border_radius: Record<string, number> };
        allowed_components: string[];
        criteria: { id: string; name: string; description: string; weight: number }[];
      }>("/quality/ui/design-system"),
    checkDeploy: (params: {
      tests_passed: boolean;
      ux_approved: boolean;
      ui_approved: boolean;
      security_passed: boolean;
      build_successful: boolean;
    }) =>
      fetchAPI<{
        can_deploy: boolean;
        blocking_issues: string[];
        rollback_plan: unknown;
      }>(
        `/quality/deploy/check?tests_passed=${params.tests_passed}&ux_approved=${params.ux_approved}&ui_approved=${params.ui_approved}&security_passed=${params.security_passed}&build_successful=${params.build_successful}`,
        { method: "POST" }
      ),
  },
};
