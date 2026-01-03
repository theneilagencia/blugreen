# Análise Técnica: Integração com Ollama para Análise de Código

## 📋 Contexto

O **Ollama** é um serviço de LLM (Large Language Model) local que permite executar modelos de IA sem depender de APIs externas. No Blugreen, o Ollama é usado pelos agentes para análise de código, geração de código, interpretação de requisitos e outras tarefas que requerem inteligência artificial.

## 🔍 Análise da Implementação Atual

### Localização
- **Cliente:** `backend/app/services/ollama.py`
- **Integração:** `backend/app/agents/base.py`
- **API:** `backend/app/api/system.py`

### Arquitetura Atual

```
┌─────────────────────────────────────┐
│         BaseAgent                   │
│  (Architect, Backend, Frontend...)  │
└──────────────┬──────────────────────┘
               │
               │ usa
               ▼
┌─────────────────────────────────────┐
│       OllamaClient                  │
│  - generate()                       │
│  - chat()                           │
│  - is_available()                   │
└──────────────┬──────────────────────┘
               │
               │ HTTP
               ▼
┌─────────────────────────────────────┐
│       Ollama Server                 │
│  (Docker container)                 │
│  Modelo: qwen2.5:7b                 │
└─────────────────────────────────────┘
```

### Configuração Atual

**Arquivo:** `backend/app/config.py`
```python
ollama_base_url: str = "http://localhost:11434"
ollama_model: str = "qwen2.5:7b"
```

**Docker Compose:**
```yaml
ollama:
  image: ollama/ollama:latest
  ports:
    - "11434:11434"
  volumes:
    - ollama_data:/root/.ollama
  # Requer GPU NVIDIA (atualmente rodando em CPU)
```

---

## ✅ Funcionalidades Implementadas

### 1. OllamaClient

**Métodos Disponíveis:**

#### `generate(prompt, system, temperature, max_tokens)`
Gera texto baseado em um prompt simples.

**Entrada:**
```python
{
    "prompt": str,                    # Prompt principal
    "system": Optional[str],          # System prompt (contexto)
    "temperature": float = 0.7,       # Criatividade (0.0 - 1.0)
    "max_tokens": Optional[int]       # Limite de tokens
}
```

**Saída:**
```python
str  # Texto gerado
```

**Uso Típico:**
```python
response = await ollama_client.generate(
    prompt="Analyze this code and identify potential bugs",
    system="You are a code review expert",
    temperature=0.3  # Baixa criatividade para análise técnica
)
```

---

#### `chat(messages, temperature, max_tokens)`
Conversa multi-turno com contexto.

**Entrada:**
```python
{
    "messages": [
        {"role": "user", "content": "What is this code doing?"},
        {"role": "assistant", "content": "This code..."},
        {"role": "user", "content": "Can you improve it?"}
    ],
    "temperature": float = 0.7,
    "max_tokens": Optional[int]
}
```

**Saída:**
```python
str  # Resposta do assistente
```

**Uso Típico:**
```python
messages = [
    {"role": "user", "content": "Analyze this Python function"},
    {"role": "assistant", "content": "This function calculates..."},
    {"role": "user", "content": "What are the edge cases?"}
]
response = await ollama_client.chat(messages=messages)
```

---

#### `is_available()`
Verifica se o Ollama está disponível.

**Saída:**
```python
bool  # True se disponível, False caso contrário
```

**Uso Típico:**
```python
if await ollama_client.is_available():
    # Usar Ollama
else:
    # Usar fallback
```

---

#### `list_models()`
Lista modelos disponíveis no Ollama.

**Saída:**
```python
List[str]  # Lista de nomes de modelos
```

**Exemplo:**
```python
["qwen2.5:7b", "llama2:13b", "codellama:7b"]
```

---

### 2. BaseAgent Integration

Todos os agentes herdam de `BaseAgent` e têm acesso aos métodos:

#### `ask_llm(prompt, temperature, max_tokens)`
Wrapper simplificado para `generate()` com system prompt automático.

#### `chat_with_llm(messages, temperature, max_tokens)`
Wrapper simplificado para `chat()` com system prompt automático.

#### `is_llm_available()`
Verifica disponibilidade do LLM.

---

## 🎯 Casos de Uso para Análise de Código

### 1. Análise de Estrutura

**Objetivo:** Identificar arquitetura e organização do código.

**Prompt Template:**
```python
prompt = f"""
Analyze the following code structure:

{file_tree}

Identify:
1. Architecture pattern (MVC, layered, microservices, etc)
2. Main components and their responsibilities
3. Dependencies between components
4. Potential architectural issues

Provide a structured analysis in JSON format.
"""
```

