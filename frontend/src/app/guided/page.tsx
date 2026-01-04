"use client";

/**
 * Modo Guiado para Leigos (CAMADA 1)
 * 
 * Interface simplificada onde o usuário vê APENAS intenções humanas.
 * 
 * Princípios:
 * - Linguagem 100% humana
 * - Sem termos técnicos (stack, branch, pipeline)
 * - Máximo 3 perguntas por etapa
 * - Sistema infere tudo internamente
 */

import { useState } from "react";
import { useRouter } from "next/navigation";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";

type GuidedIntent = "criar" | "melhorar" | "entender";

interface IntentOption {
  id: GuidedIntent;
  title: string;
  description: string;
  icon: string;
  color: string;
}

const intentOptions: IntentOption[] = [
  {
    id: "criar",
    title: "Quero criar um produto",
    description: "Vou te ajudar a criar um produto do zero, do jeito que você imaginou.",
    icon: "✨",
    color: "bg-blue-50 hover:bg-blue-100 border-blue-200"
  },
  {
    id: "melhorar",
    title: "Quero melhorar um produto existente",
    description: "Vou analisar o seu produto e fazer as melhorias que você precisa.",
    icon: "🚀",
    color: "bg-green-50 hover:bg-green-100 border-green-200"
  },
  {
    id: "entender",
    title: "Quero entender um repositório",
    description: "Vou explicar como o código funciona em linguagem simples.",
    icon: "📚",
    color: "bg-purple-50 hover:bg-purple-100 border-purple-200"
  }
];

export default function GuidedModePage() {
  const router = useRouter();
  const [selectedIntent, setSelectedIntent] = useState<GuidedIntent | null>(null);
  const [loading, setLoading] = useState(false);

  const handleSelectIntent = async (intent: GuidedIntent) => {
    setSelectedIntent(intent);
    setLoading(true);

    try {
      // Criar sessão guiada
      const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/guided/start`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ intent }),
      });

      if (!response.ok) {
        throw new Error("Erro ao iniciar sessão guiada");
      }

      const session = await response.json();

      // Redirecionar para wizard
      router.push(`/guided/${session.id}`);
    } catch (error) {
      console.error("Erro:", error);
      alert("Ops! Algo deu errado. Tente novamente.");
      setLoading(false);
      setSelectedIntent(null);
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100 py-12 px-4">
      <div className="max-w-4xl mx-auto">
        {/* Header */}
        <div className="text-center mb-12">
          <h1 className="text-4xl font-bold text-gray-900 mb-4">
            Olá! 👋
          </h1>
          <p className="text-xl text-gray-600">
            Sou o Blugreen, seu time sênior de desenvolvimento de software.
          </p>
          <p className="text-lg text-gray-500 mt-2">
            Vou te ajudar a criar, melhorar ou entender produtos de software.
          </p>
        </div>

        {/* Intent Selection */}
        <div className="mb-8">
          <h2 className="text-2xl font-semibold text-gray-800 mb-6 text-center">
            O que você quer fazer hoje?
          </h2>

          <div className="grid gap-6 md:grid-cols-3">
            {intentOptions.map((option) => (
              <Card
                key={option.id}
                className={`
                  p-6 cursor-pointer transition-all duration-200
                  border-2 ${option.color}
                  ${selectedIntent === option.id ? "ring-4 ring-blue-300" : ""}
                  ${loading ? "opacity-50 cursor-not-allowed" : ""}
                `}
                onClick={() => !loading && handleSelectIntent(option.id)}
              >
                <div className="text-center">
                  <div className="text-5xl mb-4">{option.icon}</div>
                  <h3 className="text-lg font-semibold text-gray-900 mb-2">
                    {option.title}
                  </h3>
                  <p className="text-sm text-gray-600">
                    {option.description}
                  </p>
                </div>
              </Card>
            ))}
          </div>
        </div>

        {/* Loading State */}
        {loading && (
          <div className="text-center py-8">
            <div className="inline-block animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
            <p className="mt-4 text-gray-600">Preparando tudo para você...</p>
          </div>
        )}

        {/* Info Box */}
        <div className="mt-12 bg-white rounded-lg shadow-sm p-6 border border-gray-200">
          <h3 className="text-lg font-semibold text-gray-800 mb-3">
            ℹ️ Como funciona?
          </h3>
          <ul className="space-y-2 text-gray-600">
            <li className="flex items-start">
              <span className="mr-2">1️⃣</span>
              <span>Você escolhe o que quer fazer</span>
            </li>
            <li className="flex items-start">
              <span className="mr-2">2️⃣</span>
              <span>Eu faço algumas perguntas simples (no máximo 3 por etapa)</span>
            </li>
            <li className="flex items-start">
              <span className="mr-2">3️⃣</span>
              <span>Você confirma o plano</span>
            </li>
            <li className="flex items-start">
              <span className="mr-2">4️⃣</span>
              <span>Eu cuido de tudo e te mostro o resultado</span>
            </li>
          </ul>
        </div>

        {/* Safety Note */}
        <div className="mt-6 bg-green-50 rounded-lg p-4 border border-green-200">
          <p className="text-sm text-green-800 text-center">
            ✅ <strong>Modo Seguro Ativado:</strong> Você vai poder revisar tudo antes de qualquer mudança ser feita.
          </p>
        </div>
      </div>
    </div>
  );
}
