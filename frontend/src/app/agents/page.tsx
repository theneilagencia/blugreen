"use client";

import { Alert } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { api } from "@/lib/api";
import {
  Bot,
  CheckCircle,
  Code,
  Cpu,
  Layout,
  Server,
  Shield,
  Sparkles,
} from "lucide-react";
import { useEffect, useState } from "react";

interface AgentType {
  type: string;
  name: string;
  description: string;
}

interface AgentCapabilities {
  capabilities: string[];
  restrictions: string[];
}

export default function AgentsPage() {
  const [agentTypes, setAgentTypes] = useState<AgentType[]>([]);
  const [selectedAgent, setSelectedAgent] = useState<string | null>(null);
  const [capabilities, setCapabilities] = useState<AgentCapabilities | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    loadAgentTypes();
  }, []);

  useEffect(() => {
    if (selectedAgent) {
      loadCapabilities(selectedAgent);
    }
  }, [selectedAgent]);

  async function loadAgentTypes() {
    try {
      setLoading(true);
      const data = await api.agents.types();
      setAgentTypes(data);
      if (data.length > 0) {
        setSelectedAgent(data[0].type);
      }
      setError(null);
    } catch (err) {
      setError("Failed to load agents. Make sure the backend is running.");
    } finally {
      setLoading(false);
    }
  }

  async function loadCapabilities(type: string) {
    try {
      const data = await api.agents.capabilities(type);
      setCapabilities(data);
    } catch (err) {
      setCapabilities(null);
    }
  }

  function getAgentIcon(type: string) {
    const icons: Record<string, React.ReactNode> = {
      architect: <Cpu className="h-6 w-6" />,
      backend: <Server className="h-6 w-6" />,
      frontend: <Layout className="h-6 w-6" />,
      infra: <Code className="h-6 w-6" />,
      qa: <Shield className="h-6 w-6" />,
      ux: <Sparkles className="h-6 w-6" />,
      ui_refinement: <Sparkles className="h-6 w-6" />,
    };
    return icons[type] || <Bot className="h-6 w-6" />;
  }

  return (
    <div className="max-w-7xl mx-auto px-md py-lg">
      <div className="mb-lg">
        <h1 className="text-2xl font-bold text-gray-900">Agents</h1>
        <p className="text-gray-600 mt-xs">
          Specialized agents that power the autonomous engineering platform
        </p>
      </div>

      {error && (
        <Alert variant="error" className="mb-lg">
          {error}
        </Alert>
      )}

      {loading ? (
        <div className="text-center text-gray-500 py-lg">Loading agents...</div>
      ) : (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-lg">
          <div className="lg:col-span-1">
            <Card>
              <CardHeader>
                <h2 className="text-lg font-semibold">Agent Types</h2>
              </CardHeader>
              <CardContent className="p-0">
                <div className="divide-y divide-gray-200">
                  {agentTypes.map((agent) => (
                    <button
                      key={agent.type}
                      className={`w-full p-md text-left flex items-center gap-md transition-colors ${
                        selectedAgent === agent.type
                          ? "bg-primary-50 border-l-4 border-primary-500"
                          : "hover:bg-gray-50"
                      }`}
                      onClick={() => setSelectedAgent(agent.type)}
                    >
                      <div
                        className={`p-sm rounded-md ${
                          selectedAgent === agent.type
                            ? "bg-primary-100 text-primary-600"
                            : "bg-gray-100 text-gray-600"
                        }`}
                      >
                        {getAgentIcon(agent.type)}
                      </div>
                      <div>
                        <p className="font-medium">{agent.name}</p>
                        <p className="text-sm text-gray-500 line-clamp-1">
                          {agent.description}
                        </p>
                      </div>
                    </button>
                  ))}
                </div>
              </CardContent>
            </Card>
          </div>

          <div className="lg:col-span-2">
            {selectedAgent && capabilities && (
              <div className="space-y-lg">
                <Card>
                  <CardHeader>
                    <div className="flex items-center gap-md">
                      <div className="p-sm bg-primary-100 text-primary-600 rounded-md">
                        {getAgentIcon(selectedAgent)}
                      </div>
                      <div>
                        <h2 className="text-lg font-semibold">
                          {agentTypes.find((a) => a.type === selectedAgent)?.name}
                        </h2>
                        <p className="text-gray-500">
                          {agentTypes.find((a) => a.type === selectedAgent)?.description}
                        </p>
                      </div>
                    </div>
                  </CardHeader>
                </Card>

                <Card>
                  <CardHeader>
                    <h3 className="font-semibold flex items-center gap-sm">
                      <CheckCircle className="h-5 w-5 text-green-500" />
                      Capabilities
                    </h3>
                  </CardHeader>
                  <CardContent>
                    <div className="flex flex-wrap gap-sm">
                      {capabilities.capabilities.map((cap) => (
                        <Badge key={cap} variant="success">
                          {cap.replace(/_/g, " ")}
                        </Badge>
                      ))}
                    </div>
                  </CardContent>
                </Card>

                <Card>
                  <CardHeader>
                    <h3 className="font-semibold flex items-center gap-sm">
                      <Shield className="h-5 w-5 text-danger-500" />
                      Restrictions
                    </h3>
                  </CardHeader>
                  <CardContent>
                    <div className="flex flex-wrap gap-sm">
                      {capabilities.restrictions.map((restriction) => (
                        <Badge key={restriction} variant="danger">
                          {restriction.replace(/_/g, " ")}
                        </Badge>
                      ))}
                    </div>
                  </CardContent>
                </Card>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
