# Restrições do Modelo de Otimização de Escalas (MIP)

Este documento lista as restrições do problema de Otimização de Escalas de CSE's entre Turnos, modelado como um problema de Programação Inteira Mista (MIP).

---

## Variáveis de Decisão e Parâmetros

### Parâmetros e índices

- **$i \in \{1, 18\}$:** Colaboradores.
- **$j \in \{1, 4\}$:** Turnos (Diurno A, Diurno B, Noturno A, Noturno B).
- **$k \in \{1, 3\}$:** Linhas de Atendimento (Flexlab, Atellica, Immulite).

### Variáveis Binárias

- **$X_{ij}$:** 1 se o colaborador $i$ atende ao turno $j$, 0 caso contrário.
- **$Y_{ik}$:** 1 se o colaborador $i$ atende à linha $k$, 0 caso contrário.
- **$W_{ijk}$:** Variável auxiliar para linearização; 1 se o colaborador $i$ trabalha na linha $k$ e no turno $j$, 0 caso contrário.
- **$S_i$ (swap):** 1 se o colaborador $i$ for alocado em período oposto ao seu período original (Diurno↔Noturno), 0 caso contrário.

---

## Restrições do Modelo

### 1. Cobertura Mínima por Linha e Turno

O número de colaboradores escalados deve garantir a cobertura mínima exigida em cada linha ($k$) e em todos os turnos ($j$). A soma é feita sobre todos os colaboradores ($i$).

|     Linha ($k$)      |   Cobertura Mínima   |              Restrição Matemática (usando $W_{ijk}$)              |
| :------------------: | :------------------: | :---------------------------------------------------------------: |
| **Flexlab** ($k=1$)  | Pelo menos 1 pessoa  | $\sum_{i=1}^{18} W_{i, j, 1} \ge 1, \quad \forall j \in \{1, 4\}$ |
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
X_{ij}, Y_{ik}, W_{ijk}, S_i \in \{0, 1\}
$$

**Equivalência Lógica (Implementada por Restrições):**

$$
W_{ijk} = X_{ij} \cdot Y_{ik}
$$

---

### 4.Engenheiro só pode trabalhar em turnos compatíveis com sua categoria (com penalização para D↔N)

Cada colaborador tem uma categoria inicial (MDA/MDB → diurno; MNA/MNB → noturno).

**Regra implementada no modelo:**

- O engenheiro **pode** mudar entre subturnos dentro do mesmo período (A↔B ou N1↔N2) **sem custo**.
- O engenheiro **pode** ser alocado em período oposto (Diurno ↔ Noturno), **porém** essa escolha ativa a variável $S_i$ (swap) e gera um custo adicional na função objetivo para penalizar essa troca.

**Como isso é modelado:**

- Se o colaborador $i$ é originalmente **diurno** (MDA/MDB), então

$$
S_i \ge X_{i3}, \qquad S_i \ge X_{i4}
$$

- Se o colaborador $i$ é originalmente **noturno** (MNA/MNB), então

$$
S_i \ge X_{i1}, \qquad S_i \ge X_{i2}
$$

A variável $S_i$ assume valor 1 sempre que $i$ for alocado em um turno de período contrário ao seu original; o termo de penalização $p \cdot S_i$ é somado à função objetivo (no seu código $p$ foi definido como 5000 por padrão).

---

## Função Objetivo

A função objetivo do seu modelo minimiza o custo total de alocação **incluindo** a penalização por troca de período:

$$
\text{Min } Z = \sum_{i=1}^{18} \sum_{j=1}^{4} (c_j + e_i) X_{ij} \;+\; p\sum_{i=1}^{18} S_i
$$

Onde:

- $c_j$ é o custo do turno $j$ ($c_j=1$ para turnos diurnos e $c_j=2$ para turnos noturnos).
- $e_i$ é o custo do colaborador $i$ (cada colaborador tem um custo associado, variando de 100 a 270 unidades).
- $p$ é o parâmetro de penalização por troca Diurno↔Noturno (no código atual $p=5000$).

---

# Tabelas de dados

## 1. Variável de Disponibilidade: $Y_{ik}$

_1 se o colaborador $i$ atende à linha $k$, 0 caso contrário._

| Colaborador (i) | k=1 (Flexlab) | k=2 (Atellica) | k=3 (Immulite) |
| :-------------: | :-----------: | :------------: | :------------: |
|        1        |       1       |       1        |       1        |
|        2        |       0       |       1        |       1        |
|        3        |       1       |       1        |       1        |
|        4        |       1       |       1        |       1        |
|        5        |       0       |       1        |       1        |
|        6        |       0       |       1        |       1        |
|        7        |       1       |       1        |       0        |
|        8        |       0       |       1        |       1        |
|        9        |       1       |       1        |       0        |
|       10        |       1       |       0        |       1        |
|       11        |       0       |       1        |       1        |
|       12        |       0       |       1        |       1        |
|       13        |       1       |       1        |       0        |
|       14        |       0       |       1        |       0        |
|       15        |       0       |       1        |       1        |
|       16        |       1       |       0        |       0        |
|       17        |       0       |       1        |       1        |
|       18        |       1       |       0        |       1        |

---

## 2. Custo por Turno

| Turno | Custo |
| ----- | ----- |
| 1     | 1     |
| 2     | 1     |
| 3     | 2     |
| 4     | 2     |

---

## 3. Custo por Funcionário

| Funcionário | Custo |
| ----------- | ----- |
| 1           | 100.0 |
| 2           | 110.0 |
| 3           | 120.0 |
| 4           | 130.0 |
| 5           | 140.0 |
| 6           | 150.0 |
| 7           | 160.0 |
| 8           | 170.0 |
| 9           | 180.0 |
| 10          | 190.0 |
| 11          | 200.0 |
| 12          | 210.0 |
| 13          | 220.0 |
| 14          | 230.0 |
| 15          | 240.0 |
| 16          | 250.0 |
| 17          | 260.0 |
| 18          | 270.0 |

---

## 4.Skill Level por Engenheiro e Linha

| Eng | L1  | L2  | L3  |
| --- | --- | --- | --- |
| 1   | 5   | 3   | 3   |
| 2   | 1   | 3   | 3   |
| 3   | 3   | 3   | 5   |
| 4   | 3   | 3   | 3   |
| 5   | 1   | 3   | 3   |
| 6   | 1   | 3   | 1   |
| 7   | 3   | 3   | 0   |
| 8   | 1   | 3   | 3   |
| 9   | 3   | 3   | 0   |
| 10  | 5   | 0   | 3   |
| 11  | 1   | 3   | 3   |
| 12  | 1   | 3   | 3   |
| 13  | 5   | 3   | 0   |
| 14  | 1   | 3   | 0   |
| 15  | 1   | 3   | 3   |
| 16  | 5   | 0   | 0   |
| 17  | 1   | 3   | 3   |
| 18  | 5   | 0   | 3   |

---

## 5. Categoria dos Engenheiros

| Engenheiro | Categoria |
| ---------- | --------- |
| 1          | MDA       |
| 2          | MDB       |
| 3          | MDA       |
| 4          | MDA       |
| 5          | MNB       |
| 6          | MNB       |
| 7          | MNA       |
| 8          | MNA       |
| 9          | MNB       |
| 10         | MDA       |
| 11         | MDB       |
| 12         | MDB       |
| 13         | MDB       |
| 14         | MNA       |
| 15         | MDA       |
| 16         | MDB       |
| 17         | MNA       |
| 18         | MNB       |

