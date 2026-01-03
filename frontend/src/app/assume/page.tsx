"use client";

import { Alert } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Modal } from "@/components/ui/modal";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { SkeletonTable } from "@/components/ui/skeleton";
import { TableEmptyState } from "@/components/ui/empty-state";
import { api, AssumptionStatus, Project } from "@/lib/api";
import {
  CheckCircle,
  Clock,
  Download,
  FolderOpen,
  GitBranch,
  Loader2,
  Plus,
  RefreshCw,
  XCircle,
} from "lucide-react";
import { useEffect, useState } from "react";

export default function AssumePage() {
  const [projects, setProjects] = useState<Project[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showAssumeModal, setShowAssumeModal] = useState(false);
  const [assumeForm, setAssumeForm] = useState({
    name: "",
    description: "",
    repository_url: "",
    branch: "main",
  });
  const [assuming, setAssuming] = useState(false);
  const [activeAssumption, setActiveAssumption] = useState<{
    projectId: number;
    status: AssumptionStatus | null;
  } | null>(null);

  useEffect(() => {
    loadProjects();
  }, []);

  useEffect(() => {
    let interval: NodeJS.Timeout;
    if (activeAssumption && activeAssumption.status?.assumption_status === "in_progress") {
      interval = setInterval(async () => {
        try {
          const status = await api.assume.status(activeAssumption.projectId);
          setActiveAssumption((prev) => prev ? { ...prev, status } : null);
          if (status.assumption_status !== "in_progress") {
            clearInterval(interval);
            await loadProjects();
          }
        } catch (err) {
          console.error("Failed to poll status:", err);
        }
      }, 2000);
    }
    return () => clearInterval(interval);
  }, [activeAssumption?.projectId, activeAssumption?.status?.assumption_status]);

  async function loadProjects() {
    try {
      setLoading(true);
      const data = await api.projects.list();
      const assumedProjects = data.filter(
        (p) => p.repository_url && ["draft", "assuming", "diagnosing", "evolving", "deployed"].includes(p.status)
      );
      setProjects(assumedProjects);
      setError(null);
    } catch (err) {
      setError("Failed to load projects. Make sure the backend is running.");
    } finally {
      setLoading(false);
    }
  }

  async function handleAssumeProject() {
    if (!assumeForm.name.trim() || !assumeForm.repository_url.trim()) return;

    try {
      setAssuming(true);
      const result = await api.assume.project({
        name: assumeForm.name,
        description: assumeForm.description || undefined,
        repository_url: assumeForm.repository_url,
        branch: assumeForm.branch || "main",
      });
      setShowAssumeModal(false);
      setAssumeForm({ name: "", description: "", repository_url: "", branch: "main" });
      setActiveAssumption({
        projectId: result.project_id,
        status: {
          project_id: result.project_id,
          project_name: assumeForm.name,
          project_status: "assuming",
          assumption_status: "in_progress",
          steps: [],
        },
      });
      await loadProjects();
    } catch (err) {
      setError("Failed to assume project");
    } finally {
      setAssuming(false);
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
    };
    return <Badge variant={variants[status] || "default"}>{status}</Badge>;
  }

  function getStepIcon(success: boolean | undefined) {
    if (success === true) return <CheckCircle className="h-4 w-4 text-green-500" />;
    if (success === false) return <XCircle className="h-4 w-4 text-red-500" />;
    return <Clock className="h-4 w-4 text-gray-400" />;
  }

  return (
    <div className="max-w-7xl mx-auto px-md py-lg">
      <div className="flex items-center justify-between mb-lg">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Assume Project</h1>
          <p className="text-gray-600 mt-xs">
            Take over existing repositories and analyze their structure
          </p>
        </div>
        <Button onClick={() => setShowAssumeModal(true)}>
          <Download className="h-4 w-4 mr-2" />
          Assume Repository
        </Button>
      </div>

      {error && (
        <Alert variant="error" className="mb-lg">
          {error}
        </Alert>
      )}

      {activeAssumption && activeAssumption.status?.assumption_status === "in_progress" && (
        <Card className="mb-lg">
          <CardHeader>
            <div className="flex items-center gap-sm">
              <Loader2 className="h-5 w-5 animate-spin text-primary-600" />
              <h2 className="text-lg font-semibold">
                Assuming: {activeAssumption.status.project_name}
              </h2>
            </div>
          </CardHeader>
          <CardContent>
            <div className="space-y-sm">
              {activeAssumption.status.steps.map((step, index) => (
                <div key={index} className="flex items-center gap-sm">
                  {getStepIcon(step.success)}
                  <span className="text-sm">
                    {step.step.replace(/_/g, " ").replace(/\b\w/g, (l) => l.toUpperCase())}
                  </span>
                  {step.error && (
                    <span className="text-sm text-red-500">- {step.error}</span>
                  )}
                </div>
              ))}
              {activeAssumption.status.steps.length === 0 && (
                <p className="text-sm text-gray-500">Starting assumption process...</p>
              )}
            </div>
          </CardContent>
        </Card>
      )}

      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <h2 className="text-lg font-semibold">Assumed Projects</h2>
            <Button variant="secondary" size="sm" onClick={loadProjects} disabled={loading}>
              <RefreshCw className={`h-4 w-4 mr-2 ${loading ? "animate-spin" : ""}`} />
              Refresh
            </Button>
          </div>
        </CardHeader>
        <CardContent className="p-0">
          {loading ? (
            <div className="p-md">
              <SkeletonTable rows={5} columns={5} />
            </div>
          ) : projects.length === 0 ? (
            <TableEmptyState
              icon={FolderOpen}
              title="No assumed projects yet"
              description="Take over an existing repository to analyze its structure, run diagnostics, and evolve it safely."
              action={{
                label: "Assume Repository",
                onClick: () => setShowAssumeModal(true),
                icon: Download,
              }}
            />
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Name</TableHead>
                  <TableHead>Repository</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead>Created</TableHead>
                  <TableHead>Actions</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {projects.map((project) => (
                  <TableRow key={project.id} hoverable>
                    <TableCell className="font-medium">{project.name}</TableCell>
                    <TableCell>
                      <div className="flex items-center gap-xs text-sm text-gray-500">
                        <GitBranch className="h-4 w-4" />
                        {project.repository_url || "-"}
                      </div>
                    </TableCell>
                    <TableCell>{getStatusBadge(project.status)}</TableCell>
                    <TableCell>
                      {new Date(project.created_at).toLocaleDateString()}
                    </TableCell>
                    <TableCell>
                      <Button
                        variant="secondary"
                        size="sm"
                        onClick={() => (window.location.href = `/assume/${project.id}`)}
                      >
                        View Details
                      </Button>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>

      <Modal
        isOpen={showAssumeModal}
        onClose={() => setShowAssumeModal(false)}
        title="Assume Existing Repository"
        footer={
          <>
            <Button variant="secondary" onClick={() => setShowAssumeModal(false)}>
              Cancel
            </Button>
            <Button
              onClick={handleAssumeProject}
              loading={assuming}
              disabled={!assumeForm.name.trim() || !assumeForm.repository_url.trim()}
            >
              <Plus className="h-4 w-4 mr-2" />
              Assume Project
            </Button>
          </>
        }
      >
        <div className="space-y-md">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-xs">
              Project Name *
            </label>
            <Input
              placeholder="Enter project name"
              value={assumeForm.name}
              onChange={(e) => setAssumeForm({ ...assumeForm, name: e.target.value })}
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-xs">
              Description (optional)
            </label>
            <Input
              placeholder="Enter project description"
              value={assumeForm.description}
              onChange={(e) => setAssumeForm({ ...assumeForm, description: e.target.value })}
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-xs">
              Repository URL *
            </label>
            <Input
              placeholder="https://github.com/user/repo.git"
              value={assumeForm.repository_url}
              onChange={(e) => setAssumeForm({ ...assumeForm, repository_url: e.target.value })}
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-xs">
              Branch
            </label>
            <Input
              placeholder="main"
              value={assumeForm.branch}
              onChange={(e) => setAssumeForm({ ...assumeForm, branch: e.target.value })}
            />
          </div>
        </div>
      </Modal>
    </div>
  );
}
