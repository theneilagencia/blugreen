"use client";

/**
 * Wizard do Modo Guiado (CAMADA 1)
 * 
 * Wizard de perguntas em linguagem humana.
 * Máximo 3 perguntas por etapa.
 */

import { use, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";

interface GuidedQuestion {
  id: string;
  text: string;
  placeholder: string;
  help_text?: string;
  required: boolean;
  field_type: string;
}

interface GuidedStep {
  step_number: number;
  title: string;
  description: string;
  questions: GuidedQuestion[];
  can_skip: boolean;
}

interface GuidedSession {
  id: number;
  intent: string;
  status: string;
  user_responses: Record<string, string>;
  system_inferences: Record<string, any>;
}

export default function GuidedWizardPage({ params }: { params: Promise<{ id: string }> }) {
  const resolvedParams = use(params);
  const sessionId = resolvedParams.id;
  const router = useRouter();
  
  const [session, setSession] = useState<GuidedSession | null>(null);
  const [steps, setSteps] = useState<GuidedStep[]>([]);
  const [currentStepIndex, setCurrentStepIndex] = useState(0);
  const [responses, setResponses] = useState<Record<string, string>>({});
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    loadSession();
  }, [sessionId]);

  const loadSession = async () => {
    try {
      // Carregar sessão
      const sessionRes = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/guided/${sessionId}`);
      if (!sessionRes.ok) throw new Error("Sessão não encontrada");
      const sessionData = await sessionRes.json();
      setSession(sessionData);
      setResponses(sessionData.user_responses || {});

      // Carregar etapas
      const stepsRes = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/guided/${sessionId}/steps`);
      if (!stepsRes.ok) throw new Error("Erro ao carregar etapas");
      const stepsData = await stepsRes.json();
      setSteps(stepsData);

      setLoading(false);
    } catch (error) {
      console.error("Erro:", error);
      alert("Ops! Não consegui carregar a sessão.");
      router.push("/guided");
    }
  };

  const handleInputChange = (questionId: string, value: string) => {
    setResponses(prev => ({
      ...prev,
      [questionId]: value
    }));
  };

  const handleNext = async () => {
    const currentStep = steps[currentStepIndex];
    
    // Validar respostas obrigatórias
    const missingRequired = currentStep.questions
      .filter(q => q.required && !responses[q.id])
      .map(q => q.text);

    if (missingRequired.length > 0) {
      alert(`Por favor, responda: ${missingRequired.join(", ")}`);
      return;
    }

    // Se é a última etapa, ir para resumo
    if (currentStepIndex === steps.length - 1) {
      await saveAndShowSummary();
    } else {
      // Próxima etapa
      setCurrentStepIndex(prev => prev + 1);
    }
  };

  const handleBack = () => {
    if (currentStepIndex > 0) {
      setCurrentStepIndex(prev => prev - 1);
    }
  };

  const saveAndShowSummary = async () => {
    setSubmitting(true);

    try {
      // Salvar respostas
      const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/guided/${sessionId}`, {
        method: "PATCH",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          user_responses: responses,
          status: "confirming"
        }),
      });

      if (!response.ok) {
        throw new Error("Erro ao salvar respostas");
      }

      // Redirecionar para resumo
      router.push(`/guided/${sessionId}/summary`);
    } catch (error) {
      console.error("Erro:", error);
      alert("Ops! Algo deu errado ao salvar. Tente novamente.");
      setSubmitting(false);
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100 flex items-center justify-center">
        <div className="text-center">
          <div className="inline-block animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
          <p className="mt-4 text-gray-600">Carregando...</p>
        </div>
      </div>
    );
  }

  if (!session || steps.length === 0) {
    return null;
  }

  const currentStep = steps[currentStepIndex];
  const progress = ((currentStepIndex + 1) / steps.length) * 100;

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100 py-12 px-4">
      <div className="max-w-3xl mx-auto">
        {/* Progress Bar */}
        <div className="mb-8">
          <div className="flex justify-between items-center mb-2">
            <span className="text-sm text-gray-600">
              Etapa {currentStepIndex + 1} de {steps.length}
            </span>
            <span className="text-sm text-gray-600">
              {Math.round(progress)}% completo
            </span>
          </div>
          <div className="w-full bg-gray-200 rounded-full h-2">
            <div
              className="bg-blue-600 h-2 rounded-full transition-all duration-300"
              style={{ width: `${progress}%` }}
            ></div>
          </div>
        </div>

        {/* Step Card */}
        <Card className="p-8 bg-white shadow-lg">
          {/* Step Header */}
          <div className="mb-8">
            <h2 className="text-3xl font-bold text-gray-900 mb-2">
              {currentStep.title}
            </h2>
            <p className="text-gray-600">
              {currentStep.description}
            </p>
          </div>

          {/* Questions */}
          <div className="space-y-6">
            {currentStep.questions.map((question) => (
              <div key={question.id}>
                <label className="block text-lg font-medium text-gray-800 mb-2">
                  {question.text}
                  {question.required && <span className="text-red-500 ml-1">*</span>}
                </label>
                
                {question.field_type === "textarea" ? (
                  <textarea
                    className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                    placeholder={question.placeholder}
                    value={responses[question.id] || ""}
                    onChange={(e) => handleInputChange(question.id, e.target.value)}
                    rows={4}
                  />
                ) : question.field_type === "select" ? (
                  <select
                    className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                    value={responses[question.id] || ""}
                    onChange={(e) => handleInputChange(question.id, e.target.value)}
                  >
                    <option value="">Selecione...</option>
                    <option value="Sim">Sim</option>
                    <option value="Não">Não</option>
                  </select>
                ) : (
                  <Input
                    type="text"
                    placeholder={question.placeholder}
                    value={responses[question.id] || ""}
                    onChange={(e) => handleInputChange(question.id, e.target.value)}
                    className="w-full px-4 py-3"
                  />
                )}

                {question.help_text && (
                  <p className="mt-2 text-sm text-gray-500">
                    💡 {question.help_text}
                  </p>
                )}
              </div>
            ))}
          </div>

          {/* Navigation */}
          <div className="mt-8 flex justify-between items-center">
            <Button
              variant="outline"
              onClick={handleBack}
              disabled={currentStepIndex === 0 || submitting}
            >
              ← Voltar
            </Button>

            <Button
              onClick={handleNext}
              disabled={submitting}
              className="bg-blue-600 hover:bg-blue-700 text-white px-8"
            >
              {submitting ? (
                "Salvando..."
              ) : currentStepIndex === steps.length - 1 ? (
                "Ver Resumo →"
              ) : (
                "Próximo →"
              )}
            </Button>
          </div>

          {/* Skip Option */}
          {currentStep.can_skip && (
            <div className="mt-4 text-center">
              <button
                className="text-sm text-gray-500 hover:text-gray-700 underline"
                onClick={() => setCurrentStepIndex(prev => prev + 1)}
                disabled={submitting}
              >
                Pular esta etapa
              </button>
            </div>
          )}
        </Card>

        {/* Help Box */}
        <div className="mt-6 bg-blue-50 rounded-lg p-4 border border-blue-200">
          <p className="text-sm text-blue-800 text-center">
            ℹ️ Suas respostas me ajudam a criar exatamente o que você precisa.
          </p>
        </div>
      </div>
    </div>
  );
}
