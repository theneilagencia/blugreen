"use client";

import { Alert } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Modal, ModalContent, ModalFooter, ModalHeader } from "@/components/ui/modal";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { api, Project, ProductCreationStatus } from "@/lib/api";
import {
  CheckCircle,
  Clock,
  Eye,
  Loader2,
  Plus,
  Rocket,
  XCircle,
} from "lucide-react";
import { useEffect, useState } from "react";

export default function CreateProductPage() {
  const [projects, setProjects] = useState<Project[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showModal, setShowModal] = useState(false);
  const [creating, setCreating] = useState(false);

  const [formData, setFormData] = useState({
    name: "",
    description: "",
    requirements: "",
  });

  const [activeCreation, setActiveCreation] = useState<{
    projectId: number;
    status: ProductCreationStatus | null;
  } | null>(null);

  useEffect(() => {
    loadProjects();
  }, []);

  useEffect(() => {
    let interval: NodeJS.Timeout | null = null;

    if (activeCreation) {
      interval = setInterval(async () => {
        try {
          const status = await api.product.status(activeCreation.projectId);
          setActiveCreation((prev) =>
            prev ? { ...prev, status } : null
          );

          if (
            status.creation_status === "completed" ||
            status.creation_status === "error" ||
            status.creation_status === "failed"
          ) {
            if (interval) clearInterval(interval);
            loadProjects();
          }
        } catch (err) {
          console.error("Failed to fetch creation status:", err);
        }
      }, 2000);
    }

    return () => {
      if (interval) clearInterval(interval);
    };
  }, [activeCreation?.projectId]);

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

  async function handleCreateProduct() {
    if (!formData.name || !formData.requirements) {
      setError("Name and requirements are required");
      return;
    }

    try {
      setCreating(true);
      setError(null);

      const result = await api.product.create({
        name: formData.name,
        description: formData.description,
        requirements: formData.requirements,
      });

      setActiveCreation({
        projectId: result.project_id,
        status: null,
      });

      setShowModal(false);
      setFormData({ name: "", description: "", requirements: "" });
    } catch (err) {
      setError("Failed to create product. Please try again.");
    } finally {
      setCreating(false);
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

  function getStepIcon(step: { success: boolean }) {
    if (step.success) {
      return <CheckCircle className="h-4 w-4 text-green-500" />;
    }
    return <XCircle className="h-4 w-4 text-red-500" />;
  }

  return (
    <div className="max-w-7xl mx-auto px-md py-lg">
      <div className="flex items-center justify-between mb-lg">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Create Product</h1>
          <p className="text-gray-600 mt-xs">
            Create new SaaS products from requirements using AI agents
          </p>
        </div>
        <Button onClick={() => setShowModal(true)}>
          <Plus className="h-4 w-4 mr-2" />
          New Product
        </Button>
      </div>

      {error && (
        <Alert variant="error" className="mb-lg">
          {error}
        </Alert>
      )}

      {activeCreation && (
        <Card className="mb-lg">
          <CardHeader>
            <div className="flex items-center justify-between">
              <h2 className="text-lg font-semibold flex items-center gap-2">
                <Loader2 className="h-5 w-5 animate-spin text-primary-600" />
                Creating Product...
              </h2>
              {activeCreation.status && (
                <Badge variant="primary">{activeCreation.status.creation_status}</Badge>
              )}
            </div>
          </CardHeader>
          <CardContent>
            {activeCreation.status ? (
              <div className="space-y-md">
                <div className="flex items-center gap-md">
                  <span className="text-sm text-gray-600">Project:</span>
                  <span className="font-medium">{activeCreation.status.project_name}</span>
                  {getStatusBadge(activeCreation.status.project_status)}
                </div>

                {activeCreation.status.error && (
                  <Alert variant="error">{activeCreation.status.error}</Alert>
                )}

                {activeCreation.status.steps && activeCreation.status.steps.length > 0 && (
                  <div className="space-y-sm">
                    <h3 className="text-sm font-medium text-gray-700">Progress:</h3>
                    <div className="space-y-xs">
                      {activeCreation.status.steps.map((step, index) => (
                        <div
                          key={index}
                          className="flex items-center gap-sm text-sm"
                        >
                          {getStepIcon(step)}
                          <span className={step.success ? "text-gray-700" : "text-red-600"}>
                            {step.step}
                          </span>
                          {step.error && (
                            <span className="text-red-500 text-xs">({step.error})</span>
                          )}
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {(activeCreation.status.creation_status === "completed" ||
                  activeCreation.status.creation_status === "error" ||
                  activeCreation.status.creation_status === "failed") && (
                  <div className="flex gap-sm">
                    <Button
                      variant="outline"
                      onClick={() => setActiveCreation(null)}
                    >
                      Dismiss
                    </Button>
                    <Button
                      onClick={() =>
                        (window.location.href = `/create/${activeCreation.projectId}`)
                      }
                    >
                      <Eye className="h-4 w-4 mr-2" />
                      View Details
                    </Button>
                  </div>
                )}
              </div>
            ) : (
              <div className="flex items-center gap-sm text-gray-500">
                <Loader2 className="h-4 w-4 animate-spin" />
                Initializing product creation...
              </div>
            )}
          </CardContent>
        </Card>
      )}

      <Card>
        <CardHeader>
          <h2 className="text-lg font-semibold">Products</h2>
        </CardHeader>
        <CardContent className="p-0">
          {loading ? (
            <div className="p-lg text-center text-gray-500">
              <Clock className="h-8 w-8 mx-auto mb-sm animate-spin" />
              Loading products...
            </div>
          ) : projects.length === 0 ? (
            <div className="p-lg text-center text-gray-500">
              <Rocket className="h-8 w-8 mx-auto mb-sm" />
              No products yet. Create your first product to get started.
            </div>
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
                {projects.map((project) => (
                  <TableRow key={project.id}>
                    <TableCell className="font-medium">{project.name}</TableCell>
                    <TableCell className="text-gray-600 max-w-xs truncate">
                      {project.description || "-"}
                    </TableCell>
                    <TableCell>{getStatusBadge(project.status)}</TableCell>
                    <TableCell>
                      {new Date(project.created_at).toLocaleDateString()}
                    </TableCell>
                    <TableCell>
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() =>
                          (window.location.href = `/create/${project.id}`)
                        }
                      >
                        <Eye className="h-4 w-4 mr-1" />
                        Details
                      </Button>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>

      <Modal open={showModal} onClose={() => setShowModal(false)}>
        <ModalHeader>
          <h2 className="text-lg font-semibold">Create New Product</h2>
        </ModalHeader>
        <ModalContent>
          <div className="space-y-md">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-xs">
                Product Name *
              </label>
              <Input
                placeholder="My SaaS Product"
                value={formData.name}
                onChange={(e) =>
                  setFormData({ ...formData, name: e.target.value })
                }
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-xs">
                Description
              </label>
              <Input
                placeholder="A brief description of your product"
                value={formData.description}
                onChange={(e) =>
                  setFormData({ ...formData, description: e.target.value })
                }
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-xs">
                Requirements *
              </label>
              <textarea
                className="w-full px-sm py-sm border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent min-h-[120px]"
                placeholder="Describe what your product should do. Be as detailed as possible about features, user flows, and technical requirements."
                value={formData.requirements}
                onChange={(e) =>
                  setFormData({ ...formData, requirements: e.target.value })
                }
              />
              <p className="text-xs text-gray-500 mt-xs">
                The AI agents will interpret these requirements to create your product.
              </p>
            </div>
          </div>
        </ModalContent>
        <ModalFooter>
          <Button variant="outline" onClick={() => setShowModal(false)}>
            Cancel
          </Button>
          <Button onClick={handleCreateProduct} disabled={creating}>
            {creating ? (
              <>
                <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                Creating...
              </>
            ) : (
              <>
                <Rocket className="h-4 w-4 mr-2" />
                Create Product
              </>
            )}
          </Button>
        </ModalFooter>
      </Modal>
    </div>
  );
}
