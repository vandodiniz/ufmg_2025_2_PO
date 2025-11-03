# Restrições do Modelo de Otimização de Escalas (MIP)

Este documento lista as restrições do problema de Otimização de Escalas de CSE's entre Turnos, modelado como um problema de Programação Inteira Mista (MIP).

---

## Variáveis de Decisão e Parâmetros

### Parâmetros e índices
* **$i \in \{1, 18\}$:** Colaboradores.
* **$j \in \{1, 4\}$:** Turnos (Diurno A, Diurno B, Noturno A, Noturno B).
* **$k \in \{1, 3\}$:** Linhas de Atendimento (Flexlab, Atellica, Immulite).

### Variáveis Binárias
* **$X_{ij}$:** 1 se o colaborador $i$ atende ao turno $j$, 0 caso contrário.
* **$Y_{ik}$:** 1 se o colaborador $i$ atende à linha $k$, 0 caso contrário.
* **$W_{ijk}$:** Variável auxiliar para linearização; 1 se o colaborador $i$ trabalha na linha $k$ e no turno $j$, 0 caso contrário.

---

## Restrições do Modelo

### 1. Cobertura Mínima por Linha e Turno

O número de colaboradores escalados deve garantir a cobertura mínima exigida em cada linha ($k$) e em todos os turnos ($j$). A soma é feita sobre todos os colaboradores ($i$).

| Linha ($k$) | Cobertura Mínima | Restrição Matemática (usando $W_{ijk}$) |
| :---: | :---: | :---: |
| **Flexlab** ($k=1$) | Pelo menos 1 pessoa | $\sum_{i=1}^{18} W_{i, j, 1} \ge 1, \quad \forall j \in \{1, 4\}$ |
| **Atellica** ($k=2$) | Pelo menos 2 pessoas | $\sum_{i=1}^{18} W_{i, j, 2} \ge 2, \quad \forall j \in \{1, 4\}$ |
| **Immulite** ($k=3$) | Pelo menos 2 pessoas | $\sum_{i=1}^{18} W_{i, j, 3} \ge 2, \quad \forall j \in \{1, 4\}$ |

### 2. Alocação Máxima do Funcionário

Cada funcionário ($i$) só pode ser alocado em, no máximo, 1 turno ($j$).

$$
\sum_{j=1}^{4} X_{ij} \le 1, \quad \forall i \in \{1, 18\}
$$

### 3. Linearização e Domínio

A variável auxiliar $W_{ijk}$ substitui o produto não-linear ($X_{ij} \cdot Y_{ik}$) para manter a estrutura MIP do modelo. A equivalência é definida pelas restrições de linearização.

**Domínio das Variáveis:**

Todas as variáveis de decisão são binárias:
$$
X_{ij}, Y_{ik}, W_{ijk} \in \{0, 1\}
$$

**Equivalência Lógica (Implementada por Restrições):**
$$
W_{ijk} = X_{ij} \cdot Y_{ik}
$$

---
**Função Objetivo:**

A função objetivo, que busca minimizar o custo total de alocação (considerando custos de turno e custos por funcionário), é:

$$
\text{Min } Z = \sum_{i=1}^{18} \sum_{j=1}^{4} (c_j + e_i) X_{ij}
$$

Onde:
* $c_j$ é o custo do turno $j$ ($c_j=1$ para turnos diurnos e $c_j=2$ para turnos noturnos).
* $e_i$ é o custo do colaborador $i$ (cada colaborador tem um custo associado, variando de 100 a 270 unidades).

### 4. Tabela de dados
# Variável de Disponibilidade: $Y_{ik}$
*1 se o colaborador $i$ atende à linha $k$, 0 caso contrário.*

| Colaborador (i) | k=1 (Flexlab) | k=2 (Atellica) | k=3 (Immulite) |
| :-------------: | :-----------: | :------------: | :------------: |
| 1 | 1 | 1 | 1 |
| 2 | 0 | 1 | 1 |
| 3 | 1 | 1 | 1 |
| 4 | 1 | 1 | 1 |
| 5 | 0 | 1 | 1 |
| 6 | 0 | 1 | 1 |
| 7 | 1 | 1 | 0 |
| 8 | 0 | 1 | 1 |
| 9 | 1 | 1 | 0 |
| 10 | 1 | 0 | 1 |
| 11 | 0 | 1 | 1 |
| 12 | 0 | 1 | 1 |
| 13 | 1 | 1 | 0 |
| 14 | 0 | 1 | 0 |
| 15 | 0 | 1 | 1 |
| 16 | 1 | 0 | 0 |
| 17 | 0 | 1 | 1 |
| 18 | 1 | 0 | 1 |