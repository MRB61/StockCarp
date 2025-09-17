import sys, os
sys.path.insert(0, r"C:\Users\Manuel\StockCarp")
from poke_env.player import Player, RandomPlayer 
from poke_env.data import GenData
from poke_env.player.battle_order import BattleOrder 
from poke_env import AccountConfiguration,ServerConfiguration,LocalhostServerConfiguration
from src.pokemon import Pokemon
from src.battle_pokemon import BattlePokemon
from src.battle_core import BattleEnv,ActionType
from src.MCTS import MCTS_pick
from src.move import Move
import unicodedata,re

















STAT_KEYS = ["hp","attack","defense","special-attack","special-defense","speed"]
PROTECTS = {"Protect","Detect","Spiky Shield","Baneful Bunker","Obstruct","Silktrap"}
def _calc_stats(base_stats: dict, evs: dict, level=50, nature_mult: dict | None = None) -> dict:
    ivs = {k: 31 for k in STAT_KEYS} #Almost always we use 31 iv on everything.
    evs = {k: max(0, min(252, int(evs.get(k, 0)))) for k in STAT_KEYS}
    nature_mult = nature_mult or {k: 1.0 for k in STAT_KEYS}
    out = {}
    for k in STAT_KEYS:
        B = int(base_stats[k])
        IV = int(ivs.get(k, 31))
        EVq = evs[k] // 4
        if k == "hp":
            out[k] = ((2*B + IV + EVq) * level) // 100 + level + 10
        else:
            val = ((2*B + IV + EVq) * level) // 100 + 5
            out[k] = int(val * float(nature_mult.get(k, 1.0)))
    return out
def team_from_PS(team_names,movesets,abilities,items,current_hp,EVs=[{"hp":252, "attack":252,"defense":4,"special-attack":0,"special-defense":0,"speed":0},
                                                          {"hp":252, "attack":252,"defense":4,"special-attack":0,"special-defense":0,"speed":0},
                                                          {"hp":252, "attack":252,"defense":4,"special-attack":0,"special-defense":0,"speed":0},
                                                          {"hp":252, "attack":252,"defense":4,"special-attack":0,"special-defense":0,"speed":0},
                                                          {"hp":252, "attack":252,"defense":4,"special-attack":0,"special-defense":0,"speed":0},
                                                          {"hp":252, "attack":252,"defense":4,"special-attack":0,"special-defense":0,"speed":0},],is_opp=False):
    team=[]
    pokedex=GenData.from_gen(9).load_pokedex(9)
    movedex=GenData.from_gen(9).load_moves(9)
    for i,name in enumerate(team_names):
        movimientos=[]
        for j,move in enumerate(movesets[i]):
            real=movedex.get(move)
            movimientos.append(Move(real["name"],real["type"],real["basePower"],accuracy=real["accuracy"],category=real["category"],priority=real["priority"],))
            if real["name"] in PROTECTS:
                movimientos[j].is_protect=True
            if real["target"]=="allAdjacentFoes":
                movimientos[j].is_spread=True
         
        poke=pokedex.get(name)
        bs=poke["baseStats"]
        p=Pokemon(name=poke["name"],types=poke["types"],stats={
                "hp": bs["hp"],
                "attack": bs["atk"],
                "defense": bs["def"],
                "special-attack": bs["spa"],
                "special-defense": bs["spd"],
                "speed": bs["spe"],
            },abilities=poke["abilities"],moves=movimientos,id=poke["num"])
        stats=_calc_stats(p.base_stats,evs=EVs[i])
        p.base_stats=stats
        bp=BattlePokemon(p)
        bp.item=items[i]
        bp.ability=abilities[i]
        if is_opp:
            if current_hp[i]==0:#Simple bypass to not make my engine think the two mons in the back are defeated. Bit conservative.
                current_hp[i]=100
            bp.current_hp=(current_hp[i]/100)*p.base_stats["hp"] #BECAUSE POKE-ENV GIVES %OF HP LEFT WHEN REFERRING TO OPPS.
        else:
            bp.current_hp=current_hp[i]
        team.append(bp)
    return team

def ps_id(name: str) -> str:
    s = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode("ascii")
    return re.sub(r"[^a-z0-9]+", "", s.lower())

class RawBattleOrder(BattleOrder):
    __slots__ = ("message",)
    def __init__(self, message: str):
        self.message = message