**Saída Esperada:**
```json
{
    "architecture_pattern": "layered",
    "components": [
        {
            "name": "api",
            "responsibility": "HTTP endpoints",
            "dependencies": ["services", "models"]
        }
    ],
    "issues": [
        "Circular dependency between services and models"
    ]
}
```

---

### 2. Detecção de Riscos

**Objetivo:** Identificar vulnerabilidades e problemas de segurança.

**Prompt Template:**
```python
prompt = f"""
Analyze the following code for security risks:

```python
{code_snippet}
```

Identify:
1. Security vulnerabilities (SQL injection, XSS, etc)
2. Performance issues
3. Memory leaks
4. Error handling problems
5. Best practices violations

Rate each risk as: CRITICAL, HIGH, MEDIUM, LOW
"""
```

**Saída Esperada:**
```json
{
    "risks": [
        {
            "type": "SQL Injection",
            "severity": "CRITICAL",
            "line": 42,
            "description": "User input not sanitized",
            "recommendation": "Use parameterized queries"
        }
    ],
    "overall_risk_score": 0.75
}
```

---

### 3. Análise de Qualidade

**Objetivo:** Avaliar qualidade geral do código.

**Prompt Template:**
```python
prompt = f"""
Evaluate the quality of this code:

```python
{code_snippet}
```

Analyze:
1. Code clarity and readability
2. Naming conventions
3. Documentation
4. Test coverage (if tests are present)
5. Maintainability
6. Complexity

Provide scores (0.0 - 1.0) for each aspect.
"""
```

**Saída Esperada:**
```json
{
    "quality_scores": {
        "clarity": 0.8,
        "naming": 0.9,
        "documentation": 0.6,
        "maintainability": 0.75,
        "complexity": 0.7
    },
    "overall_quality": 0.75,
    "suggestions": [
        "Add docstrings to functions",
        "Reduce cyclomatic complexity in main()"
    ]
}
```

---

### 4. Sugestões de Melhoria

**Objetivo:** Propor refatorações e melhorias.

**Prompt Template:**
```python
prompt = f"""
Suggest improvements for this code:

```python
{code_snippet}
```

Provide:
1. Refactoring opportunities
2. Performance optimizations
3. Code simplifications
4. Better patterns to use

For each suggestion, provide:
- Description
- Priority (HIGH, MEDIUM, LOW)
- Estimated effort (SMALL, MEDIUM, LARGE)
- Example code (if applicable)
"""
```

---

## 🔄 Integração com Métricas de Qualidade

### Fluxo de Análise

```
┌─────────────────────────────────────┐
│  1. Código do Projeto               │
└──────────────┬──────────────────────┘
               │
               ▼
┌─────────────────────────────────────┐
│  2. Ollama Analisa Código           │
│     - Estrutura                     │
│     - Riscos                        │
│     - Qualidade                     │
└──────────────┬──────────────────────┘
               │
               ▼
┌─────────────────────────────────────┐
│  3. Resultados Estruturados         │
│     (JSON)                          │
└──────────────┬──────────────────────┘
               │
               ▼
┌─────────────────────────────────────┐
│  4. QualityMetric Records           │
│     - Persistidos no BD             │
│     - Versionados                   │
│     - Auditáveis                    │
└─────────────────────────────────────┘
```

### Exemplo de Integração

```python
async def analyze_code_quality(project: Project) -> dict:
    """Analisa qualidade do código usando Ollama."""
    
    # 1. Obter código do projeto
    code_files = get_project_files(project)
    
    # 2. Analisar com Ollama
    ollama = get_ollama_client()
    
    if not await ollama.is_available():
        # Fallback: análise estática simples
        return static_analysis(code_files)
    
    results = []
    for file in code_files:
        prompt = f"""
        Analyze this code file for quality:
        
        File: {file.path}
        ```{file.language}
        {file.content}
        ```
        
        Provide quality scores (0.0 - 1.0) for:
        - clarity
        - maintainability
        - complexity
        - documentation
        """
        
        response = await ollama.generate(prompt, temperature=0.3)
        analysis = parse_json_response(response)
        results.append(analysis)
    
    # 3. Agregar resultados
    overall_quality = calculate_overall_quality(results)
    
    # 4. Persistir métricas
    metric = QualityMetric(
        project_id=project.id,
        name="code_quality",
        value=overall_quality,
        category="quality",
        metadata={"details": results}
    )
    session.add(metric)
    session.commit()
    
    return {
        "overall_quality": overall_quality,
        "files_analyzed": len(code_files),
        "details": results
    }
```

