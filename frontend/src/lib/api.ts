// Use production URL directly to avoid build-time environment variable issues
const API_URL = "https://api.blugreen.com.br";

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

// DELETE projects returns raw response for proper error handling
async function deleteProject(id: number): Promise<Response> {
  return fetch(`${API_URL}/projects/${id}`, {
    method: "DELETE",
    credentials: "include",
    headers: {
      "Content-Type": "application/json",
    },
  });
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

export interface AssumeProjectRequest {
  name: string;
  description?: string;
  repository_url: string;
  branch?: string;
}

export interface AssumptionStatus {
  project_id: number;
  project_name: string;
  project_status: string;
  assumption_status: string;
  steps: Array<{ step: string; success: boolean; result?: unknown; error?: string }>;
  error?: string;
}

export interface ProjectContext {
  project_id: number;
  project_name: string;
  context: {
    file_tree?: unknown;
    key_files?: string[];
    detected_stack?: {
      languages: string[];
      frameworks: string[];
      databases: string[];
      tools: string[];
    };
    build_commands?: Array<{ type: string; command: string }>;
    test_commands?: Array<{ type: string; command: string }>;
  };
}

export interface DiagnosticsStatus {
  project_id: number;
  project_name: string;
  project_status: string;
  diagnostics_status: string;
  summary: {
    code_quality?: { lint_passed: boolean; tests_passed: boolean };
    security?: { secrets_found: boolean; vulnerabilities: number };
    ux_ui?: { ux_score: number; ui_score: number };
  };
  steps: Array<{ step: string; success: boolean; result?: unknown; error?: string }>;
  error?: string;
}

export interface EvolutionStatus {
  project_id: number;
  project_name: string;
  project_status: string;
  evolution_status: string;
  steps: Array<{ step: string; success: boolean; result?: unknown; error?: string }>;
  error?: string;
  rollback?: unknown;
}

export interface ProductCreateRequest {
  name: string;
  description: string;
  requirements: string;
}

export interface ProductCreationStatus {
  project_id: number;
  project_name: string;
  project_status: string;
  creation_status: string;
  steps: Array<{ step: string; success: boolean; result?: unknown; error?: string }>;
  error?: string;
}

export interface DeployRequest {
  docker_image: string;
  environment_variables?: Record<string, string>;
}

export interface DeploymentStatus {
  project_name: string;
  status: string;
  url?: string;
  health?: string;
  last_deployment?: string;
}

export interface DeploymentHistory {
  project_id: number;
  project_name: string;
  deployments: Array<{
    timestamp: string;
    status: string;
    docker_image?: string;
    url?: string;
  }>;
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
    delete: (id: number) => deleteProject(id),
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
  assume: {
    project: (data: AssumeProjectRequest) =>
      fetchAPI<{ status: string; project_id: number; message: string; monitor_url: string }>(
        "/assume/project",
        { method: "POST", body: JSON.stringify(data) }
      ),
    status: (projectId: number) =>
      fetchAPI<AssumptionStatus>(`/assume/project/${projectId}/status`),
    context: (projectId: number) =>
      fetchAPI<ProjectContext>(`/assume/project/${projectId}/context`),
    runDiagnostics: (projectId: number) =>
      fetchAPI<{ status: string; project_id: number; message: string; monitor_url: string }>(
        `/assume/project/${projectId}/diagnostics`,
        { method: "POST" }
      ),
    diagnosticsStatus: (projectId: number) =>
      fetchAPI<DiagnosticsStatus>(`/assume/project/${projectId}/diagnostics/status`),
    latestDiagnostics: (projectId: number) =>
      fetchAPI<{ project_id: number; project_name: string; diagnostics: unknown }>(
        `/assume/project/${projectId}/diagnostics/latest`
      ),
    evolve: (projectId: number, changeRequest: string) =>
      fetchAPI<{ status: string; project_id: number; message: string; monitor_url: string }>(
        `/assume/project/${projectId}/evolve`,
        { method: "POST", body: JSON.stringify({ change_request: changeRequest }) }
      ),
    evolutionStatus: (projectId: number) =>
      fetchAPI<EvolutionStatus>(`/assume/project/${projectId}/evolve/status`),
    evolutionHistory: (projectId: number) =>
      fetchAPI<{ project_id: number; project_name: string; history: unknown[] }>(
        `/assume/project/${projectId}/evolve/history`
      ),
    rollback: (projectId: number) =>
      fetchAPI<{ status: string; project_id: number; project_name: string; rollback_result: unknown }>(
        `/assume/project/${projectId}/rollback`,
        { method: "POST" }
      ),
  },
  product: {
    create: (data: ProductCreateRequest) =>
      fetchAPI<{ status: string; project_id: number; message: string; monitor_url: string }>(
        "/product/create",
        { method: "POST", body: JSON.stringify(data) }
      ),
    status: (projectId: number) =>
      fetchAPI<ProductCreationStatus>(`/product/${projectId}/status`),
    deploy: (projectId: number, data: DeployRequest) =>
      fetchAPI<{ status: string; deployment_id?: string; url?: string; error?: string }>(
        `/product/${projectId}/deploy`,
        { method: "POST", body: JSON.stringify(data) }
      ),
    rollback: (projectId: number) =>
      fetchAPI<{ status: string; message?: string; error?: string }>(
        `/product/${projectId}/rollback`,
        { method: "POST" }
      ),
    deploymentStatus: (projectId: number) =>
      fetchAPI<DeploymentStatus>(`/product/${projectId}/deployment/status`),
    deploymentHistory: (projectId: number) =>
      fetchAPI<DeploymentHistory>(`/product/${projectId}/deployment/history`),
  },
};
