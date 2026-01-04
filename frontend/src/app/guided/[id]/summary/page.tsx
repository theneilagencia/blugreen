"use client";

/**
 * Resumo do Modo Guiado com Captura de Intenção (CAMADA 1 + CAMADA 2 + CAMADA 3)
 * 
 * Após confirmação, cria um ProjectIntent (contrato imutável).
 */

import { use, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";

interface Summary {
  session_id: number;
  intent: string;
  summary: string;
  ready_to_execute: boolean;
}

interface ProjectIntent {
  id: number;
  intent_type: string;
  status: string;
  product_name: string;
  business_goal: string;
  success_criteria: string;
  constraints: string;
  risk_level: string;
}

export default function GuidedSummaryPageV2({ params }: { params: Promise<{ id: string }> }) {
  const resolvedParams = use(params);
  const sessionId = resolvedParams.id;
  const router = useRouter();
  
  const [summary, setSummary] = useState<Summary | null>(null);
  const [intent, setIntent] = useState<ProjectIntent | null>(null);
  const [loading, setLoading] = useState(true);
  const [confirming, setConfirming] = useState(false);
  const [step, setStep] = useState<"summary" | "intent_created" | "executing">("summary");

  useEffect(() => {
    loadSummary();
  }, [sessionId]);

  const loadSummary = async () => {
    try {
      const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/guided/${sessionId}/summary`);
      if (!response.ok) throw new Error("Erro ao carregar resumo");
      
      const data = await response.json();
      setSummary(data);
      setLoading(false);
    } catch (error) {
      console.error("Erro:", error);
      alert("Ops! Não consegui carregar o resumo.");
      router.push("/guided");
    }
  };

  const handleConfirm = async () => {
    setConfirming(true);

    try {
      // PASSO 1: Criar ProjectIntent (CAMADA 2)
      const intentResponse = await fetch(
        `${process.env.NEXT_PUBLIC_API_URL}/intent/from-guided/${sessionId}`,
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
        }
      );

      if (!intentResponse.ok) {
        throw new Error("Erro ao criar intenção");
      }

      const intentData = await intentResponse.json();
      setIntent(intentData);
      setStep("intent_created");

      // PASSO 2: Validar intenção
      const validateResponse = await fetch(
        `${process.env.NEXT_PUBLIC_API_URL}/intent/${intentData.id}/validate`,
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({
            validated_by: "user"
          }),
        }
      );

      if (!validateResponse.ok) {
        throw new Error("Erro ao validar intenção");
      }

      // PASSO 3: Congelar intenção (tornar imutável)
      const freezeResponse = await fetch(
        `${process.env.NEXT_PUBLIC_API_URL}/intent/${intentData.id}/freeze`,
        {
          method: "POST",
        }
      );

      if (!freezeResponse.ok) {
        throw new Error("Erro ao congelar intenção");
      }

      const frozenIntent = await freezeResponse.json();
      setIntent(frozenIntent);

      // PASSO 4: Atualizar sessão guiada para executando
      await fetch(`${process.env.NEXT_PUBLIC_API_URL}/guided/${sessionId}`, {
        method: "PATCH",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          status: "executing"
        }),
      });

      setStep("executing");

      // TODO: Integrar com CAMADA 4 (Loop Autônomo)
      setTimeout(() => {
        alert("Intenção criada e congelada! Agora vou começar a trabalhar no seu produto.");
        router.push("/projects");
      }, 2000);

    } catch (error) {
      console.error("Erro:", error);
      alert("Ops! Algo deu errado. Tente novamente.");
      setConfirming(false);
    }
  };

  const handleCancel = () => {
    if (confirm("Tem certeza que quer cancelar? Você vai perder todas as respostas.")) {
      router.push("/guided");
    }
  };

  const handleEdit = () => {
    router.push(`/guided/${sessionId}`);
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100 flex items-center justify-center">
        <div className="text-center">
          <div className="inline-block animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
          <p className="mt-4 text-gray-600">Preparando resumo...</p>
        </div>
      </div>
    );
  }

  if (!summary) {
    return null;
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100 py-12 px-4">
      <div className="max-w-3xl mx-auto">
        {/* Header */}
        <div className="text-center mb-8">
          <h1 className="text-4xl font-bold text-gray-900 mb-2">
            {step === "summary" && "Resumo do Plano 📋"}
            {step === "intent_created" && "Intenção Criada ✅"}
            {step === "executing" && "Executando 🚀"}
          </h1>
          <p className="text-lg text-gray-600">
            {step === "summary" && "Veja o que eu vou fazer para você"}
            {step === "intent_created" && "Seu contrato foi criado e congelado"}
            {step === "executing" && "Estou trabalhando no seu produto"}
          </p>
        </div>

        {/* Summary Card */}
        {step === "summary" && (
          <>
            <Card className="p-8 bg-white shadow-lg mb-6">
              <div className="prose prose-lg max-w-none">
                {summary.summary.split('\n').map((line, index) => {
                  if (line.trim() === '') return <br key={index} />;
                  
                  if (line.includes('**')) {
                    const parts = line.split('**');
                    return (
                      <p key={index} className="text-gray-800">
                        {parts.map((part, i) => 
                          i % 2 === 1 ? <strong key={i}>{part}</strong> : part
                        )}
                      </p>
                    );
                  }
                  
                  if (line.startsWith('✅')) {
                    return (
                      <p key={index} className="text-green-700 font-medium">
                        {line}
                      </p>
                    );
                  }
                  
                  if (line.startsWith('📝')) {
                    return (
                      <p key={index} className="text-blue-700 font-medium">
                        {line}
                      </p>
                    );
                  }
                  
                  if (line.startsWith('📚')) {
                    return (
                      <p key={index} className="text-purple-700 font-medium">
                        {line}
                      </p>
                    );
                  }
                  
                  return (
                    <p key={index} className="text-gray-800">
                      {line}
                    </p>
                  );
                })}
              </div>
            </Card>

            {/* Confirmation Box */}
            <Card className="p-6 bg-yellow-50 border-2 border-yellow-300 mb-6">
              <h3 className="text-lg font-semibold text-yellow-900 mb-3">
                ⚠️ Confirmação Necessária
              </h3>
              <p className="text-yellow-800 mb-4">
                Antes de eu começar, preciso da sua confirmação explícita.
              </p>
              <p className="text-yellow-800 font-medium">
                Deseja continuar com este plano?
              </p>
            </Card>

            {/* Actions */}
            <div className="flex gap-4">
              <Button
                variant="outline"
                onClick={handleEdit}
                disabled={confirming}
                className="flex-1"
              >
                ✏️ Editar Respostas
              </Button>
              
              <Button
                variant="outline"
                onClick={handleCancel}
                disabled={confirming}
                className="flex-1 border-red-300 text-red-700 hover:bg-red-50"
              >
                ❌ Cancelar
              </Button>
              
              <Button
                onClick={handleConfirm}
                disabled={confirming || !summary.ready_to_execute}
                className="flex-1 bg-green-600 hover:bg-green-700 text-white"
              >
                {confirming ? "Criando contrato..." : "✅ Confirmar e Começar"}
              </Button>
            </div>
          </>
        )}

        {/* Intent Created */}
        {step === "intent_created" && intent && (
          <Card className="p-8 bg-white shadow-lg mb-6">
            <div className="text-center mb-6">
              <div className="text-6xl mb-4">🔒</div>
              <h2 className="text-2xl font-bold text-gray-900 mb-2">
                Contrato Imutável Criado
              </h2>
              <p className="text-gray-600">
                Sua intenção foi transformada em um contrato que governa toda a execução.
              </p>
            </div>

            <div className="space-y-4 text-left">
              <div>
                <span className="font-semibold text-gray-700">Produto:</span>
                <p className="text-gray-900">{intent.product_name}</p>
              </div>
              <div>
                <span className="font-semibold text-gray-700">Objetivo:</span>
                <p className="text-gray-900">{intent.business_goal}</p>
              </div>
              <div>
                <span className="font-semibold text-gray-700">Sucesso:</span>
                <p className="text-gray-900">{intent.success_criteria}</p>
              </div>
              <div>
                <span className="font-semibold text-gray-700">Restrições:</span>
                <p className="text-gray-900">{intent.constraints}</p>
              </div>
              <div>
                <span className="font-semibold text-gray-700">Risco:</span>
                <p className="text-gray-900 capitalize">{intent.risk_level}</p>
              </div>
            </div>

            <div className="mt-6 p-4 bg-blue-50 rounded-lg border border-blue-200">
              <p className="text-sm text-blue-800 text-center">
                🔒 <strong>Este contrato é IMUTÁVEL.</strong> Qualquer tentativa de violação será bloqueada.
              </p>
            </div>
          </Card>
        )}

        {/* Executing */}
        {step === "executing" && (
          <Card className="p-8 bg-white shadow-lg text-center">
            <div className="inline-block animate-spin rounded-full h-16 w-16 border-b-4 border-green-600 mb-4"></div>
            <h2 className="text-2xl font-bold text-gray-900 mb-2">
              Trabalhando no seu produto...
            </h2>
            <p className="text-gray-600">
              Vou te mostrar o progresso em tempo real.
            </p>
          </Card>
        )}

        {/* Info Boxes */}
        {step === "summary" && (
          <>
            <div className="mt-6 bg-green-50 rounded-lg p-4 border border-green-200">
              <p className="text-sm text-green-800 text-center">
                ✅ <strong>Modo Seguro Ativado:</strong> Vou te mostrar tudo o que estou fazendo em tempo real.
              </p>
            </div>

            <div className="mt-4 bg-blue-50 rounded-lg p-4 border border-blue-200">
              <h3 className="text-sm font-semibold text-blue-900 mb-2">
                ℹ️ O que acontece depois?
              </h3>
              <ul className="space-y-1 text-sm text-blue-800">
                <li>• Vou criar um contrato imutável com suas intenções</li>
                <li>• Vou trabalhar no seu produto seguindo este plano</li>
                <li>• Você vai ver o progresso em tempo real</li>
                <li>• Vou te avisar quando terminar</li>
              </ul>
            </div>
          </>
        )}
      </div>
    </div>
  );
}
