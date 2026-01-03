"use client";

import { Alert } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { api, Project } from "@/lib/api";
import {
  Activity,
  CheckCircle,
  Clock,
  FolderOpen,
  Plus,
  XCircle,
} from "lucide-react";
import { useEffect, useState } from "react";

export default function Dashboard() {
  const [projects, setProjects] = useState<Project[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

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

  const stats = {
    total: projects.length,
    inProgress: projects.filter((p) => p.status === "in_progress").length,
    deployed: projects.filter((p) => p.status === "deployed").length,
    failed: projects.filter((p) => p.status === "failed").length,
  };

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
          <h1 className="text-2xl font-bold text-gray-900">Dashboard</h1>
          <p className="text-gray-600 mt-xs">
            Overview of your autonomous engineering platform
          </p>
        </div>
        <Button onClick={() => (window.location.href = "/create")}>
          <Plus className="h-4 w-4 mr-2" />
          Create Product
        </Button>
      </div>

      {error && (
        <Alert variant="error" className="mb-lg">
          {error}
        </Alert>
      )}

      <div className="grid grid-cols-1 md:grid-cols-4 gap-md mb-lg">
        <Card>
          <CardContent className="flex items-center gap-md">
            <div className="p-sm bg-gray-100 rounded-md">
              <FolderOpen className="h-6 w-6 text-gray-600" />
            </div>
            <div>
              <p className="text-sm text-gray-600">Total Projects</p>
              <p className="text-2xl font-bold">{stats.total}</p>
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="flex items-center gap-md">
            <div className="p-sm bg-yellow-100 rounded-md">
              <Activity className="h-6 w-6 text-yellow-600" />
            </div>
            <div>
              <p className="text-sm text-gray-600">In Progress</p>
              <p className="text-2xl font-bold">{stats.inProgress}</p>
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="flex items-center gap-md">
            <div className="p-sm bg-green-100 rounded-md">
              <CheckCircle className="h-6 w-6 text-green-600" />
            </div>
            <div>
              <p className="text-sm text-gray-600">Deployed</p>
              <p className="text-2xl font-bold">{stats.deployed}</p>
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="flex items-center gap-md">
            <div className="p-sm bg-danger-100 rounded-md">
              <XCircle className="h-6 w-6 text-danger-600" />
            </div>
            <div>
              <p className="text-sm text-gray-600">Failed</p>
              <p className="text-2xl font-bold">{stats.failed}</p>
            </div>
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader>
          <h2 className="text-lg font-semibold">Recent Projects</h2>
        </CardHeader>
        <CardContent className="p-0">
          {loading ? (
            <div className="p-lg text-center text-gray-500">
              <Clock className="h-8 w-8 mx-auto mb-sm animate-spin" />
              Loading projects...
            </div>
          ) : projects.length === 0 ? (
            <div className="p-lg text-center text-gray-500">
              <FolderOpen className="h-8 w-8 mx-auto mb-sm" />
              No projects yet. Create your first project to get started.
            </div>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Name</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead>Created</TableHead>
                  <TableHead>Updated</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {projects.slice(0, 5).map((project) => (
                  <TableRow
                    key={project.id}
                    hoverable
                    onClick={() =>
                      (window.location.href = `/projects/${project.id}`)
                    }
                  >
                    <TableCell className="font-medium">
                      {project.name}
                    </TableCell>
                    <TableCell>{getStatusBadge(project.status)}</TableCell>
                    <TableCell>
                      {new Date(project.created_at).toLocaleDateString()}
                    </TableCell>
                    <TableCell>
                      {new Date(project.updated_at).toLocaleDateString()}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
