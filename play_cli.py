from typing import List, Tuple
import random,pickle
from src.battle_core import BattleEnv, Action, ActionType, auto_replace_fainted, _alive
from src.battle_pokemon import BattlePokemon
from src.team_builder import team_selection
from src.MCTS import MCTS_pick, best_deterministic_move


def hp_bar(bp:"BattlePokemon", width=20):
    if bp is None: return "-"*width
    cur=int(max(0,bp.current_hp))
    max_hp=bp.pokemon.base_stats["hp"]
    fill=int(width*max(0,cur)/max(1,max_hp))
    return "["+"#"*fill + "-"*(width-fill)+f"]{cur}/{max_hp}"

def show_state(env:"BattleEnv"):
    s=env.state
    print("Player 1 active")
    for i,bp in enumerate(s.p1.active):
        name=bp.pokemon.name if _alive(bp) else "-"
        print(f"slot {i}: {name:20} {hp_bar(bp)}")
    print("Player 1 bench:",[b.pokemon.name for b in s.p1.bench if _alive(b)])
    print("Player 2 active:")
    for i, bp in enumerate(s.p2.active):
        name = bp.pokemon.name if _alive(bp) else "—"
        print(f"  slot {i}: {name:16} {hp_bar(bp)}")
    print("Player 2 bench:", [b.pokemon.name for b in s.p2.bench if _alive(b)])
def list_actions(env,side:int)->List[Action]:
    legal=env.legal_actions(side)
    legal.sort(key=lambda a: (a.slot, a.kind.value, a.move_index if a.move_index is not None else -1))
    opp= env.state.p2.active if side==0 else env.state.p1.active
    for idx, a in enumerate(legal):
        if a.kind == ActionType.USE_MOVE:
            user = env.state.p1.active[a.slot] if side==0 else env.state.p2.active[a.slot]
            mv   = user.pokemon.moves[a.move_index]
            tgt  = "self" if not a.target else (f"{opp[0].pokemon.name}" if a.target[1]==0 else f"{opp[1].pokemon.name}")
            print(f"[{idx:02d}] slot {a.slot} MOVE  {mv.name:16} -> {tgt}")
        else:
            S = env.state.p1 if side==0 else env.state.p2
            incoming = S.bench[a.bench_index].pokemon.name
            print(f"[{idx:02d}] slot {a.slot} SWITCH -> {incoming}")
    return legal
def ask_actions(env,side:int)->List[Action]:
    legal=list_actions(env,side)
    chosen:List[Action]=[]
    by_slot={0:[a for a in legal if a.slot==0], 1: [a for a in legal if a.slot==1]}
    for slot in (0,1):
        L=by_slot[slot]
        if not L:
            continue
        while True:
            s=input(f"Pick action for slot {slot} or g for my actual deterministic algorithm and r for random:").strip().lower()
            if s=="":
                break
            if s=="g":
                a=best_deterministic_move(env,side,random.Random(0))
                chosen.extend([x for x in a if x.slot==slot])
                break
            if s=="r":
                chosen.append(random.choice(L))
                break
            try:
                idx=int(s)
                if 0<= idx< len(legal) and legal[idx].slot==slot:
                    chosen.append(legal[idx])
                    break
            except:
                pass
            print("Invalid!")

    return chosen
import ast

def parse_ids(prompt: str):
    while True:
        s = input(prompt).strip()
        try:
            if s.startswith("["):                     
                vals = ast.literal_eval(s)            
                ids = [int(x) for x in vals]
            else:                                     
                ids = [int(x) for x in s.replace(" ", "").split(",") if x]
            if len(ids) != 4:
                print("Please enter exactly 4 IDs.")
                continue
            return ids
        except Exception:
            print("Couldn't parse the input")

def main():
    print("Select your team.")
    name=input()
    with open(f"data/clean/teams/{name}.pkl","rb") as f:
        team_2=pickle.load(f)
    print("Select your rival's team.")
    name=input()
    with open(f"data/clean/teams/{name}.pkl","rb") as f:
        team_1=pickle.load(f)
    print("Select your order")
    order=input()
    order=[int(x) for x in order.replace(" ", "").split(",") if x]
    p1_active,p1_bench=[team_1[order[0]],team_1[order[1]]],[team_1[order[2]],team_1[order[3]]]
    p2_active,p2_bench=[team_2[order[0]],team_2[order[1]]],[team_2[order[2]],team_2[order[3]]]
    env=BattleEnv(p1_active, p1_bench,p2_active,p2_bench, seed=123)
    rng_ai=random.Random(42)
    print("You are playing against StockCarp!")
    while not env.state.is_terminal():
        show_state(env)
        a_p1=MCTS_pick(env.state,side=0,sims=300,seed=123)
        print("\nYour moves:")
        a_p2=ask_actions(env,side=1)
        _,log=env.step(a_p1,a_p2)
        print("\n".join(log))
        env.state=auto_replace_fainted(env.state)

    res=env.state.result()
    if res==1.0: print("StockCarp wins!")
    elif res==0.0: print("You win!")
    else: print("Ayiyi")
if __name__=="__main__":
    main()

