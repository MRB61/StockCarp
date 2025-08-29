import numpy as np
from src.battle_core import BattleEnv, BattleState, auto_replace_fainted, Action,ActionType, damage_calc, _alive
import random
from typing import List, Tuple, Optional
from collections import defaultdict

def epsilon_perturbation(env,side,rng,eps=0.3):
    if rng.random()<eps:
        return pick_random_per_slot(env,side,rng)
    return best_deterministic_move(env,side,rng)

def make_env_from_state(state)->"BattleEnv":
    dummy=BattleEnv([],[],[],[],seed=0)
    dummy.state=state.clone()
    return dummy

def sim_rest_battle(state: "BattleState",rng,max_steps=60):
    """This will do a rollout when we are at the final leaf. 
    Meaning playing (with whatever algorithm I am playing at the moment) the rest of the battle"""

    env=make_env_from_state(state)
    step=0
    while not env.state.is_terminal() and step<max_steps:
        a_p1=pick_random_per_slot(env,0,rng)
        a_p2=pick_random_per_slot(env,1,rng)
        _,_=env.step(a_p1,a_p2)
        env.state=auto_replace_fainted(env.state)
        step+=1
    return 1 if env.state.result()==1.0 else 0


def compound_key(actions):
    return tuple((a.kind,a.slot,a.move_index,a.target,a.bench_index)for a in actions)

def pick_random_per_slot(env,side,rng): #I was adamant to write this but in the end one must take a knee to the functions
    legal=env.legal_actions(side)
    s0=[a for a in legal if a.slot==0]
    s1=[a for a in legal if a.slot==1]
    out=[]
    if s0:out.append(rng.choice(s0))
    if s1:out.append(rng.choice(s1))
    return out

def best_damage(env,side,slot):
    legal=env.legal_actions(side)
    attacker=env.state.p1.active[slot] if side==0 else env.state.p2.active[slot]
    s=[a for a in legal if a.slot==slot and a.kind==ActionType.USE_MOVE]
    opp =env.state.p2 if side==0 else env.state.p1
    def expected_damage(a):
        mv=attacker.pokemon.moves[a.move_index]
        p_acc=(mv.accuracy/100) if (mv.accuracy is not None) else 1.0
        if getattr(mv,"is_spread",False):
            defenders=[bp for bp in opp.active if _alive(bp)]
            if not defenders:
                return 0.0
            total=0.0
            for d in defenders:
                total+=max(1,int(damage_calc(attacker,d,mv)*0.75))
            return p_acc*total
        if a.target and a.target[0]==side: #protect
            return 0.0
        tslot=a.target[1] if (a.target is not None) else None
        defender=None
        if tslot is not None:
            d=opp.active[tslot] if 0<=tslot<2 else None
            if not _alive(d):
                d=opp.active[1-tslot] if (0<=1-tslot<2 and _alive(opp.active[1-tslot])) else None
            defender=d
        if not _alive(defender):
            return 0.0
        dmg=max(1,int(damage_calc(attacker,defender,mv)))
        return p_acc*dmg
    best=max(s,key=expected_damage)
    return best
        
        


def best_deterministic_move(env,side,rng): #switch or the best attacking
    legal=env.legal_actions(side)
    by_slot={0:[],1:[]}
    for a in legal:
        by_slot[a.slot].append(a)
    picks:List["Action"]=[]
    for slot in (0,1):
        L=by_slot.get(slot,[])
        if not L:
            continue
        sampled=rng.choice(L)
        if sampled.kind==ActionType.SWITCH:
            picks.append(sampled)
        else:
            best=best_damage(env,side,slot)
            picks.append(best if best is not None else sampled)
    return picks






    

def expansion(state:"BattleState",rng,k_first=5, k_after=2):
    "This create childs nodes, selecting a move at random"
    k=k_first if state.turn==1 else k_after

    env0=make_env_from_state(state)
    legal=env0.legal_actions(0)
    s0=[a for a in legal if a.slot==0]
    s1=[a for a in legal if a.slot==1]
    max_unique=max(1,(len(s0)if s0 else 1)*(len(s1)if s1 else 1))
    k=min(k,max_unique)
    seen_keys=set()
    actions_keys:List[Tuple]=[]
    next_states:List["BattleState"]=[]
    tries=0
    while len(actions_keys)<k and tries <20*k:
        tries+=1
        env=make_env_from_state(state) #INMUTABLE ENV ALWAYS GENERATE THE SAME
        a_p1=pick_random_per_slot(env,0,rng)
        key=compound_key(a_p1)
        if key in seen_keys:
            continue
        a_p2=best_deterministic_move(env,1,rng)
        _,_=env.step(a_p1,a_p2)
        env.state=auto_replace_fainted(env.state)
        seen_keys.add(key) 
        actions_keys.append(key)
        next_states.append(env.state.clone())
    return actions_keys, next_states


    
