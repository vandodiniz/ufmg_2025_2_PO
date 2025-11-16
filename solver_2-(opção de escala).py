from typing import Dict, List, Tuple
import pulp
#exclusivamente para geração de escalas factíveis
def build_model() -> Tuple[pulp.LpProblem, Dict[Tuple[int, int], pulp.LpVariable], Dict[Tuple[int, int, int], pulp.LpVariable]]:

    employees = list(range(1, 19))
    shifts = list(range(1, 5))
    lines = [1, 2, 3]

    # disponibilidade Y_ik
    availability = {}
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

    min_cover = {1: 1, 2: 2, 3: 2}

    model = pulp.LpProblem("Escalas_CSE_Use_All", pulp.LpMinimize)

    x_vars = {
        (i, j): pulp.LpVariable(f"X_{i}_{j}", lowBound=0, upBound=1, cat=pulp.LpBinary)
        for i in employees for j in shifts
    }

    w_vars = {
        (i, j, k): pulp.LpVariable(f"W_{i}_{j}_{k}", lowBound=0, upBound=1, cat=pulp.LpBinary)
        for i in employees for j in shifts for k in lines
    }

    # -------- FUNÇÃO OBJETIVO: nada para otimizar --------
    model += 0, "No_Objective"

    # -------- COBERTURA MÍNIMA --------
    for j in shifts:
        for k in lines:
            model += (
                pulp.lpSum(w_vars[(i, j, k)] for i in employees) >= min_cover[k]
            ), f"MinCover_k{k}_j{j}"

    # -------- CADA ENGENHEIRO DEVE TRABALHAR EXATAMENTE 1 TURNO --------
    for i in employees:
        model += (
            pulp.lpSum(x_vars[(i, j)] for j in shifts) == 1
        ), f"ExactlyOneShift_i{i}"

    # -------- W_ijk = X_ij * Y_ik (linearização) --------
    for i in employees:
        for j in shifts:
            for k in lines:
                y_ik = availability[(i, k)]
                model += w_vars[(i, j, k)] <= x_vars[(i, j)]
                model += w_vars[(i, j, k)] <= y_ik
                model += w_vars[(i, j, k)] >= x_vars[(i, j)] + y_ik - 1

    return model, x_vars, w_vars


def solve_and_format() -> str:
    model, x_vars, w_vars = build_model()
    model.solve(pulp.PULP_CBC_CMD(msg=False))

    status = pulp.LpStatus[model.status]
    out = [f"Status: {status}"]

    if status not in {"Optimal", "Feasible"}:
        out.append("Nenhuma solução viável.")
        return "\n".join(out)

    out.append("\nAtribuições por colaborador:")
    for (i, j), var in x_vars.items():
        if var.value() == 1:
            out.append(f" - Colaborador {i} → Turno {j}")

    out.append("\nCobertura por turno e linha:")
    for j in range(1, 5):
        for k in range(1, 4):
            cover = sum(w_vars[(i, j, k)].value() for i in range(1, 19))
            out.append(f" - Turno {j}, Linha {k}: {int(cover)}")

    return "\n".join(out)


def main():
    print(solve_and_format())


if __name__ == "__main__":
    main()
