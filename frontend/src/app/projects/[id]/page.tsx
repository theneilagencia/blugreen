"use client";

import { Alert } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Breadcrumb } from "@/components/ui/breadcrumb";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { ConfirmModal } from "@/components/ui/confirm-modal";
import { Input } from "@/components/ui/input";
import { api, Project } from "@/lib/api";
import {
  Clock,
  Edit2,
  Loader2,
  Save,
  Trash2,
} from "lucide-react";
import { useParams, useRouter } from "next/navigation";
import { useEffect, useState } from "react";

export default function ProjectDetailsPage() {
  const params = useParams();
  const router = useRouter();
  const projectId = Number(params.id);

  const [project, setProject] = useState<Project | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [editing, setEditing] = useState(false);
  const [editForm, setEditForm] = useState({ name: "", description: "" });
  const [saving, setSaving] = useState(false);

  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false);
  const [deleting, setDeleting] = useState(false);

  useEffect(() => {
    loadProject();
  }, [projectId]);

  async function loadProject() {
    try {
      setLoading(true);
      setError(null);
      const data = await api.projects.get(projectId);
      setProject(data);
      setEditForm({ name: data.name, description: data.description || "" });
    } catch (err) {
      setError("Failed to load project. Make sure the backend is running.");
    } finally {
      setLoading(false);
    }
  }

  async function handleSave() {
    if (!editForm.name.trim()) {
      setError("Project name is required");
      return;
    }

    try {
      setSaving(true);
      setError(null);
      await api.projects.update(projectId, {
        name: editForm.name,
        description: editForm.description || undefined,
      });
      setEditing(false);
      loadProject();
    } catch (err) {
      setError("Failed to update project. Please try again.");
    } finally {
      setSaving(false);
    }
  }

  async function confirmDelete() {
    try {
      setDeleting(true);
      setError(null);
      await api.projects.delete(projectId);
      router.push("/projects");
    } catch (err) {
      setError("Failed to delete project. The project may have active deployments or dependencies.");
      setDeleting(false);
    }
  }

  function getStatusBadge(status: string) {
    const variants: Record<string, "default" | "primary" | "success" | "warning" | "danger"> = {
      draft: "default",
      planning: "primary",
      in_progress: "warning",
      testing: "primary",
      deploying: "primary",
      deployed: "success",
      failed: "danger",
      rolled_back: "danger",
    };
    return <Badge variant={variants[status] || "default"}>{status}</Badge>;
  }

  if (loading) {
    return (
      <div className="max-w-7xl mx-auto px-md py-lg">
        <div className="flex items-center justify-center py-xl">
          <Clock className="h-8 w-8 animate-spin text-gray-400" />
          <span className="ml-sm text-gray-500">Loading project...</span>
        </div>
      </div>
    );
  }

  if (!project) {
    return (
      <div className="max-w-7xl mx-auto px-md py-lg">
        <Breadcrumb
          items={[
            { label: "Projects", href: "/projects" },
            { label: "Not Found" },
          ]}
          className="mb-md"
        />
        <Alert variant="error">
          Project not found. The project may have been deleted or you may not have access.
        </Alert>
      </div>
    );
  }

  return (
    <div className="max-w-7xl mx-auto px-md py-lg">
      <Breadcrumb
        items={[
          { label: "Projects", href: "/projects" },
          { label: project.name },
        ]}
        className="mb-md"
      />
      <div className="flex items-center gap-md mb-lg">
        <div className="flex-1">
          <h1 className="text-2xl font-bold text-gray-900">{project.name}</h1>
          <p className="text-gray-600">{project.description || "No description"}</p>
        </div>
        {getStatusBadge(project.status)}
      </div>

      {error && (
        <Alert variant="error" className="mb-lg">
          {error}
        </Alert>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-lg">
        <Card>
          <CardHeader>
            <div className="flex items-center justify-between">
              <h2 className="text-lg font-semibold">Project Details</h2>
              <div className="flex gap-sm">
                {!editing && (
                  <Button
                    variant="secondary"
                    size="sm"
                    onClick={() => setEditing(true)}
                  >
                    <Edit2 className="h-4 w-4 mr-1" />
                    Edit
                  </Button>
                )}
                <Button
                  variant="danger"
                  size="sm"
                  onClick={() => setShowDeleteConfirm(true)}
                >
                  <Trash2 className="h-4 w-4" />
                </Button>
              </div>
            </div>
          </CardHeader>
          <CardContent>
            {editing ? (
              <div className="space-y-md">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-xs">
                    Project Name *
                  </label>
                  <Input
                    value={editForm.name}
                    onChange={(e) => setEditForm({ ...editForm, name: e.target.value })}
                    placeholder="Enter project name"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-xs">
                    Description
                  </label>
                  <Input
                    value={editForm.description}
                    onChange={(e) => setEditForm({ ...editForm, description: e.target.value })}
                    placeholder="Enter project description"
                  />
                </div>
                <div className="flex gap-sm justify-end">
                  <Button
                    variant="secondary"
                    onClick={() => {
                      setEditing(false);
                      setEditForm({ name: project.name, description: project.description || "" });
                    }}
                  >
                    Cancel
                  </Button>
                  <Button onClick={handleSave} disabled={saving}>
                    {saving ? (
                      <>
                        <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                        Saving...
                      </>
                    ) : (
                      <>
                        <Save className="h-4 w-4 mr-2" />
                        Save
                      </>
                    )}
                  </Button>
                </div>
              </div>
            ) : (
              <div className="space-y-md">
                <div className="grid grid-cols-2 gap-sm text-sm">
                  <div>
                    <span className="text-gray-600">ID:</span>
                    <span className="ml-sm font-medium">{project.id}</span>
                  </div>
                  <div>
                    <span className="text-gray-600">Status:</span>
                    <span className="ml-sm">{getStatusBadge(project.status)}</span>
                  </div>
                  <div>
                    <span className="text-gray-600">Created:</span>
                    <span className="ml-sm">
                      {new Date(project.created_at).toLocaleString()}
                    </span>
                  </div>
                  <div>
                    <span className="text-gray-600">Updated:</span>
                    <span className="ml-sm">
                      {new Date(project.updated_at).toLocaleString()}
                    </span>
                  </div>
                </div>
              </div>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <h2 className="text-lg font-semibold">Quick Actions</h2>
          </CardHeader>
          <CardContent>
            <div className="space-y-sm">
              <p className="text-sm text-gray-600 mb-md">
                Navigate to specialized views for this project:
              </p>
              <Button
                variant="secondary"
                className="w-full justify-start"
                onClick={() => router.push(`/create/${project.id}`)}
              >
                View Product Creation Details
              </Button>
              <Button
                variant="secondary"
                className="w-full justify-start"
                onClick={() => router.push(`/assume/${project.id}`)}
              >
                View Assumption Details
              </Button>
            </div>
          </CardContent>
        </Card>
      </div>

      <ConfirmModal
        isOpen={showDeleteConfirm}
        onClose={() => setShowDeleteConfirm(false)}
        onConfirm={confirmDelete}
        title="Delete Project"
        message="Are you sure you want to delete this project? This action cannot be undone. All associated data, deployments, and history will be permanently removed."
        confirmLabel="Delete Project"
        cancelLabel="Cancel"
        variant="danger"
        loading={deleting}
      />
    </div>
  );
}
