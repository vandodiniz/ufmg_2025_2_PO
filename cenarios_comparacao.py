# cenarios_comparacao.py
from typing import Dict, List, Tuple
import pulp
import time
import random
from dataclasses import dataclass

@dataclass
class Resultado:
    algoritmo: str
    custo: float
    tempo: float
    status: str
    viável: bool

def gerar_dados_aleatorios(n_colaboradores, n_turnos, n_linhas):
    """Gera dados aleatórios para os cenários"""
    employees = list(range(1, n_colaboradores + 1))
    shifts = list(range(1, n_turnos + 1))
    lines = list(range(1, n_linhas + 1))
    
    # Custos dos turnos (alternando diurno/noturno)
    shift_cost = {}
    for j in shifts:
        shift_cost[j] = 1 if j % 2 == 1 else 2  # Ímpares: diurno, Pares: noturno
    
    # Custo dos colaboradores (crescente)
    employee_cost = {i: 100 + (i-1)*10 for i in employees}
    
    # Disponibilidade aleatória (80% de chance de disponível)
    availability = {}
    for i in employees:
        for k in lines:
            availability[(i, k)] = 1 if random.random() < 0.8 else 0
    
    # Skills aleatórias (0-5)
    skill_level = {}
    for i in employees:
        for k in lines:
            skill_level[(i, k)] = random.randint(0, 5) if availability[(i, k)] == 1 else 0
    
    # Classificação dos colaboradores
    shift_class = {}
    for i in employees:
        # Alterna entre categorias
        categories = ["MDA", "MDB", "MNA", "MNB"]
        shift_class[i] = categories[i % 4]
    
    # Demandas mínimas
    min_skill_required = {k: random.randint(3, 8) for k in lines}
    min_cover = {k: random.randint(1, 2) for k in lines}
    
    return (employees, shifts, lines, shift_cost, employee_cost, 
            availability, skill_level, shift_class, min_skill_required, min_cover)

def solver_mip_pulp(n_colaboradores, n_turnos, n_linhas):
    """Solver MIP original usando PuLP com CBC"""
    start_time = time.time()
    
    (employees, shifts, lines, shift_cost, employee_cost, 
     availability, skill_level, shift_class, min_skill_required, min_cover) = gerar_dados_aleatorios(n_colaboradores, n_turnos, n_linhas)
    
    model = pulp.LpProblem("Escalas_MIP", pulp.LpMinimize)
    
    # Variáveis
    x_vars = {(i,j): pulp.LpVariable(f"X_{i}_{j}", cat=pulp.LpBinary)
              for i in employees for j in shifts}
    
    w_vars = {(i,j,k): pulp.LpVariable(f"W_{i}_{j}_{k}", cat=pulp.LpBinary)
              for i in employees for j in shifts for k in lines}
    
    swap = {i: pulp.LpVariable(f"Swap_{i}", cat=pulp.LpBinary) for i in employees}
    
    # Função objetivo
    model += (
        pulp.lpSum((shift_cost[j] + employee_cost[i]) * x_vars[(i,j)]
                   for i in employees for j in shifts)
        + pulp.lpSum(5000 * swap[i] for i in employees)
    )
    
    # Restrições
    for j in shifts:
        for k in lines:
            model += pulp.lpSum(skill_level[(i,k)] * w_vars[(i,j,k)]
                                for i in employees) >= min_skill_required[k]
            model += pulp.lpSum(w_vars[(i,j,k)] for i in employees) >= min_cover[k]
    
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
    
    # Penalidades D↔N
    for i in employees:
        cat = shift_class[i]
        cat_period = "D" if "D" in cat else "N"
        
        if cat_period == "D":
            for j in shifts:
                if shift_cost[j] == 2:  # Turno noturno
                    model += swap[i] >= x_vars[(i,j)]
        else:
            for j in shifts:
                if shift_cost[j] == 1:  # Turno diurno
                    model += swap[i] >= x_vars[(i,j)]
    
    # Resolver
    model.solve(pulp.PULP_CBC_CMD(msg=False, timeLimit=300))  # 5 minutos timeout
    
    end_time = time.time()
    
    status = pulp.LpStatus[model.status]
    custo = pulp.value(model.objective) if status in ["Optimal", "Feasible"] else float('inf')
    
    return Resultado(
        algoritmo="MIP_PuLP_CBC",
        custo=custo,
        tempo=end_time - start_time,
        status=status,
        viável=status in ["Optimal", "Feasible"]
    )

