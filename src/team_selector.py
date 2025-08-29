from src.battle_pokemon import BattlePokemon
from src.battle_core import BattleEnv
from src.MCTS import sim_rest_battle
from typing import List
import random
import numpy as np
def all_teams_possible():
    from itertools import combinations
    lista=[0,1,2,3,4,5]
    monster=[]
    combi=combinations(lista,2)
    for a in combi:
        mod=[x for x in lista if x not in a]
        recomb=combinations(mod,2)
        for j in recomb:
            monster.append([a,j])
    flat=[[monster[i][0][0],monster[i][0][1],monster[i][1][0],monster[i][1][1]] for i in range(90)]
    return flat

def random_team_selection(team:List["BattlePokemon"],rng):
    selection=rng.sample(team,4)
    return selection

def team_selecting_policy(my_team:List["BattlePokemon"], rival_team:List["BattlePokemon"],sims=100,seed=123):
    rng=random.Random(seed)
    all_combs=all_teams_possible()
    achievements=[]
    for comb in all_combs:
        wins=0
        for i in range(sims):
            p1_active,p1_bench=[my_team[comb[0]],my_team[comb[1]]],[my_team[comb[2]],my_team[comb[3]]]
            rival_selection=random_team_selection(rival_team,rng)
            p2_active,p2_bench=[rival_selection[0],rival_selection[1]],[rival_selection[2],rival_selection[3]]
            env=BattleEnv(p1_active,p1_bench,p2_active,p2_bench)
            wins+=sim_rest_battle(env.state,rng)
        achievements.append(wins)
    best=all_combs[np.argmax(achievements)]
    return [my_team[best[0]],my_team[best[1]],my_team[best[2]],my_team[best[3]]]

