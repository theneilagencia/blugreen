"use client";

import { Alert } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { api } from "@/lib/api";
import { CheckCircle, Palette, Shield, XCircle } from "lucide-react";
import { useEffect, useState } from "react";

interface UXRules {
  rules: { id: string; rule: string; required: boolean }[];
  criteria: { id: string; name: string; description: string; weight: number }[];
  threshold: number;
}

interface DesignSystem {
  tokens: {
    spacing: Record<string, number>;
    border_radius: Record<string, number>;
  };
  allowed_components: string[];
  criteria: { id: string; name: string; description: string; weight: number }[];
}

export default function QualityPage() {
  const [uxRules, setUxRules] = useState<UXRules | null>(null);
  const [designSystem, setDesignSystem] = useState<DesignSystem | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    loadQualityData();
  }, []);

  async function loadQualityData() {
    try {
      setLoading(true);
      const [uxData, dsData] = await Promise.all([
        api.quality.uxRules(),
        api.quality.designSystem(),
      ]);
      setUxRules(uxData);
      setDesignSystem(dsData);
      setError(null);
    } catch (err) {
      setError("Failed to load quality data. Make sure the backend is running.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="max-w-7xl mx-auto px-md py-lg">
      <div className="mb-lg">
        <h1 className="text-2xl font-bold text-gray-900">Quality Gates</h1>
        <p className="text-gray-600 mt-xs">
          UX rules, UI quality criteria, and design system specifications
        </p>
      </div>

      {error && (
        <Alert variant="error" className="mb-lg">
          {error}
        </Alert>
      )}

      {loading ? (
        <div className="text-center text-gray-500 py-lg">Loading quality data...</div>
      ) : (
        <div className="space-y-lg">
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-lg">
            <Card>
              <CardHeader>
                <h2 className="text-lg font-semibold flex items-center gap-sm">
                  <Shield className="h-5 w-5 text-primary-500" />
                  UX Rules Engine
                </h2>
                <p className="text-sm text-gray-500">
                  Mandatory rules that all UX must follow
                </p>
              </CardHeader>
              <CardContent>
                {uxRules && (
                  <div className="space-y-md">
                    <div>
                      <p className="text-sm text-gray-500 mb-sm">
                        Passing threshold: {(uxRules.threshold * 100).toFixed(0)}%
                      </p>
                    </div>
                    <div className="space-y-sm">
                      {uxRules.rules.map((rule) => (
                        <div
                          key={rule.id}
                          className="flex items-start gap-sm p-sm bg-gray-50 rounded-md"
                        >
                          {rule.required ? (
                            <CheckCircle className="h-5 w-5 text-green-500 flex-shrink-0 mt-0.5" />
                          ) : (
                            <XCircle className="h-5 w-5 text-gray-400 flex-shrink-0 mt-0.5" />
                          )}
                          <div>
                            <p className="font-medium">{rule.rule}</p>
                            <p className="text-sm text-gray-500">
                              {rule.required ? "Required" : "Optional"}
                            </p>
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <h2 className="text-lg font-semibold flex items-center gap-sm">
                  <Palette className="h-5 w-5 text-primary-500" />
                  UI Quality Criteria
                </h2>
                <p className="text-sm text-gray-500">
                  Criteria for evaluating UI quality
                </p>
              </CardHeader>
              <CardContent>
                {designSystem && (
                  <div className="space-y-sm">
                    {designSystem.criteria.map((criterion) => (
                      <div
                        key={criterion.id}
                        className="p-sm bg-gray-50 rounded-md"
                      >
                        <div className="flex items-center justify-between mb-xs">
                          <p className="font-medium">{criterion.name}</p>
                          <Badge variant="primary">
                            {(criterion.weight * 100).toFixed(0)}%
                          </Badge>
                        </div>
                        <p className="text-sm text-gray-500">
                          {criterion.description}
                        </p>
                      </div>
                    ))}
                  </div>
                )}
              </CardContent>
            </Card>
          </div>

          <Card>
            <CardHeader>
              <h2 className="text-lg font-semibold">Design System</h2>
              <p className="text-sm text-gray-500">
                Design tokens and allowed components
              </p>
            </CardHeader>
            <CardContent>
              {designSystem && (
                <div className="grid grid-cols-1 md:grid-cols-3 gap-lg">
                  <div>
                    <h3 className="font-semibold mb-sm">Spacing Tokens</h3>
                    <div className="space-y-xs">
                      {Object.entries(designSystem.tokens.spacing).map(
                        ([name, value]) => (
                          <div
                            key={name}
                            className="flex items-center justify-between p-sm bg-gray-50 rounded-md"
                          >
                            <span className="font-mono text-sm">{name}</span>
                            <span className="text-gray-500">{value}px</span>
                          </div>
                        )
                      )}
                    </div>
                  </div>

                  <div>
                    <h3 className="font-semibold mb-sm">Border Radius</h3>
                    <div className="space-y-xs">
                      {Object.entries(designSystem.tokens.border_radius).map(
                        ([name, value]) => (
                          <div
                            key={name}
                            className="flex items-center justify-between p-sm bg-gray-50 rounded-md"
                          >
                            <span className="font-mono text-sm">{name}</span>
                            <span className="text-gray-500">{value}px</span>
                          </div>
                        )
                      )}
                    </div>
                  </div>

                  <div>
                    <h3 className="font-semibold mb-sm">Allowed Components</h3>
                    <div className="flex flex-wrap gap-sm">
                      {designSystem.allowed_components.map((component) => (
                        <Badge key={component} variant="primary">
                          {component}
                        </Badge>
                      ))}
                    </div>
                  </div>
                </div>
              )}
            </CardContent>
          </Card>
        </div>
      )}
    </div>
  );
}