---

## ⚠️ Fallbacks e Tratamento de Erros

### Estratégia de Fallback

O Ollama é **OPCIONAL**. Quando indisponível, o sistema deve usar alternativas:

#### 1. Análise Estática

Usar ferramentas de análise estática quando Ollama não estiver disponível:

```python
async def analyze_with_fallback(code: str) -> dict:
    """Analisa código com fallback para análise estática."""
    
    ollama = get_ollama_client()
    
    if await ollama.is_available():
        # Usar Ollama (análise inteligente)
        return await analyze_with_ollama(code)
    else:
        # Fallback: análise estática
        logger.warning("Ollama unavailable, using static analysis")
        return static_analysis(code)
```

**Ferramentas de Análise Estática:**
- **Python:** `pylint`, `flake8`, `mypy`, `bandit`
- **JavaScript/TypeScript:** `eslint`, `tsc`
- **Genérico:** `radon` (complexidade), `cloc` (linhas de código)

---

#### 2. Análise Simplificada

Quando nem Ollama nem ferramentas estão disponíveis:

```python
def simple_analysis(code: str) -> dict:
    """Análise simplificada baseada em heurísticas."""
    
    lines = code.split("\n")
    
    return {
        "lines_of_code": len(lines),
        "complexity_estimate": estimate_complexity(code),
        "has_comments": any("#" in line or "//" in line for line in lines),
        "has_docstrings": '"""' in code or "'''" in code,
        "quality_score": 0.5  # Score neutro
    }
```

---

#### 3. Cache de Resultados

Para evitar análises repetidas:

```python
from functools import lru_cache
import hashlib

@lru_cache(maxsize=1000)
async def analyze_code_cached(code_hash: str, code: str) -> dict:
    """Analisa código com cache."""
    return await analyze_with_fallback(code)

def get_code_hash(code: str) -> str:
    """Gera hash do código para cache."""
    return hashlib.sha256(code.encode()).hexdigest()

# Uso
code_hash = get_code_hash(code)
result = await analyze_code_cached(code_hash, code)
```

---

### Tratamento de Erros

#### Timeout

```python
async def analyze_with_timeout(code: str, timeout: float = 30.0) -> dict:
    """Analisa código com timeout."""
    
    try:
        return await asyncio.wait_for(
            analyze_with_ollama(code),
            timeout=timeout
        )
    except asyncio.TimeoutError:
        logger.warning(f"Ollama analysis timed out after {timeout}s")
        return static_analysis(code)
```

#### Erro de Conexão

```python
async def analyze_with_retry(code: str, max_retries: int = 3) -> dict:
    """Analisa código com retry."""
    
    for attempt in range(max_retries):
        try:
            return await analyze_with_ollama(code)
        except OllamaError as e:
            if attempt == max_retries - 1:
                logger.error(f"Ollama failed after {max_retries} attempts")
                return static_analysis(code)
            
            await asyncio.sleep(2 ** attempt)  # Exponential backoff
```

---

## 📊 Métricas de Uso do Ollama

### Métricas a Coletar

1. **Disponibilidade:**
   - Taxa de sucesso de chamadas
   - Tempo de resposta médio
   - Taxa de timeout

2. **Uso:**
   - Número de análises por dia
   - Tokens processados
   - Custo computacional (CPU/GPU)

3. **Qualidade:**
   - Precisão das análises (comparado com análise estática)
   - Feedback dos usuários

### Implementação de Métricas

```python
class OllamaMetrics:
    """Coleta métricas de uso do Ollama."""
    
    def __init__(self):
        self.total_calls = 0
        self.successful_calls = 0
        self.failed_calls = 0
        self.total_time = 0.0
        self.timeouts = 0
    
    async def track_call(self, func, *args, **kwargs):
        """Rastreia uma chamada ao Ollama."""
        self.total_calls += 1
        start_time = time.time()
        
        try:
            result = await func(*args, **kwargs)
            self.successful_calls += 1
            return result
        except asyncio.TimeoutError:
            self.timeouts += 1
            self.failed_calls += 1
            raise
        except Exception:
            self.failed_calls += 1
            raise
        finally:
            self.total_time += time.time() - start_time
    
    def get_stats(self) -> dict:
        """Retorna estatísticas de uso."""
        return {
            "total_calls": self.total_calls,
            "success_rate": self.successful_calls / self.total_calls if self.total_calls > 0 else 0,
            "avg_time": self.total_time / self.total_calls if self.total_calls > 0 else 0,
            "timeout_rate": self.timeouts / self.total_calls if self.total_calls > 0 else 0
        }
```

