"use client";

import { Alert } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Modal } from "@/components/ui/modal";
import {
  api,
  DiagnosticsStatus,
  EvolutionStatus,
  Project,
  ProjectContext,
} from "@/lib/api";
import {
  Activity,
  ArrowLeft,
  CheckCircle,
  Clock,
  Code,
  FileCode,
  GitBranch,
  Loader2,
  Play,
  RefreshCw,
  RotateCcw,
  Shield,
  XCircle,
  Zap,
} from "lucide-react";
import { useParams } from "next/navigation";
import { useEffect, useState } from "react";

export default function AssumeProjectDetailPage() {
  const params = useParams();
  const projectId = Number(params.id);

  const [project, setProject] = useState<Project | null>(null);
  const [context, setContext] = useState<ProjectContext | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [diagnosticsStatus, setDiagnosticsStatus] = useState<DiagnosticsStatus | null>(null);
  const [runningDiagnostics, setRunningDiagnostics] = useState(false);

  const [evolutionStatus, setEvolutionStatus] = useState<EvolutionStatus | null>(null);
  const [showEvolveModal, setShowEvolveModal] = useState(false);
  const [changeRequest, setChangeRequest] = useState("");
  const [evolving, setEvolving] = useState(false);

  const [rollingBack, setRollingBack] = useState(false);

  useEffect(() => {
    loadProjectData();
  }, [projectId]);

  useEffect(() => {
    let interval: NodeJS.Timeout;
    if (diagnosticsStatus?.diagnostics_status === "in_progress") {
      interval = setInterval(async () => {
        try {
          const status = await api.assume.diagnosticsStatus(projectId);
          setDiagnosticsStatus(status);
          if (status.diagnostics_status !== "in_progress") {
            clearInterval(interval);
            await loadProjectData();
          }
        } catch (err) {
          console.error("Failed to poll diagnostics status:", err);
        }
      }, 2000);
    }
    return () => clearInterval(interval);
  }, [projectId, diagnosticsStatus?.diagnostics_status]);

  useEffect(() => {
    let interval: NodeJS.Timeout;
    if (evolutionStatus?.evolution_status === "in_progress") {
      interval = setInterval(async () => {
        try {
          const status = await api.assume.evolutionStatus(projectId);
          setEvolutionStatus(status);
          if (status.evolution_status !== "in_progress") {
            clearInterval(interval);
            await loadProjectData();
          }
        } catch (err) {
          console.error("Failed to poll evolution status:", err);
        }
      }, 2000);
    }
    return () => clearInterval(interval);
  }, [projectId, evolutionStatus?.evolution_status]);

  async function loadProjectData() {
    try {
      setLoading(true);
      const projectData = await api.projects.get(projectId);
      setProject(projectData);

      try {
        const contextData = await api.assume.context(projectId);
        setContext(contextData);
      } catch {
        // Context may not be available yet
      }

      try {
        const diagStatus = await api.assume.diagnosticsStatus(projectId);
        setDiagnosticsStatus(diagStatus);
      } catch {
        // Diagnostics may not have been run yet
      }

      try {
        const evoStatus = await api.assume.evolutionStatus(projectId);
        setEvolutionStatus(evoStatus);
      } catch {
        // Evolution may not have been run yet
      }

      setError(null);
    } catch (err) {
      setError("Failed to load project data");
    } finally {
      setLoading(false);
    }
  }

  async function handleRunDiagnostics() {
    try {
      setRunningDiagnostics(true);
      await api.assume.runDiagnostics(projectId);
      setDiagnosticsStatus({
        project_id: projectId,
        project_name: project?.name || "",
        project_status: "diagnosing",
        diagnostics_status: "in_progress",
        summary: {},
        steps: [],
      });
    } catch (err) {
      setError("Failed to start diagnostics");
    } finally {
      setRunningDiagnostics(false);
    }
  }

  async function handleEvolve() {
    if (!changeRequest.trim()) return;

    try {
      setEvolving(true);
      await api.assume.evolve(projectId, changeRequest);
      setShowEvolveModal(false);
      setChangeRequest("");
      setEvolutionStatus({
        project_id: projectId,
        project_name: project?.name || "",
        project_status: "evolving",
        evolution_status: "in_progress",
        steps: [],
      });
    } catch (err) {
      setError("Failed to start evolution");
    } finally {
      setEvolving(false);
    }
  }

  async function handleRollback() {
    if (!confirm("Are you sure you want to rollback? This will revert to the last baseline.")) {
      return;
    }

    try {
      setRollingBack(true);
      await api.assume.rollback(projectId);
      await loadProjectData();
    } catch (err) {
      setError("Failed to rollback");
    } finally {
      setRollingBack(false);
    }
  }

  function getStatusBadge(status: string) {
    const variants: Record<string, "default" | "primary" | "success" | "warning" | "danger"> = {
      draft: "default",
      assuming: "warning",
      diagnosing: "primary",
      evolving: "primary",
      deployed: "success",
      failed: "danger",
      in_progress: "warning",
      success: "success",
      unknown: "default",
    };
    return <Badge variant={variants[status] || "default"}>{status}</Badge>;
  }

  function getStepIcon(success: boolean | undefined) {
    if (success === true) return <CheckCircle className="h-4 w-4 text-green-500" />;
    if (success === false) return <XCircle className="h-4 w-4 text-red-500" />;
    return <Clock className="h-4 w-4 text-gray-400" />;
  }

  if (loading) {
    return (
      <div className="max-w-7xl mx-auto px-md py-lg">
        <div className="flex items-center justify-center h-64">
          <Loader2 className="h-8 w-8 animate-spin text-primary-600" />
        </div>
      </div>
    );
  }

  if (!project) {
    return (
      <div className="max-w-7xl mx-auto px-md py-lg">
        <Alert variant="error">Project not found</Alert>
      </div>
    );
  }

  const detectedStack = context?.context?.detected_stack;

  return (
    <div className="max-w-7xl mx-auto px-md py-lg">
      <div className="flex items-center gap-md mb-lg">
        <Button variant="secondary" size="sm" onClick={() => (window.location.href = "/assume")}>
          <ArrowLeft className="h-4 w-4 mr-2" />
          Back
        </Button>
        <div className="flex-1">
          <h1 className="text-2xl font-bold text-gray-900">{project.name}</h1>
          <div className="flex items-center gap-sm mt-xs">
            {getStatusBadge(project.status)}
            {project.repository_url && (
              <span className="text-sm text-gray-500 flex items-center gap-xs">
                <GitBranch className="h-4 w-4" />
                {project.repository_url}
              </span>
            )}
          </div>
        </div>
        <Button variant="secondary" onClick={loadProjectData}>
          <RefreshCw className="h-4 w-4 mr-2" />
          Refresh
        </Button>
      </div>

      {error && (
        <Alert variant="error" className="mb-lg">
          {error}
        </Alert>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-lg mb-lg">
        <Card>
          <CardHeader>
            <div className="flex items-center gap-sm">
              <Code className="h-5 w-5 text-primary-600" />
              <h2 className="text-lg font-semibold">Detected Stack</h2>
            </div>
          </CardHeader>
          <CardContent>
            {detectedStack ? (
              <div className="space-y-md">
                {detectedStack.languages?.length > 0 && (
                  <div>
                    <p className="text-sm font-medium text-gray-700 mb-xs">Languages</p>
                    <div className="flex flex-wrap gap-xs">
                      {detectedStack.languages.map((lang, i) => (
                        <Badge key={i} variant="primary">{lang}</Badge>
                      ))}
                    </div>
                  </div>
                )}
                {detectedStack.frameworks?.length > 0 && (
                  <div>
                    <p className="text-sm font-medium text-gray-700 mb-xs">Frameworks</p>
                    <div className="flex flex-wrap gap-xs">
                      {detectedStack.frameworks.map((fw, i) => (
                        <Badge key={i} variant="default">{fw}</Badge>
                      ))}
                    </div>
                  </div>
                )}
                {detectedStack.tools?.length > 0 && (
                  <div>
                    <p className="text-sm font-medium text-gray-700 mb-xs">Tools</p>
                    <div className="flex flex-wrap gap-xs">
                      {detectedStack.tools.map((tool, i) => (
                        <Badge key={i} variant="default">{tool}</Badge>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            ) : (
              <p className="text-sm text-gray-500">
                Stack detection not available. Project may still be processing.
              </p>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <div className="flex items-center gap-sm">
              <FileCode className="h-5 w-5 text-primary-600" />
              <h2 className="text-lg font-semibold">Key Files</h2>
            </div>
          </CardHeader>
          <CardContent>
            {context?.context?.key_files?.length ? (
              <ul className="space-y-xs">
                {context.context.key_files.map((file, i) => (
                  <li key={i} className="text-sm text-gray-600 flex items-center gap-xs">
                    <FileCode className="h-4 w-4 text-gray-400" />
                    {file}
                  </li>
                ))}
              </ul>
            ) : (
              <p className="text-sm text-gray-500">No key files detected yet.</p>
            )}
          </CardContent>
        </Card>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-lg mb-lg">
        <Card>
          <CardHeader>
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-sm">
                <Activity className="h-5 w-5 text-primary-600" />
                <h2 className="text-lg font-semibold">Diagnostics</h2>
              </div>
              {diagnosticsStatus && getStatusBadge(diagnosticsStatus.diagnostics_status)}
            </div>
          </CardHeader>
          <CardContent>
            {diagnosticsStatus?.diagnostics_status === "in_progress" ? (
              <div className="space-y-sm">
                <div className="flex items-center gap-sm text-sm text-gray-600">
                  <Loader2 className="h-4 w-4 animate-spin" />
                  Running diagnostics...
                </div>
                {diagnosticsStatus.steps.map((step, i) => (
                  <div key={i} className="flex items-center gap-sm text-sm">
                    {getStepIcon(step.success)}
                    <span>{step.step.replace(/_/g, " ")}</span>
                  </div>
                ))}
              </div>
            ) : diagnosticsStatus?.diagnostics_status === "success" ? (
              <div className="space-y-sm">
                <div className="flex items-center gap-sm text-sm text-green-600">
                  <CheckCircle className="h-4 w-4" />
                  Diagnostics completed
                </div>
                {diagnosticsStatus.summary?.code_quality && (
                  <p className="text-sm text-gray-600">
                    Lint: {diagnosticsStatus.summary.code_quality.lint_passed ? "Passed" : "Failed"} |
                    Tests: {diagnosticsStatus.summary.code_quality.tests_passed ? "Passed" : "Failed"}
                  </p>
                )}
              </div>
            ) : (
              <p className="text-sm text-gray-500 mb-md">
                Run diagnostics to analyze code quality, security, and UX/UI.
              </p>
            )}
            <Button
              className="w-full mt-md"
              onClick={handleRunDiagnostics}
              loading={runningDiagnostics}
              disabled={diagnosticsStatus?.diagnostics_status === "in_progress"}
            >
              <Shield className="h-4 w-4 mr-2" />
              {diagnosticsStatus ? "Re-run Diagnostics" : "Run Diagnostics"}
            </Button>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-sm">
                <Zap className="h-5 w-5 text-primary-600" />
                <h2 className="text-lg font-semibold">Evolution</h2>
              </div>
              {evolutionStatus && getStatusBadge(evolutionStatus.evolution_status)}
            </div>
          </CardHeader>
          <CardContent>
            {evolutionStatus?.evolution_status === "in_progress" ? (
              <div className="space-y-sm">
                <div className="flex items-center gap-sm text-sm text-gray-600">
                  <Loader2 className="h-4 w-4 animate-spin" />
                  Evolving project...
                </div>
                {evolutionStatus.steps.map((step, i) => (
                  <div key={i} className="flex items-center gap-sm text-sm">
                    {getStepIcon(step.success)}
                    <span>{step.step.replace(/_/g, " ")}</span>
                  </div>
                ))}
              </div>
            ) : evolutionStatus?.evolution_status === "success" ? (
              <div className="flex items-center gap-sm text-sm text-green-600">
                <CheckCircle className="h-4 w-4" />
                Evolution completed successfully
              </div>
            ) : evolutionStatus?.evolution_status === "failed" ? (
              <div className="flex items-center gap-sm text-sm text-red-600">
                <XCircle className="h-4 w-4" />
                Evolution failed - {evolutionStatus.error}
              </div>
            ) : (
              <p className="text-sm text-gray-500 mb-md">
                Safely evolve this project with automatic rollback on failure.
              </p>
            )}
            <Button
              className="w-full mt-md"
              onClick={() => setShowEvolveModal(true)}
              disabled={evolutionStatus?.evolution_status === "in_progress"}
            >
              <Play className="h-4 w-4 mr-2" />
              Start Evolution
            </Button>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <div className="flex items-center gap-sm">
              <RotateCcw className="h-5 w-5 text-primary-600" />
              <h2 className="text-lg font-semibold">Rollback</h2>
            </div>
          </CardHeader>
          <CardContent>
            <p className="text-sm text-gray-500 mb-md">
              Revert to the last known good state if something goes wrong.
            </p>
            <Button
              variant="danger"
              className="w-full"
              onClick={handleRollback}
              loading={rollingBack}
            >
              <RotateCcw className="h-4 w-4 mr-2" />
              Rollback to Baseline
            </Button>
          </CardContent>
        </Card>
      </div>

      <Modal
        isOpen={showEvolveModal}
        onClose={() => setShowEvolveModal(false)}
        title="Evolve Project"
        footer={
          <>
            <Button variant="secondary" onClick={() => setShowEvolveModal(false)}>
              Cancel
            </Button>
            <Button
              onClick={handleEvolve}
              loading={evolving}
              disabled={!changeRequest.trim()}
            >
              <Zap className="h-4 w-4 mr-2" />
              Start Evolution
            </Button>
          </>
        }
      >
        <div className="space-y-md">
          <p className="text-sm text-gray-600">
            Describe the changes you want to make to this project. The system will
            create a baseline, plan the changes, implement them, and deploy with
            automatic rollback if anything fails.
          </p>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-xs">
              Change Request *
            </label>
            <Input
              placeholder="e.g., Add a new user authentication feature with OAuth support"
              value={changeRequest}
              onChange={(e) => setChangeRequest(e.target.value)}
            />
          </div>
        </div>
      </Modal>
    </div>
  );
}
