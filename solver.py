from typing import Dict, List, Tuple

import pulp


def build_model() -> Tuple[pulp.LpProblem, Dict[Tuple[int, int], pulp.LpVariable], Dict[Tuple[int, int, int], pulp.LpVariable]]:
    """Cria o modelo MIP conforme especificado no README.

    Retorna o problema (modelo) e os dicionários de variáveis X_ij e W_ijk.
    """
    # Conjuntos (índices)
    employees: List[int] = list(range(1, 19))  # i in {1..18}
    shifts: List[int] = list(range(1, 5))      # j in {1..4}
    lines: List[int] = [1, 2, 3]               # k in {1..3} (1 Flexlab, 2 Atellica, 3 Immulite)

    # Parâmetros: custos por turno (1,2 diurnos; 3,4 noturnos)
    shift_cost: Dict[int, int] = {1: 1, 2: 1, 3: 2, 4: 2}

    # Parâmetro de disponibilidade Y_ik (tabela do README)
    availability: Dict[Tuple[int, int], int] = {}
    raw_rows = {
        1:  (1, 1, 1),
        2:  (0, 1, 1),
        3:  (1, 1, 1),
        4:  (1, 1, 1),
        5:  (0, 1, 1),
        6:  (0, 1, 1),
        7:  (1, 1, 0),
        8:  (0, 1, 1),
        9:  (1, 1, 0),
        10: (1, 0, 1),
        11: (0, 1, 1),
        12: (0, 1, 1),
        13: (1, 1, 0),
        14: (0, 1, 0),
        15: (0, 1, 1),
        16: (1, 0, 0),
        17: (0, 1, 1),
        18: (1, 0, 1),
    }
    for i in employees:
        k1, k2, k3 = raw_rows[i]
        availability[(i, 1)] = k1
        availability[(i, 2)] = k2
        availability[(i, 3)] = k3

    # Cobertura mínima por linha e por turno (para cada j)
    min_cover: Dict[int, int] = {1: 1, 2: 2, 3: 2}  # k: mínimo

    # Modelo
    model = pulp.LpProblem("Escalas_CSE_MIP", pulp.LpMinimize)

    # Variáveis binárias X_ij: 1 se colaborador i atende ao turno j
    x_vars: Dict[Tuple[int, int], pulp.LpVariable] = {
        (i, j): pulp.LpVariable(f"X_{i}_{j}", lowBound=0, upBound=1, cat=pulp.LpBinary)
        for i in employees
        for j in shifts
    }

    # Variáveis binárias W_ijk: 1 se colaborador i trabalha na linha k e turno j
    w_vars: Dict[Tuple[int, int, int], pulp.LpVariable] = {
        (i, j, k): pulp.LpVariable(f"W_{i}_{j}_{k}", lowBound=0, upBound=1, cat=pulp.LpBinary)
        for i in employees
        for j in shifts
        for k in lines
    }

    # Função objetivo: minimizar custo total som_j c_j * X_ij
    model += pulp.lpSum(shift_cost[j] * x_vars[(i, j)] for i in employees for j in shifts), "Minimize_Shift_Cost"

    # Restrição 1: Cobertura mínima por linha k em cada turno j
    for j in shifts:
        for k in lines:
            model += (
                pulp.lpSum(w_vars[(i, j, k)] for i in employees) >= min_cover[k]
            ), f"MinCover_k{k}_j{j}"

    # Restrição 2: Alocação máxima por colaborador (no máximo 1 turno)
    for i in employees:
        model += (
            pulp.lpSum(x_vars[(i, j)] for j in shifts) <= 1
        ), f"MaxOneShift_i{i}"

    # Restrição 3: Linearização W_ijk = X_ij * Y_ik
    # Implementação padrão:
    #   W_ijk <= X_ij
    #   W_ijk <= Y_ik
    #   W_ijk >= X_ij + Y_ik - 1
    for i in employees:
        for j in shifts:
            for k in lines:
                y_ik = availability[(i, k)]
                # W_ijk <= X_ij
                model += w_vars[(i, j, k)] <= x_vars[(i, j)], f"W_le_X_i{i}_j{j}_k{k}"
                # W_ijk <= Y_ik
                # quando Y_ik é 0/1 constante, isso é igual a W_ijk <= y_ik
                model += w_vars[(i, j, k)] <= y_ik, f"W_le_Y_i{i}_k{k}_j{j}"
                # W_ijk >= X_ij + Y_ik - 1
                model += w_vars[(i, j, k)] >= x_vars[(i, j)] + y_ik - 1, f"W_ge_XplusYminus1_i{i}_j{j}_k{k}"

    return model, x_vars, w_vars


def solve_and_format() -> str:
    """Resolve o modelo e retorna uma string formatada com a solução."""
    model, x_vars, w_vars = build_model()

    # Resolver com solver padrão do PuLP (CBC incluso)
    model.solve(pulp.PULP_CBC_CMD(msg=False))

    status = pulp.LpStatus[model.status]
    lines: List[str] = []
    lines.append(f"Status: {status}")

    if status not in {"Optimal", "Feasible"}:
        lines.append("Nenhuma solução viável encontrada.")
        return "\n".join(lines)

    # Valor objetivo
    obj = pulp.value(model.objective)
    lines.append(f"Custo total (Z): {obj:.2f}")

    # Imprimir X_ij atribuídos
    lines.append("\nAtribuições por colaborador e turno (X_ij = 1):")
    for (i, j), var in sorted(x_vars.items()):
        if var.value() is not None and var.value() > 0.5:
            lines.append(f" - Colaborador {i} no Turno {j}")

    # Resumo de cobertura por linha e turno via W_ijk
    lines.append("\nCobertura por linha e turno (soma W_ijk):")
    employees = sorted({i for (i, _j) in {(i, j) for (i, j) in x_vars.keys()}})
    shifts = sorted({j for (_i, j) in x_vars.keys()})
    lines_k = [1, 2, 3]
    for j in shifts:
        for k in lines_k:
            cover_jk = sum(w_vars[(i, j, k)].value() or 0 for i in employees)
            lines.append(f" - Turno {j}, Linha {k}: {int(round(cover_jk))}")

    return "\n".join(lines)


def main() -> None:
    result = solve_and_format()
    print(result)


if __name__ == "__main__":
    main()