---

## 🔧 Configuração e Otimização

### Modelos Recomendados

| Modelo | Tamanho | Uso | Performance |
|--------|---------|-----|-------------|
| `qwen2.5:7b` | 7B params | Análise geral | Bom (atual) |
| `codellama:7b` | 7B params | Código específico | Excelente |
| `llama2:13b` | 13B params | Análise profunda | Lento |
| `mistral:7b` | 7B params | Balanceado | Bom |

### Otimizações

#### 1. Batch Processing

Processar múltiplos arquivos em paralelo:

```python
async def analyze_multiple_files(files: List[str]) -> List[dict]:
    """Analisa múltiplos arquivos em paralelo."""
    
    tasks = [analyze_code(file) for file in files]
    results = await asyncio.gather(*tasks)
    return results
```

#### 2. Chunking

Dividir arquivos grandes em chunks:

```python
def chunk_code(code: str, max_lines: int = 100) -> List[str]:
    """Divide código em chunks menores."""
    
    lines = code.split("\n")
    chunks = []
    
    for i in range(0, len(lines), max_lines):
        chunk = "\n".join(lines[i:i+max_lines])
        chunks.append(chunk)
    
    return chunks
```

#### 3. Prompt Engineering

Usar prompts otimizados para melhor performance:

```python
OPTIMIZED_PROMPTS = {
    "code_quality": """
    Analyze code quality. Output ONLY JSON:
    {
        "clarity": 0.0-1.0,
        "maintainability": 0.0-1.0,
        "complexity": 0.0-1.0
    }
    Code:
    {code}
    """,
    
    "security": """
    Find security issues. Output ONLY JSON:
    {
        "issues": [{"type": "", "severity": "", "line": 0}]
    }
    Code:
    {code}
    """
}
```

---

## 📝 Contrato de Uso

### Entrada Padrão

```python
{
    "code": str,                    # Código a analisar
    "analysis_type": str,           # "structure" | "risks" | "quality" | "suggestions"
    "language": Optional[str],      # Linguagem do código
    "context": Optional[dict]       # Contexto adicional
}
```

### Saída Padrão

```python
{
    "analysis_type": str,
    "result": dict,                 # Resultado estruturado
    "confidence": float,            # 0.0 - 1.0
    "model_used": str,              # Modelo do Ollama usado
    "processing_time": float,       # Tempo de processamento
    "fallback_used": bool           # Se usou fallback
}
```

---

## 🚀 Próximos Passos (para Devin)

### Prioridade Alta

1. **Implementar Fallbacks:**
   - Integrar ferramentas de análise estática
   - Implementar análise simplificada
   - Testar todos os cenários de falha

2. **Otimizar Prompts:**
   - Criar biblioteca de prompts otimizados
   - Testar diferentes temperaturas
   - Validar qualidade das respostas

3. **Integrar com Métricas:**
   - Persistir resultados de análise
   - Criar dashboard de qualidade
   - Implementar alertas

### Prioridade Média

4. **Batch Processing:**
   - Implementar análise paralela
   - Otimizar uso de recursos
   - Implementar queue system

5. **Cache:**
   - Implementar cache de resultados
   - Definir estratégia de invalidação
   - Otimizar performance

### Prioridade Baixa

6. **Modelos Alternativos:**
   - Testar outros modelos
   - Comparar performance
   - Documentar trade-offs

---

## 📌 Decisões Técnicas

| Decisão | Justificativa |
|---------|---------------|
| Ollama opcional | Não bloquear funcionalidade se indisponível |
| Fallback para análise estática | Garantir análise sempre disponível |
| Cache de resultados | Evitar análises repetidas |
| Timeout de 30s | Balance entre qualidade e UX |
| Modelo qwen2.5:7b | Bom balance entre qualidade e performance |
| Temperature 0.3 para análise | Respostas mais determinísticas |

---

## ⚠️ Limitações Conhecidas

1. **GPU:** Ollama está rodando em CPU (mais lento)
2. **Contexto:** Limite de tokens pode truncar arquivos grandes
3. **Precisão:** LLM pode ter falsos positivos/negativos
4. **Custo:** Análise de projetos grandes pode ser lenta
5. **Idioma:** Melhor performance com código em inglês

---

**Status:** 📋 Análise Completa - Pronto para Implementação  
**Responsável pela Implementação:** Devin  
**Data:** 03/01/2026
