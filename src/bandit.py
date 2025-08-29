from src.battle_core import BattleEnv
from src.MCTS import make_env_from_state,realize_compound,compound_key,state_key,sim_rest_battle
import random
import numpy as np
def total_health(state,side):
    p1=state.p1 if side==0 else state.p2
    team_health=p1.active[0].pokemon.base_stats["hp"]+p1.active[1].pokemon.base_stats["hp"]+p1.bench[0].pokemon.base_stats["hp"]+p1.bench[1].pokemon.base_stats["hp"]
    current_health=p1.active[0].current_hp+p1.active[1].current_hp+p1.bench[0].current_hp+p1.bench[1].current_hp
    return team_health/current_health #normalization so we lie inside [0,1]

def total_combination_actions(state):
    env=make_env_from_state(state)
    legal_1=env.legal_actions(0)
    legal_2=env.legal_actions(1)
    s0_0=[x for x in legal_1 if x.slot==0]
    s0_1=[x for x in legal_1 if x.slot==1]
    s1_0=[x for x in legal_2 if x.slot==0]
    s1_1=[x for x in legal_2 if x.slot==1]
    pairs_1=[[x,y] for x in s0_0 for y in s0_1]
    paris_2=[[x,y] for x in s1_0 for y in s1_1]
    monster=[[x,y] for x in pairs_1 for y in paris_2]
    return monster


def explorer(state,side):
    p1=state.p1 if side==0 else state.p2
    monster=total_combination_actions(state)
    rewards=[[] for _ in range(len(monster))]
    for i,turn in enumerate(monster):
        env=make_env_from_state(state)
        _,_=env.step(turn[0],turn[1])
        rewards[i].append(total_health(env.state,side))
        lobster=total_combination_actions(env.state)
        for j, turn_2 in enumerate(lobster):
            env=make_env_from_state(state)
            _,_=env.step(turn_2[0],turn_2[1])
            rewards[i].append(total_health(env.state,side))
    sumichi=[sum(x) for x in rewards]
    arg=np.argmax(sumichi)
    real_arg=rewards[arg][0]
    #best_first_move=monster[np.argmax(rewards)][side]
    return monster[real_arg][side]
    


def absolute_search(root_state,side=0,turns_ahead=3):
    p1=root_state.p1 if side==0 else root_state.p2
    env=make_env_from_state(root_state)


        
