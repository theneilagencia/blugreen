"use client";

import { Alert } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Modal, ModalContent, ModalFooter, ModalHeader } from "@/components/ui/modal";
import {
  api,
  DeploymentHistory,
  DeploymentStatus,
  ProductCreationStatus,
  Project,
} from "@/lib/api";
import {
  ArrowLeft,
  CheckCircle,
  Clock,
  History,
  Loader2,
  RefreshCw,
  Rocket,
  RotateCcw,
  XCircle,
} from "lucide-react";
import { useParams } from "next/navigation";
import { useEffect, useState } from "react";

export default function ProductDetailsPage() {
  const params = useParams();
  const projectId = Number(params.id);

  const [project, setProject] = useState<Project | null>(null);
  const [creationStatus, setCreationStatus] = useState<ProductCreationStatus | null>(null);
  const [deploymentStatus, setDeploymentStatus] = useState<DeploymentStatus | null>(null);
  const [deploymentHistory, setDeploymentHistory] = useState<DeploymentHistory | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [showDeployModal, setShowDeployModal] = useState(false);
  const [deploying, setDeploying] = useState(false);
  const [deployForm, setDeployForm] = useState({
    docker_image: "",
    env_vars: "",
  });

  const [rollingBack, setRollingBack] = useState(false);
  const [pollingCreation, setPollingCreation] = useState(false);

  useEffect(() => {
    loadProjectData();
  }, [projectId]);

  useEffect(() => {
    let interval: NodeJS.Timeout | null = null;

    if (pollingCreation && creationStatus) {
      interval = setInterval(async () => {
        try {
          const status = await api.product.status(projectId);
          setCreationStatus(status);

          if (
            status.creation_status === "completed" ||
            status.creation_status === "error" ||
            status.creation_status === "failed"
          ) {
            setPollingCreation(false);
            loadProjectData();
          }
        } catch (err) {
          console.error("Failed to fetch creation status:", err);
        }
      }, 2000);
    }

    return () => {
      if (interval) clearInterval(interval);
    };
  }, [pollingCreation, projectId]);

  async function loadProjectData() {
    try {
      setLoading(true);
      setError(null);

      const [projectData, statusData] = await Promise.all([
        api.projects.get(projectId),
        api.product.status(projectId),
      ]);

      setProject(projectData);
      setCreationStatus(statusData);

      if (
        statusData.creation_status !== "completed" &&
        statusData.creation_status !== "error" &&
        statusData.creation_status !== "failed" &&
        statusData.creation_status !== "unknown"
      ) {
        setPollingCreation(true);
      }

      try {
        const [deployStatus, deployHistory] = await Promise.all([
          api.product.deploymentStatus(projectId),
          api.product.deploymentHistory(projectId),
        ]);
        setDeploymentStatus(deployStatus);
        setDeploymentHistory(deployHistory);
      } catch {
        // Deployment info may not be available yet
      }
    } catch (err) {
      setError("Failed to load project data. Make sure the backend is running.");
    } finally {
      setLoading(false);
    }
  }

  async function handleDeploy() {
    if (!deployForm.docker_image) {
      setError("Docker image is required");
      return;
    }

    try {
      setDeploying(true);
      setError(null);

      let envVars: Record<string, string> | undefined;
      if (deployForm.env_vars.trim()) {
        try {
          envVars = JSON.parse(deployForm.env_vars);
        } catch {
          setError("Invalid JSON for environment variables");
          setDeploying(false);
          return;
        }
      }

      await api.product.deploy(projectId, {
        docker_image: deployForm.docker_image,
        environment_variables: envVars,
      });

      setShowDeployModal(false);
      setDeployForm({ docker_image: "", env_vars: "" });
      loadProjectData();
    } catch (err) {
      setError("Failed to deploy. Please try again.");
    } finally {
      setDeploying(false);
    }
  }

  async function handleRollback() {
    if (!confirm("Are you sure you want to rollback this deployment? This will restore the previous version.")) {
      return;
    }

    try {
      setRollingBack(true);
      setError(null);

      await api.product.rollback(projectId);
      loadProjectData();
    } catch (err) {
      setError("Failed to rollback. Please try again.");
    } finally {
      setRollingBack(false);
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
      started: "primary",
      completed: "success",
      error: "danger",
      unknown: "default",
    };
    return <Badge variant={variants[status] || "default"}>{status}</Badge>;
  }

  function getStepIcon(step: { success: boolean }) {
    if (step.success) {
      return <CheckCircle className="h-4 w-4 text-green-500" />;
    }
    return <XCircle className="h-4 w-4 text-red-500" />;
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
        <Alert variant="error">Project not found</Alert>
        <Button
          variant="outline"
          className="mt-md"
          onClick={() => (window.location.href = "/create")}
        >
          <ArrowLeft className="h-4 w-4 mr-2" />
          Back to Products
        </Button>
      </div>
    );
  }

  return (
    <div className="max-w-7xl mx-auto px-md py-lg">
      <div className="flex items-center gap-md mb-lg">
        <Button
          variant="outline"
          size="sm"
          onClick={() => (window.location.href = "/create")}
        >
          <ArrowLeft className="h-4 w-4 mr-1" />
          Back
        </Button>
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
              <h2 className="text-lg font-semibold">Creation Status</h2>
              <Button variant="outline" size="sm" onClick={loadProjectData}>
                <RefreshCw className="h-4 w-4" />
              </Button>
            </div>
          </CardHeader>
          <CardContent>
            {creationStatus ? (
              <div className="space-y-md">
                <div className="flex items-center gap-md">
                  <span className="text-sm text-gray-600">Status:</span>
                  {getStatusBadge(creationStatus.creation_status)}
                  {pollingCreation && (
                    <Loader2 className="h-4 w-4 animate-spin text-primary-600" />
                  )}
                </div>

                {creationStatus.error && (
                  <Alert variant="error">{creationStatus.error}</Alert>
                )}

                {creationStatus.steps && creationStatus.steps.length > 0 && (
                  <div className="space-y-sm">
                    <h3 className="text-sm font-medium text-gray-700">Steps:</h3>
                    <div className="space-y-xs max-h-64 overflow-y-auto">
                      {creationStatus.steps.map((step, index) => (
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
              </div>
            ) : (
              <p className="text-gray-500">No creation status available</p>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <div className="flex items-center justify-between">
              <h2 className="text-lg font-semibold">Deployment</h2>
              <div className="flex gap-sm">
                <Button
                  variant="outline"
                  size="sm"
                  onClick={handleRollback}
                  disabled={rollingBack || project.status !== "deployed"}
                >
                  {rollingBack ? (
                    <Loader2 className="h-4 w-4 animate-spin" />
                  ) : (
                    <RotateCcw className="h-4 w-4" />
                  )}
                </Button>
                <Button size="sm" onClick={() => setShowDeployModal(true)}>
                  <Rocket className="h-4 w-4 mr-1" />
                  Deploy
                </Button>
              </div>
            </div>
          </CardHeader>
          <CardContent>
            {deploymentStatus ? (
              <div className="space-y-md">
                <div className="grid grid-cols-2 gap-sm text-sm">
                  <div>
                    <span className="text-gray-600">Status:</span>
                    <span className="ml-sm font-medium">{deploymentStatus.status}</span>
                  </div>
                  {deploymentStatus.url && (
                    <div>
                      <span className="text-gray-600">URL:</span>
                      <a
                        href={deploymentStatus.url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="ml-sm text-primary-600 hover:underline"
                      >
                        {deploymentStatus.url}
                      </a>
                    </div>
                  )}
                  {deploymentStatus.health && (
                    <div>
                      <span className="text-gray-600">Health:</span>
                      <span className="ml-sm font-medium">{deploymentStatus.health}</span>
                    </div>
                  )}
                  {deploymentStatus.last_deployment && (
                    <div>
                      <span className="text-gray-600">Last Deploy:</span>
                      <span className="ml-sm">
                        {new Date(deploymentStatus.last_deployment).toLocaleString()}
                      </span>
                    </div>
                  )}
                </div>
              </div>
            ) : (
              <p className="text-gray-500">No deployment yet. Deploy your product to see status.</p>
            )}
          </CardContent>
        </Card>

        <Card className="lg:col-span-2">
          <CardHeader>
            <h2 className="text-lg font-semibold flex items-center gap-2">
              <History className="h-5 w-5" />
              Deployment History
            </h2>
          </CardHeader>
          <CardContent>
            {deploymentHistory && deploymentHistory.deployments.length > 0 ? (
              <div className="space-y-sm">
                {deploymentHistory.deployments.map((deployment, index) => (
                  <div
                    key={index}
                    className="flex items-center justify-between p-sm bg-gray-50 rounded-md"
                  >
                    <div className="flex items-center gap-md">
                      <span className="text-sm text-gray-600">
                        {new Date(deployment.timestamp).toLocaleString()}
                      </span>
                      {getStatusBadge(deployment.status)}
                    </div>
                    <div className="flex items-center gap-md text-sm">
                      {deployment.docker_image && (
                        <span className="text-gray-600 font-mono text-xs">
                          {deployment.docker_image}
                        </span>
                      )}
                      {deployment.url && (
                        <a
                          href={deployment.url}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="text-primary-600 hover:underline"
                        >
                          View
                        </a>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <p className="text-gray-500 text-center py-md">
                No deployment history yet.
              </p>
            )}
          </CardContent>
        </Card>
      </div>

      <Modal open={showDeployModal} onClose={() => setShowDeployModal(false)}>
        <ModalHeader>
          <h2 className="text-lg font-semibold">Deploy Product</h2>
        </ModalHeader>
        <ModalContent>
          <div className="space-y-md">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-xs">
                Docker Image *
              </label>
              <Input
                placeholder="myregistry/myapp:latest"
                value={deployForm.docker_image}
                onChange={(e) =>
                  setDeployForm({ ...deployForm, docker_image: e.target.value })
                }
              />
              <p className="text-xs text-gray-500 mt-xs">
                The Docker image to deploy (e.g., ghcr.io/org/app:v1.0.0)
              </p>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-xs">
                Environment Variables (JSON)
              </label>
              <textarea
                className="w-full px-sm py-sm border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent min-h-[100px] font-mono text-sm"
                placeholder='{"DATABASE_URL": "...", "API_KEY": "..."}'
                value={deployForm.env_vars}
                onChange={(e) =>
                  setDeployForm({ ...deployForm, env_vars: e.target.value })
                }
              />
              <p className="text-xs text-gray-500 mt-xs">
                Optional. Provide environment variables as a JSON object.
              </p>
            </div>
          </div>
        </ModalContent>
        <ModalFooter>
          <Button variant="outline" onClick={() => setShowDeployModal(false)}>
            Cancel
          </Button>
          <Button onClick={handleDeploy} disabled={deploying}>
            {deploying ? (
              <>
                <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                Deploying...
              </>
            ) : (
              <>
                <Rocket className="h-4 w-4 mr-2" />
                Deploy
              </>
            )}
          </Button>
        </ModalFooter>
      </Modal>
    </div>
  );
}
