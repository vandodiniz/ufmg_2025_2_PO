from typing import Dict, List, Tuple
import pulp

def build_model() -> Tuple[pulp.LpProblem, Dict[Tuple[int, int], pulp.LpVariable], Dict[Tuple[int, int, int], pulp.LpVariable]]:
    """Cria o modelo MIP com todas as restrições e função objetivo correta."""
    
    # Conjuntos
    employees: List[int] = list(range(1, 19))  # 18 funcionários
    shifts: List[int] = list(range(1, 5))      # 4 turnos
    lines: List[int] = [1, 2, 3]               # 3 linhas
    
    # Custos
    shift_cost: Dict[int, int] = {1:1, 2:1, 3:2, 4:2}  # diurno=1, noturno=2
    employee_cost: Dict[int, float] = {            # custo por funcionário
        1:100.0,2:110.0,3:120.0,4:130.0,5:140.0,6:150.0,
        7:160.0,8:170.0,9:180.0,10:190.0,11:200.0,12:210.0,
        13:220.0,14:230.0,15:240.0,16:250.0,17:260.0,18:270.0
    }
    
    # Disponibilidade por linha (Y_ik)
    availability: Dict[Tuple[int,int], int] = {}
    raw_rows = {
        1:  (1,1,1), 2: (0,1,1), 3: (1,1,1), 4: (1,1,1),
        5:  (0,1,1), 6: (0,1,1), 7: (1,1,0), 8: (0,1,1),
        9:  (1,1,0), 10: (1,0,1), 11: (0,1,1), 12: (0,1,1),
        13: (1,1,0), 14: (0,1,0), 15: (0,1,1), 16: (1,0,0),
        17: (0,1,1), 18: (1,0,1)
    }
    for i in employees:
        k1,k2,k3 = raw_rows[i]
        availability[(i,1)] = k1
        availability[(i,2)] = k2
        availability[(i,3)] = k3

    # Nível de habilidade por linha (skill_level)
    skill_level: Dict[Tuple[int,int], int] = {}
    raw_skill = {
        1: (5,3,3), 2:(1,3,3), 3:(3,3,5), 4:(3,3,3),
        5: (1,3,3), 6:(1,3,1), 7:(3,3,0), 8:(1,3,3),
        9: (3,3,0), 10:(5,0,3), 11:(1,3,3), 12:(1,3,3),
        13:(5,3,0), 14:(1,3,0), 15:(1,3,3), 16:(5,0,0),
        17:(1,3,3), 18:(5,0,3)
    }
    for i in employees:
        s1,s2,s3 = raw_skill[i]
        skill_level[(i,1)] = s1
        skill_level[(i,2)] = s2
        skill_level[(i,3)] = s3

    # Demandas mínimas
    min_skill_required: Dict[int,int] = {1:6,2:8,3:7}  # skill mínima por linha
    min_cover: Dict[int,int] = {1:1,2:2,3:2}          # cobertura mínima de pessoas

    # Modelo
    model = pulp.LpProblem("Escalas_CSE_MIP", pulp.LpMinimize)

    # Variáveis
    x_vars = {(i,j): pulp.LpVariable(f"X_{i}_{j}", cat=pulp.LpBinary)
              for i in employees for j in shifts}
    w_vars = {(i,j,k): pulp.LpVariable(f"W_{i}_{j}_{k}", cat=pulp.LpBinary)
              for i in employees for j in shifts for k in lines}

    # Função objetivo: custo total = custo turno + custo funcionário
    model += pulp.lpSum((shift_cost[j] + employee_cost[i]) * x_vars[(i,j)]
                        for i in employees for j in shifts), "MinCost"

    # Restrição 1: cobertura mínima de skill por linha e turno
    for j in shifts:
        for k in lines:
            model += pulp.lpSum(skill_level[(i,k)]*w_vars[(i,j,k)] for i in employees) >= min_skill_required[k], f"MinSkill_k{k}_j{j}"

    # Restrição 2: cobertura mínima de pessoas por linha e turno
    for j in shifts:
        for k in lines:
            model += pulp.lpSum(w_vars[(i,j,k)] for i in employees) >= min_cover[k], f"MinCover_k{k}_j{j}"

    # Restrição 3: cada funcionário trabalha no máximo 1 turno
    for i in employees:
        model += pulp.lpSum(x_vars[(i,j)] for j in shifts) <= 1, f"MaxOneShift_i{i}"

    # Restrição 4: linearização W_ijk = X_ij * Y_ik
    for i in employees:
        for j in shifts:
            for k in lines:
                y_ik = availability[(i,k)]
                model += w_vars[(i,j,k)] <= x_vars[(i,j)], f"W_le_X_i{i}_j{j}_k{k}"
                model += w_vars[(i,j,k)] <= y_ik, f"W_le_Y_i{i}_k{k}_j{j}"
                model += w_vars[(i,j,k)] >= x_vars[(i,j)] + y_ik - 1, f"W_ge_XplusYminus1_i{i}_j{j}_k{k}"

    return model, x_vars, w_vars, skill_level, min_skill_required, min_cover

def solve_and_format() -> str:
    model, x_vars, w_vars, skill_level, min_skill_required, min_cover = build_model()
    model.solve(pulp.PULP_CBC_CMD(msg=False))

    status = pulp.LpStatus[model.status]
    lines: List[str] = [f"Status: {status}"]

    if status not in {"Optimal","Feasible"}:
        lines.append("Nenhuma solução viável encontrada.")
        return "\n".join(lines)

    # Valor objetivo
    lines.append(f"Custo total: {pulp.value(model.objective):.2f}")

    # Atribuições X_ij
    lines.append("\nAtribuições por colaborador e turno:")
    for (i,j), var in sorted(x_vars.items()):
        if var.value() > 0.5:
            lines.append(f" - Colaborador {i} no Turno {j}")

    # Cobertura W_ijk
    lines.append("\nCobertura por linha e turno (pessoas e skill_sum):")
    employees = sorted({i for (i,_j) in x_vars.keys()})
    shifts = sorted({j for (_i,j) in x_vars.keys()})
    for j in shifts:
        for k in [1,2,3]:
            cover = sum(w_vars[(i,j,k)].value() for i in employees)
            skill_sum = sum(skill_level[(i,k)]*w_vars[(i,j,k)].value() for i in employees)
            lines.append(f" - Turno {j}, Linha {k}: pessoas={int(round(cover))}, skill_sum={int(round(skill_sum))}, req_skill={min_skill_required[k]}, min_pessoas={min_cover[k]}")

    return "\n".join(lines)

def main():
    print(solve_and_format())

if __name__ == "__main__":
    main()