def realize_compound(action_key,env,side):
    "key to ACTION class"
    legal=env.legal_actions(side)
    index={(a.kind, a.slot, a.move_index, a.target, a.bench_index): a for a in legal}
    return [index[k] for k in action_key if k in index]



def state_key(s):
    def sig(bp): return (0,0) if bp is None else (bp.pokemon.id,int(bp.current_hp))
    return (s.turn, tuple(sig(x)for x in s.p1.active),tuple(sig(x)for x in s.p1.bench),tuple(sig(x)for x in s.p2.active),tuple(sig(x)for x in s.p2.bench))

S_visits=defaultdict(int) #NUMBER OF VISITS TO A NODE: N(s)
SA_N=defaultdict(int) #NUMBER OF TIME WE TOOK ACTION A ON NODE S:  N(s,a)
SA_W=defaultdict(float) #NUMBER OF TIMES TAKING ACTION A ON NODE S LED TO WIN: W(s,a)
CHILDREN=defaultdict(list) #ALL NODES, this is crazy
constant=1.4 #Universal constant for the UCT formula

def uct_pick(s_key,children_keys):
    unvisited=[a for a in children_keys if SA_N[(s_key,a)]==0] #priority to unvisited nodes
    if unvisited:
        return random.choice(unvisited)
    N=max(1,S_visits[s_key])
    def score(k):
        n=SA_N[(s_key,k)]
        mu=0.0 if n==0 else SA_W[(s_key,k)]/n
        return mu+constant*(np.sqrt(np.log(N)/(1+n)))
    return max(children_keys,key=score) #does the max applying score to each 

PW_alpha=0.5
PW_C=2.0
def ensure_children(env,rng)->tuple:
    s_key=state_key(env.state)
    kids=CHILDREN[s_key]
    cap=max(1,int(PW_C*(S_visits[s_key]**PW_alpha))) #Trying not to flat the tree
    if len(kids)<cap:
        new_keys,_=expansion(env.state,rng,k_first=cap-len(kids),k_after=cap-len(kids))
        seen=set(kids)
        for k in new_keys:
            if k not in seen:
                kids.append(k)
                seen.add(k)
        CHILDREN[s_key]=kids
    return s_key,kids


def selection(env,side,rng,depth_cap=20):
    path=[]
    depth=0
    while (not env.state.is_terminal()) and depth< depth_cap:
        s_key,children=ensure_children(env,rng)
        if not children:
            break
        a_key=uct_pick(s_key,children)
        path.append((s_key,a_key))
        my_actions=realize_compound(a_key,env,side)
        if not my_actions:
            break
        opp_actions=epsilon_perturbation(env,1-side,rng,0.3)
        _,_=env.step(my_actions,opp_actions)
        env.state=auto_replace_fainted(env.state)
        depth+=1
        if SA_N[(s_key,a_key)]==0:
            break
    return env,path

def full_sim(root_state,side,rng):
    env=make_env_from_state(root_state)
    env,path=selection(env,side,rng,depth_cap=20)
    z=sim_rest_battle(env.state,rng)
    for (s_key,a_key) in path:
        S_visits[s_key]+=1
        SA_N[(s_key,a_key)]+=1
        SA_W[(s_key,a_key)]+=z



def MCTS_pick(root_state,side=0, sims=200,seed=123):
    S_visits.clear()
    SA_N.clear()
    SA_W.clear()
    CHILDREN.clear()
    rng=random.Random(seed)
    for _ in range(sims):
        full_sim(root_state,side,rng)
    root_key=state_key(root_state)
    children=CHILDREN[root_key]
    if not children:
        env=make_env_from_state(root_state)
        print("MCTS WAS NOT SUCCESFUL")
        return pick_random_per_slot(env,side,rng)
    best_key=max(children,key=lambda ak:SA_N[(root_key,ak)])
    env=make_env_from_state(root_state)
    return realize_compound(best_key,env,side)





    


