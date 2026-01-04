"use client";

import { Alert } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { ConfirmModal } from "@/components/ui/confirm-modal";
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
import { api, Project } from "@/lib/api";
import { FolderOpen, Plus, Search, Trash2 } from "lucide-react";
import { useEffect, useState } from "react";

export default function ProjectsPage() {
  const [projects, setProjects] = useState<Project[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [searchQuery, setSearchQuery] = useState("");
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [newProjectName, setNewProjectName] = useState("");
  const [newProjectDescription, setNewProjectDescription] = useState("");
  const [creating, setCreating] = useState(false);
  const [deleteConfirm, setDeleteConfirm] = useState<{ show: boolean; projectId: number | null }>({
    show: false,
    projectId: null,
  });
  const [deleting, setDeleting] = useState(false);

  useEffect(() => {
    loadProjects();
  }, []);

  async function loadProjects() {
    try {
      setLoading(true);
      const data = await api.projects.list();
      setProjects(data);
      setError(null);
    } catch (err) {
      setError("Failed to load projects. Make sure the backend is running.");
    } finally {
      setLoading(false);
    }
  }

  async function createProject() {
    if (!newProjectName.trim()) return;

    try {
      setCreating(true);
      await api.projects.create({
        name: newProjectName,
        description: newProjectDescription || undefined,
      });
      setShowCreateModal(false);
      setNewProjectName("");
      setNewProjectDescription("");
      await loadProjects();
    } catch (err) {
      setError("Failed to create project");
    } finally {
      setCreating(false);
    }
  }

  function handleDeleteClick(id: number, e: React.MouseEvent) {
    e.stopPropagation();
    setDeleteConfirm({ show: true, projectId: id });
  }

  async function confirmDelete() {
    if (!deleteConfirm.projectId) return;

    try {
      setDeleting(true);
      setError(null);
      
      const response = await api.projects.delete(deleteConfirm.projectId);
      const data = await response.json();

      if (!response.ok) {
        handleBusinessError(data);
        return;
      }

      // Success
      setDeleteConfirm({ show: false, projectId: null });
      await loadProjects();
    } catch {
      setError("Erro de conexão. Tente novamente.");
    } finally {
      setDeleting(false);
    }
  }

  function handleBusinessError(data: { error_code?: string; message?: string }) {
    const errorMessages: Record<string, string> = {
      PROJECT_NOT_FOUND: "Este projeto não existe ou já foi removido.",
      PROJECT_ACTIVE: "Este projeto está ativo. Encerre-o antes de excluir.",
      PROJECT_DELETE_CONSTRAINT: "O projeto ainda possui vínculos internos.",
      PROJECT_DELETE_INTERNAL_ERROR: "Erro interno. Tente novamente.",
    };

    const message = data.message || errorMessages[data.error_code || ""] || "Erro ao excluir projeto.";
    setError(message);
  }

  const filteredProjects = projects.filter(
    (p) =>
      p.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      p.description?.toLowerCase().includes(searchQuery.toLowerCase())
  );

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

  return (
    <div className="max-w-7xl mx-auto px-md py-lg">
      <div className="flex items-center justify-between mb-lg">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Projects</h1>
          <p className="text-gray-600 mt-xs">
            Manage your autonomous engineering projects
          </p>
        </div>
        <Button onClick={() => setShowCreateModal(true)}>
          <Plus className="h-4 w-4 mr-2" />
          New Project
        </Button>
      </div>

      {error && (
        <Alert variant="error" className="mb-lg">
          {error}
        </Alert>
      )}

      <Card>
        <CardHeader>
          <div className="flex items-center gap-md">
            <div className="relative flex-1">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-gray-400" />
              <Input
                placeholder="Search projects..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="pl-10"
              />
            </div>
          </div>
        </CardHeader>
        <CardContent className="p-0">
          {loading ? (
            <div className="p-md">
              <SkeletonTable rows={5} columns={5} />
            </div>
          ) : filteredProjects.length === 0 ? (
            <TableEmptyState
              icon={FolderOpen}
              title={searchQuery ? "No projects match your search" : "No projects yet"}
              description={
                searchQuery
                  ? "Try adjusting your search terms or clear the search to see all projects."
                  : "Create your first project to get started with autonomous engineering."
              }
              action={
                searchQuery
                  ? { label: "Clear Search", onClick: () => setSearchQuery("") }
                  : { label: "New Project", onClick: () => setShowCreateModal(true), icon: Plus }
              }
            />
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Name</TableHead>
                  <TableHead>Description</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead>Created</TableHead>
                  <TableHead>Actions</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {filteredProjects.map((project) => (
                  <TableRow
                    key={project.id}
                    hoverable
                    onClick={() =>
                      (window.location.href = `/projects/${project.id}`)
                    }
                  >
                    <TableCell className="font-medium">{project.name}</TableCell>
                    <TableCell className="text-gray-500">
                      {project.description || "-"}
                    </TableCell>
                    <TableCell>{getStatusBadge(project.status)}</TableCell>
                    <TableCell>
                      {new Date(project.created_at).toLocaleDateString()}
                    </TableCell>
                    <TableCell>
                      <Button
                        variant="danger"
                        size="sm"
                        onClick={(e) => handleDeleteClick(project.id, e)}
                      >
                        <Trash2 className="h-4 w-4" />
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
        isOpen={showCreateModal}
        onClose={() => setShowCreateModal(false)}
        title="Create New Project"
        footer={
          <>
            <Button variant="secondary" onClick={() => setShowCreateModal(false)}>
              Cancel
            </Button>
            <Button onClick={createProject} loading={creating}>
              Create Project
            </Button>
          </>
        }
      >
        <div className="space-y-md">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-xs">
              Project Name
            </label>
            <Input
              placeholder="Enter project name"
              value={newProjectName}
              onChange={(e) => setNewProjectName(e.target.value)}
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-xs">
              Description (optional)
            </label>
            <Input
              placeholder="Enter project description"
              value={newProjectDescription}
              onChange={(e) => setNewProjectDescription(e.target.value)}
            />
          </div>
        </div>
      </Modal>

      <ConfirmModal
        isOpen={deleteConfirm.show}
        onClose={() => setDeleteConfirm({ show: false, projectId: null })}
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