def solver_greedy(n_colaboradores, n_turnos, n_linhas):
    """Algoritmo guloso para comparação"""
    start_time = time.time()
    
    (employees, shifts, lines, shift_cost, employee_cost, 
     availability, skill_level, shift_class, min_skill_required, min_cover) = gerar_dados_aleatorios(n_colaboradores, n_turnos, n_linhas)
    
    # Ordenar colaboradores por custo-benefício
    colaboradores_ordenados = sorted(employees, 
                                   key=lambda i: employee_cost[i] / (sum(skill_level[(i,k)] for k in lines) + 0.1))
    
    # Estruturas para acompanhar alocações
    x_vars = {(i,j): 0 for i in employees for j in shifts}
    skill_por_turno_linha = {(j,k): 0 for j in shifts for k in lines}
    pessoas_por_turno_linha = {(j,k): 0 for j in shifts for k in lines}
    
    # Algoritmo guloso
    for i in colaboradores_ordenados:
        melhor_turno = None
        melhor_melhoria = float('inf')
        
        for j in shifts:
            # Verificar se este turno é viável para o colaborador
            turno_valido = True
            for k in lines:
                if availability[(i,k)] == 0 and (skill_por_turno_linha[(j,k)] < min_skill_required[k] or 
                                                pessoas_por_turno_linha[(j,k)] < min_cover[k]):
                    turno_valido = False
                    break
            
            if turno_valido:
                # Calcular custo-benefício
                custo = employee_cost[i] + shift_cost[j]
                if shift_class[i] == "D" and shift_cost[j] == 2:
                    custo += 5000  # Penalidade
                elif shift_class[i] == "N" and shift_cost[j] == 1:
                    custo += 5000  # Penalidade
                
                if custo < melhor_melhoria:
                    melhor_melhoria = custo
                    melhor_turno = j
        
        if melhor_turno is not None:
            x_vars[(i, melhor_turno)] = 1
            # Atualizar skills e pessoas
            for k in lines:
                if availability[(i,k)] == 1:
                    skill_por_turno_linha[(melhor_turno, k)] += skill_level[(i,k)]
                    pessoas_por_turno_linha[(melhor_turno, k)] += 1
    
    # Verificar viabilidade
    viavel = True
    for j in shifts:
        for k in lines:
            if (skill_por_turno_linha[(j,k)] < min_skill_required[k] or 
                pessoas_por_turno_linha[(j,k)] < min_cover[k]):
                viavel = False
                break
    
    # Calcular custo total
    custo_total = 0
    for (i,j), valor in x_vars.items():
        if valor == 1:
            custo = employee_cost[i] + shift_cost[j]
            if (shift_class[i] == "D" and shift_cost[j] == 2) or (shift_class[i] == "N" and shift_cost[j] == 1):
                custo += 5000
            custo_total += custo
    
    end_time = time.time()
    
    return Resultado(
        algoritmo="Greedy",
        custo=custo_total if viavel else float('inf'),
        tempo=end_time - start_time,
        status="Feasible" if viavel else "Infeasible",
        viável=viavel
    )

def solver_genetico_pulp(n_colaboradores, n_turnos, n_linhas):
    """Algoritmo genético simplificado usando PuLP como local search"""
    start_time = time.time()
    
    (employees, shifts, lines, shift_cost, employee_cost, 
     availability, skill_level, shift_class, min_skill_required, min_cover) = gerar_dados_aleatorios(n_colaboradores, n_turnos, n_linhas)
    
    # Gerar população inicial
    populacao = []
    for _ in range(10):  # 10 indivíduos na população
        individuo = {}
        for i in employees:
            # Atribuir aleatoriamente a um turno ou nenhum
            if random.random() < 0.7:  # 70% de chance de ser alocado
                individuo[i] = random.choice(shifts)
            else:
                individuo[i] = None
        populacao.append(individuo)
    
    melhor_custo = float('inf')
    melhor_solucao = None
    
    # Busca local simples (iterações limitadas)
    for iteracao in range(50):
        for individuo in populacao:
            # Avaliar solução
            custo = 0
            skill_por_turno_linha = {(j,k): 0 for j in shifts for k in lines}
            pessoas_por_turno_linha = {(j,k): 0 for j in shifts for k in lines}
            viavel = True
            
            for i, j in individuo.items():
                if j is not None:
                    custo += employee_cost[i] + shift_cost[j]
                    if (shift_class[i] == "D" and shift_cost[j] == 2) or (shift_class[i] == "N" and shift_cost[j] == 1):
                        custo += 5000
                    
                    for k in lines:
                        if availability[(i,k)] == 1:
                            skill_por_turno_linha[(j,k)] += skill_level[(i,k)]
                            pessoas_por_turno_linha[(j,k)] += 1
            
            # Verificar restrições
            for j in shifts:
                for k in lines:
                    if (skill_por_turno_linha[(j,k)] < min_skill_required[k] or 
                        pessoas_por_turno_linha[(j,k)] < min_cover[k]):
                        viavel = False
                        custo = float('inf')
                        break
            
            if viavel and custo < melhor_custo:
                melhor_custo = custo
                melhor_solucao = individuo.copy()
        
        # Operadores genéticos simples (crossover e mutação)
        if len(populacao) >= 2:
            # Selecionar os melhores
            populacao = sorted(populacao, key=lambda ind: calcular_custo(ind, employees, shifts, lines, 
                                                                       employee_cost, shift_cost, shift_class, 
                                                                       availability, skill_level, min_skill_required, min_cover))[:5]
            # Reproduzir
            nova_populacao = populacao.copy()
            for _ in range(5):
                pai1, pai2 = random.sample(populacao, 2)
                filho = {}
                for i in employees:
                    if random.random() < 0.5:
                        filho[i] = pai1.get(i)
                    else:
                        filho[i] = pai2.get(i)
                    # Mutação
                    if random.random() < 0.1:
                        filho[i] = random.choice(shifts + [None])
                nova_populacao.append(filho)
            populacao = nova_populacao
    
    end_time = time.time()
    
    return Resultado(
        algoritmo="Genetico_Simplificado",
        custo=melhor_custo if melhor_solucao else float('inf'),
        tempo=end_time - start_time,
        status="Feasible" if melhor_solucao else "Infeasible",
        viável=melhor_solucao is not None
    )

