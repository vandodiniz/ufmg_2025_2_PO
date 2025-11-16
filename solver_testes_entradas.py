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
    """Construção da modelagem de programação  linear inteira mista"""

    # definição dos conjuntos
    employees: List[int] = list(range(1, 19))  # 18 funcionários
    shifts: List[int] = list(range(1, 5))      # 4 turnos
    lines: List[int] = [1, 2, 3]               # 3 linhas

    # CLASSIFICAÇÃO MDA/MDB/MNA/MNB
    shift_class: Dict[int, str] = {
        1: "MDA", 2: "MDB", 3: "MDA", 4: "MDA", 5: "MNB", 6: "MNB",
        7: "MNA", 8: "MNA", 9: "MNB", 10: "MDA", 11: "MDB", 12: "MDB",
        13: "MDB", 14: "MNA", 15: "MDA", 16: "MDB", 17: "MNA", 18: "MNB"
    }

    # Custos estabelecidos
    shift_cost: Dict[int, int] = {1:1, 2:1, 3:2, 4:2}
    employee_cost: Dict[int, float] = {
        1:100.0,2:110.0,3:120.0,4:130.0,5:140.0,6:150.0,
        7:160.0,8:170.0,9:180.0,10:190.0,11:200.0,12:210.0,
        13:220.0,14:230.0,15:240.0,16:250.0,17:260.0,18:270.0
    }

    # Disponibilidade Yik
    availability = {}
    raw_rows = {
        1:(1,1,1),2:(0,1,1),3:(1,1,1),4:(1,1,1),
        5:(0,1,1),6:(0,1,1),7:(1,1,0),8:(0,1,1),
        9:(1,1,0),10:(1,0,1),11:(0,1,1),12:(0,1,1),
        13:(1,1,0),14:(0,1,0),15:(0,1,1),16:(1,0,0),
        17:(0,1,1),18:(1,0,1)
    }
    for i in employees:
        a,b,c = raw_rows[i]
        availability[(i,1)] = a
        availability[(i,2)] = b
        availability[(i,3)] = c

    # tabela de definição de habilidades
    skill_level = {}
    raw_skill = {
        1:(5,3,3),2:(1,3,3),3:(3,3,5),4:(3,3,3),
        5:(1,3,3),6:(1,3,1),7:(3,3,0),8:(1,3,3),
        9:(3,3,0),10:(5,0,3),11:(1,3,3),12:(1,3,3),
        13:(5,3,0),14:(1,3,0),15:(1,3,3),16:(5,0,0),
        17:(1,3,3),18:(5,0,3)
    }
    for i in employees:
        x,y,z = raw_skill[i]
        skill_level[(i,1)] = x
        skill_level[(i,2)] = y
        skill_level[(i,3)] = z

    # Demandas
    min_skill_required = {1:6,2:8,3:7}
    min_cover = {1:1,2:2,3:2}

    # Modelo
    model = pulp.LpProblem("Escalas_CSE_MIP", pulp.LpMinimize)

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

    #     DIURNO <-> NOTURNO —  COM custo para a mudança
    for i in employees:
        cat = shift_class[i]  # MDA/MDB/MNA/MNB

        # determina se o funcionário é originalmente D ou N
        cat_period = "D" if "D" in cat else "N"

        if cat_period == "D":
            # swap_i = 1 se escolher turno noturno
            model += swap[i] >= x_vars[(i,3)]
            model += swap[i] >= x_vars[(i,4)]
        else:
            # swap_i = 1 se escolher turno diurno
            model += swap[i] >= x_vars[(i,1)]
            model += swap[i] >= x_vars[(i,2)]

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
        for k in [1,2,3]:
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
