from typing import Dict, List, Tuple
import pulp

# esse é o solver de submissão para correção
def build_model() -> Tuple[
    pulp.LpProblem,
    Dict[Tuple[int, int], pulp.LpVariable],
    Dict[Tuple[int, int, int], pulp.LpVariable],
    Dict[Tuple[int,int], int],
    Dict[int,int],
    Dict[int,int]
]:
    """Construção da modelagem de programação linear inteira mista - CENÁRIO REDUZIDO"""

    # definição dos conjuntos REDUZIDOS
    employees: List[int] = list(range(1, 5))   # 4 funcionários
    shifts: List[int] = list(range(1, 3))      # 2 turnos (1=Diurno, 2=Noturno)
    lines: List[int] = [1, 2]                  # 2 linhas

    # CLASSIFICAÇÃO MDA/MDB/MNA/MNB - CENÁRIO REDUZIDO
    shift_class: Dict[int, str] = {
        1: "MDA", 2: "MDB", 3: "MNA", 4: "MNB"
    }

    # Custos estabelecidos - CENÁRIO REDUZIDO
    shift_cost: Dict[int, int] = {1:1, 2:2}  # Diurno=1, Noturno=2
    employee_cost: Dict[int, float] = {
        1:100.0, 2:110.0, 3:120.0, 4:130.0
    }

    # Disponibilidade Yik - CENÁRIO REDUZIDO
    availability = {}
    raw_rows = {
        1: (1, 1),  # Colab 1: Linha1=1, Linha2=1
        2: (0, 1),  # Colab 2: Linha1=0, Linha2=1
        3: (1, 0),  # Colab 3: Linha1=1, Linha2=0
        4: (1, 1)   # Colab 4: Linha1=1, Linha2=1
    }
    for i in employees:
        a, b = raw_rows[i]
        availability[(i,1)] = a
        availability[(i,2)] = b

    # tabela de definição de habilidades - CENÁRIO REDUZIDO
    skill_level = {}
    raw_skill = {
        1: (5, 3),  # Colab 1: Linha1=5, Linha2=3
        2: (0, 3),  # Colab 2: Linha1=0, Linha2=3
        3: (3, 0),  # Colab 3: Linha1=3, Linha2=0
        4: (3, 3)   # Colab 4: Linha1=3, Linha2=3
    }
    for i in employees:
        x, y = raw_skill[i]
        skill_level[(i,1)] = x
        skill_level[(i,2)] = y

    # Demandas - CENÁRIO REDUZIDO
    min_skill_required = {1:4, 2:3}  # Skill mínimo por linha
    min_cover = {1:1, 2:1}           # Cobertura mínima de pessoas por linha

    # Modelo
    model = pulp.LpProblem("Escalas_CSE_MIP_REDUZIDO", pulp.LpMinimize)

    # Variáveis
    x_vars = {(i,j): pulp.LpVariable(f"X_{i}_{j}", cat=pulp.LpBinary)
              for i in employees for j in shifts}
    w_vars = {(i,j,k): pulp.LpVariable(f"W_{i}_{j}_{k}", cat=pulp.LpBinary)
              for i in employees for j in shifts for k in lines}

    # NOVO: variáveis binárias indicando troca D↔N
    swap = {i: pulp.LpVariable(f"Swap_{i}", cat=pulp.LpBinary) for i in employees}

    # Função objetivo
    model += (
        pulp.lpSum((shift_cost[j] + employee_cost[i]) * x_vars[(i,j)]
                   for i in employees for j in shifts)
        + pulp.lpSum(5000 * swap[i] for i in employees)
    )

    # Cobertura mínima de nível de habilidade
    for j in shifts:
        for k in lines:
            model += pulp.lpSum(skill_level[(i,k)] * w_vars[(i,j,k)]
                                for i in employees) >= min_skill_required[k]

    # Cobertura mínima de engenheiros
    for j in shifts:
        for k in lines:
            model += pulp.lpSum(w_vars[(i,j,k)] for i in employees) >= min_cover[k]

    # No máximo 1 turno por funcionário
    for i in employees:
        model += pulp.lpSum(x_vars[(i,j)] for j in shifts) <= 1

    # Linearização W = X * Y
    for i in employees:
        for j in shifts:
            for k in lines:
                y = availability[(i,k)]
                model += w_vars[(i,j,k)] <= x_vars[(i,j)]
                model += w_vars[(i,j,k)] <= y
                model += w_vars[(i,j,k)] >= x_vars[(i,j)] + y - 1

    # DIURNO <-> NOTURNO — COM custo para a mudança
    for i in employees:
        cat = shift_class[i]  # MDA/MDB/MNA/MNB

        # determina se o funcionário é originalmente D ou N
        cat_period = "D" if "D" in cat else "N"

        if cat_period == "D":
            # swap_i = 1 se escolher turno noturno
            model += swap[i] >= x_vars[(i,2)]  # Turno 2 é noturno
        else:
            # swap_i = 1 se escolher turno diurno
            model += swap[i] >= x_vars[(i,1)]  # Turno 1 é diurno

    return model, x_vars, w_vars, skill_level, min_skill_required, min_cover


def solve_and_format() -> str:
    (model, x_vars, w_vars, skill_level, 
     min_skill_required, min_cover) = build_model()

    model.solve(pulp.PULP_CBC_CMD(msg=False))

    status = pulp.LpStatus[model.status]
    lines = [f"Status: {status}"]

    if status not in ["Optimal", "Feasible"]:
        lines.append("Nenhuma solução viável encontrada.")
        return "\n".join(lines)

    # Objetivo
    lines.append(f"Custo total: {pulp.value(model.objective):.2f}")

    # Atribuições X_ij
    lines.append("\nAtribuições por colaborador e turno:")
    for (i,j), var in sorted(x_vars.items()):
        if var.value() > 0.5:
            lines.append(f" - Colaborador {i} no Turno {j}")

    # W_ijk (cobertura)
    lines.append("\nCobertura por linha e turno (pessoas e skill_sum):")
    employees = sorted({i for (i,_j) in x_vars})
    shifts = sorted({j for (_i,j) in x_vars})
    for j in shifts:
        for k in [1,2]:
            cover = sum(w_vars[(i,j,k)].value() for i in employees)
            skill_sum = sum(skill_level[(i,k)] * w_vars[(i,j,k)].value()
                            for i in employees)
            lines.append(
                f" - Turno {j}, Linha {k}: "
                f"pessoas={int(round(cover))}, "
                f"skill_sum={int(round(skill_sum))}, "
                f"req_skill={min_skill_required[k]}, "
                f"min_pessoas={min_cover[k]}"
            )

    return "\n".join(lines)


def main():
    print(solve_and_format())


if __name__ == "__main__":
    main()