def calcular_custo(individuo, employees, shifts, lines, employee_cost, shift_cost, shift_class, availability, skill_level, min_skill_required, min_cover):
    """Função auxiliar para calcular custo de um indivíduo"""
    custo = 0
    skill_por_turno_linha = {(j,k): 0 for j in shifts for k in lines}
    pessoas_por_turno_linha = {(j,k): 0 for j in shifts for k in lines}
    
    for i, j in individuo.items():
        if j is not None:
            custo += employee_cost[i] + shift_cost[j]
            if (shift_class[i] == "D" and shift_cost[j] == 2) or (shift_class[i] == "N" and shift_cost[j] == 1):
                custo += 5000
            
            for k in lines:
                if availability[(i,k)] == 1:
                    skill_por_turno_linha[(j,k)] += skill_level[(i,k)]
                    pessoas_por_turno_linha[(j,k)] += 1
    
    # Penalizar inviabilidade
    for j in shifts:
        for k in lines:
            if (skill_por_turno_linha[(j,k)] < min_skill_required[k] or 
                pessoas_por_turno_linha[(j,k)] < min_cover[k]):
                custo += 10000  # Grande penalidade por inviabilidade
    
    return custo

def testar_cenarios():
    """Testa todos os cenários com todos os algoritmos"""
    cenarios = [
        ("Cenário 1: Mais Colaboradores", 36, 4, 3),   # 36 colabs, 4 turnos, 3 linhas
        ("Cenário 2: Mais Turnos", 18, 8, 3),          # 18 colabs, 8 turnos, 3 linhas  
        ("Cenário 3: Mais Linhas", 18, 4, 6),          # 18 colabs, 4 turnos, 6 linhas
        ("Cenário 4: Completo", 24, 6, 4),             # 24 colabs, 6 turnos, 4 linhas
    ]
    
    algoritmos = [solver_mip_pulp, solver_greedy, solver_genetico_pulp]
    
    resultados_totais = []
    
    for nome_cenario, n_colabs, n_turnos, n_linhas in cenarios:
        print(f"\n{'='*60}")
        print(f"TESTANDO: {nome_cenario}")
        print(f"Colaboradores: {n_colabs}, Turnos: {n_turnos}, Linhas: {n_linhas}")
        print(f"{'='*60}")
        
        resultados_cenario = []
        
        for algoritmo in algoritmos:
            print(f"\nExecutando {algoritmo.__name__}...")
            try:
                resultado = algoritmo(n_colabs, n_turnos, n_linhas)
                resultados_cenario.append(resultado)
                print(f"  → Custo: {resultado.custo:.2f}")
                print(f"  → Tempo: {resultado.tempo:.2f}s")
                print(f"  → Status: {resultado.status}")
            except Exception as e:
                print(f"  → ERRO: {e}")
                resultados_cenario.append(Resultado(
                    algoritmo=algoritmo.__name__,
                    custo=float('inf'),
                    tempo=0,
                    status=f"Erro: {e}",
                    viável=False
                ))
        
        resultados_totais.append((nome_cenario, resultados_cenario))
    
    return resultados_totais

def gerar_relatorio(resultados_totais):
    """Gera relatório comparativo dos resultados"""
    print(f"\n{'='*80}")
    print("RELATÓRIO COMPARATIVO - ALGORITMOS DE OTIMIZAÇÃO")
    print(f"{'='*80}")
    
    for nome_cenario, resultados in resultados_totais:
        print(f"\n{nome_cenario}")
        print("-" * len(nome_cenario))
        
        # Encontrar melhor custo viável
        custos_viaveis = [r.custo for r in resultados if r.viável and r.custo < float('inf')]
        melhor_custo = min(custos_viaveis) if custos_viaveis else float('inf')
        
        for resultado in resultados:
            status_icon = "✓" if resultado.viável else "✗"
            melhor_icon = "★" if resultado.custo == melhor_custo and resultado.viável else " "
            print(f"{melhor_icon} {status_icon} {resultado.algoritmo:20} | "
                  f"Custo: {resultado.custo:8.2f} | "
                  f"Tempo: {resultado.tempo:6.2f}s | "
                  f"Status: {resultado.status}")

if __name__ == "__main__":
    # Configurar seed para reprodutibilidade
    random.seed(42)
    
    print("INICIANDO TESTES DE CENÁRIOS E ALGORITMOS")
    print("Este teste pode levar alguns minutos...")
    
    resultados = testar_cenarios()
    gerar_relatorio(resultados)