class Probando(Player):
    def __init__(self,*args,**kwargs):
        super().__init__(*args, **kwargs)
        self.logged_once=False
        self.picked_four={}



    def actions_to_ps_order(self, battle, actions, p1_active, p1_bench):
        orders=[None,None]
        picks=[None,None]
        targets=[None,None]
        for i,a in enumerate(actions):
            if a.kind.name=="SWITCH":
                orders[i]="switch"
                picks[i]=ps_id(battle.available_switches[i][a.bench_index].name)
                targets[i]=""
                continue
            orders[i]="move"
            if a.target==(1,0):
                targets[i]=1
            elif a.target==(1,1):
                targets[i]=2
            else:
                targets[i]=""
            if len(battle.available_moves[i])>1:
                mv=battle.available_moves[i][a.move_index]._id
                picks[i]=mv
            else:
                mv=battle.available_moves[i][0]._id
                picks[i]=mv
        return f"/choose {orders[0]} {picks[0]} {targets[0]},{orders[1]} {picks[1]} {targets[1]}"


    


    def _data_from_battle(self,battle): #TAKE DATA FROM BATTLE CLASS AND TRANSFORM IT INTO MY ENGINE.
        my_vals=list(battle.team.values())
        p1_names=[getattr(p,"_species",None)for p in my_vals]
        p1_items=[getattr(p,"_item",None) for p  in my_vals]
        p1_current_hp=[]
        p1_current_hp=[(getattr(p,"_current_hp",None)or 0) for p in my_vals]

        p1_moves=[[m._id for m in getattr(p,"_moves",{}).values()] for p in my_vals]
        p1_team=team_from_PS(team_names=p1_names,movesets=p1_moves,abilities=["","","","","",""],items=p1_items,current_hp=p1_current_hp)
        
        active=[getattr(p,"_species",None) for p in battle.active_pokemon]
        ids_1={name:i for i, name in enumerate(p1_names)}
        act_id_1=[ids_1[n] for n in active if n in ids_1]
        p1_active=[p1_team[i] for i in act_id_1]                 #NEEDS FIX
        rest_id_1=[i for i in range(6) if i not in set(act_id_1)]
        p1_bench=[p1_team[i] for i in rest_id_1[:2]]
        
        

        opp_vals=list(battle.opponent_team.values())
        p2_names=[getattr(p,"_species",None)for p in opp_vals]
        p2_items=[getattr(p,"_item",None) for p  in opp_vals]
        p2_current_hp=[(getattr(p,"_current_hp",None)or 0) for p in opp_vals]
        p2_moves=[[m._id for m in getattr(p,"_moves",{}).values()] for p in opp_vals]
        
        p1_team=team_from_PS(team_names=p1_names,movesets=p1_moves,abilities=["","","","","",""],items=p1_items,current_hp=p1_current_hp)#Curerntly my engine do not support abilities.
        p2_team=team_from_PS(team_names=p2_names,movesets=p2_moves,abilities=["","","","","",""],items=p2_items,current_hp=p2_current_hp,is_opp=True)
        
        
        active_opp=[getattr(p,"_species",None) for p in battle.opponent_active_pokemon]
        ids_2={name:i for i, name in enumerate(p2_names)}
        act_id_2=[ids_2[n] for n in active_opp if n in ids_2]
        p2_active=[p2_team[i] for i in act_id_2]                  #NEEDS FIX
        rest_id_2=[i for i in range(6) if i not in set(act_id_2)]
        p2_bench=[p2_team[i] for i in rest_id_2[:2]]
        
        
        return p1_active,p1_bench,p2_active,p2_bench

    
    def _data_to_MCTS_to_PS(self,p1_active,p1_bench,p2_active,p2_bench):
        env=BattleEnv(p1_active=p1_active,p1_bench=p1_bench,p2_active=p2_active,p2_bench=p2_bench)
        
        return MCTS_pick(env.state,side=0,sims=600)



    def choose_move(self, battle):
        req=battle.last_request
        if "forceSwitch" in req:
            print("FORCED SWITCH",flush=True)
            return self.choose_default_move()
        
        p1_active,p1_bench,p2_active,p2_bench=self._data_from_battle(battle)
        if len(p1_active)==0 or len(p1_active)==1 or len(p2_active)<=1: #NEEDS FIX
            print("LENGTH DERANGED",flush=True)
            return self.choose_random_move(battle)
        print(p2_active,flush=True)
        actions=self._data_to_MCTS_to_PS(p1_active,p1_bench,p2_active,p2_bench)
        print(actions,flush=True)
        order=self.actions_to_ps_order(battle,actions,p1_active,p1_bench)
        print(order,flush=True)
        return RawBattleOrder(order)
        
        
    
    def teampreview(self, battle):
        
        #order = [1, 2, 3, 4, 5, 6]
        #self.picked_four[battle.battle_tag] = order[:4]
        return "/team 1234"
    
