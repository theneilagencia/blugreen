"use client";

/**
 * Resumo do Modo Guiado (CAMADA 1 + CAMADA 3)
 * 
 * Mostra um resumo em linguagem humana do que o sistema vai fazer.
 * Implementa a PRÉ-VISUALIZAÇÃO DO PLANO (CAMADA 3).
 * 
 * Sem confirmação explícita → NÃO EXECUTAR.
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

export default function GuidedSummaryPage({ params }: { params: Promise<{ id: string }> }) {
  const resolvedParams = use(params);
  const sessionId = resolvedParams.id;
  const router = useRouter();
  
  const [summary, setSummary] = useState<Summary | null>(null);
  const [loading, setLoading] = useState(true);
  const [confirming, setConfirming] = useState(false);

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
      // Atualizar status para executando
      const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/guided/${sessionId}`, {
        method: "PATCH",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          status: "executing"
        }),
      });

      if (!response.ok) {
        throw new Error("Erro ao confirmar execução");
      }

      // TODO: Integrar com o sistema de execução (CAMADA 4 - Loop Autônomo)
      // Por enquanto, apenas redirecionar para uma página de execução
      alert("Confirmado! Em breve vou começar a trabalhar no seu produto.");
      router.push("/projects");
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
            Resumo do Plano 📋
          </h1>
          <p className="text-lg text-gray-600">
            Veja o que eu vou fazer para você
          </p>
        </div>

        {/* Summary Card */}
        <Card className="p-8 bg-white shadow-lg mb-6">
          <div className="prose prose-lg max-w-none">
            {summary.summary.split('\n').map((line, index) => {
              if (line.trim() === '') return <br key={index} />;
              
              // Bold text
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
              
              // Checkmarks
              if (line.startsWith('✅')) {
                return (
                  <p key={index} className="text-green-700 font-medium">
                    {line}
                  </p>
                );
              }
              
              // Notes
              if (line.startsWith('📝')) {
                return (
                  <p key={index} className="text-blue-700 font-medium">
                    {line}
                  </p>
                );
              }
              
              // Books
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
            {confirming ? "Confirmando..." : "✅ Confirmar e Começar"}
          </Button>
        </div>

        {/* Safety Note */}
        <div className="mt-6 bg-green-50 rounded-lg p-4 border border-green-200">
          <p className="text-sm text-green-800 text-center">
            ✅ <strong>Modo Seguro Ativado:</strong> Vou te mostrar tudo o que estou fazendo em tempo real.
          </p>
        </div>

        {/* Info Box */}
        <div className="mt-4 bg-blue-50 rounded-lg p-4 border border-blue-200">
          <h3 className="text-sm font-semibold text-blue-900 mb-2">
            ℹ️ O que acontece depois?
          </h3>
          <ul className="space-y-1 text-sm text-blue-800">
            <li>• Vou trabalhar no seu produto seguindo este plano</li>
            <li>• Você vai ver o progresso em tempo real</li>
            <li>• Vou te avisar quando terminar</li>
            <li>• Você vai poder testar e dar feedback</li>
          </ul>
        </div>
      </div>
    </div>
  );
}
