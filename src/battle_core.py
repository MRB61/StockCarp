from dataclasses import dataclass, replace
from typing import List, Tuple, Optional
from enum import Enum,auto
import random
from src.damage_calc import damage_calc
from src.battle_pokemon import BattlePokemon
from src.move import Move

#BATTLE ENGINE FOR DOUBLES, needs cleaning :D. This is terribly organized sorry.
def _apply_sleep(bp: "BattlePokemon", rng, log): #sleep is a complicated status
    bp.status="slp"
    bp.vol["sleep_counter"]=rng.randint(1,3)
    log.append(f"{bp.pokemon.name} fell asleep!")
def secondary_effects(user: "BattlePokemon", defender: "BattlePokemon" , move,rng,log): #THE MONSTER, atp I should reconsider rewriting from scratch. I have learned so much.
    #STATUS
    if not getattr(defender,"status",None):
        if move.name=="thunder-wave" and ("electric" not in defender.pokemon.types) and ("ground" not in defender.pokemon.types):
            defender.status="par"
            log.append(f"{defender.pokemon.name} is paralyzed!")
        if move.name=="sleep-powder" and ("grass" not in defender.pokemon.types):
            _apply_sleep(defender,rng,log)
            print(f"{defender.pokemon.name} fell asleep!")
        if move.name=="spore" and ("grass" not in defender.pokemon.types):
            _apply_sleep(defender,rng,log)
            log.append(f"{defender.pokemon.name} fell asleep!")
        if move.name=="will-o-wisp" and ("fire" not in defender.pokemon.types):
            defender.status="brn"
            log.append(f"{defender.pokemon.name} is burned!")
        if move.name=="toxic" and ("poison" not in defender.pokemon.types) and ("steel" not in defender.pokemon.types):
            defender.status="psn" #No toxic for now, not really common in VGC
            log.append(f"{defender.pokemon.name} is poisoned!")
    #BOOST
    if move.name=="nasty-plot":
        user.stat_stages["special-attack"]+=2
        log.append("special-attack increases!")
    if move.name=="sword-dance":
        user.stat_stages["attack"]+=2
        log.append("attack increases!")
    if move.name=="calm-mind":
        user.stat_stages["special-attack"]+=1
        user.stat_stages["special-defense"]+=1
        log.append("special-attack increases!")
        log.append("special-defense increases!")
    if move.name=="flame-charge":
        user.stat_stages["speed"]+=1
        log.append("speed increases!")
    if move.name=="dragon-dance":
        user.stat_stages["attack"]+=1
        user.stat_stages["speed"]+=1
        log.append("attack increases!")
        log.append("speed increases!")
    if move.name=="quiver-dance":
        user.stat_stages["special-attack"]+=1
        user.stat_stages["special-defense"]+=1
        user.stat_stages["speed"]+=1
        log.append("special-attack increases!")
        log.append("special-defense increases!")
        log.append("speed increases!")
    if move.name=="iron-defense":
        user.stat_stages["defense"]+=2
        log.append("defense increases!")
    if move.name=="knock-off":
        defender.item=None
        log.append(f"{defender.pokemon.name}'s item was knocked off!")
    if move.name in ("draco-meteor", "leaf-storm", "overheat", "psycho-boost"):
        user.stat_stages["special-attack"]-=2
        log.append("special-attack decreases!")



def _status_precheck(user: "BattlePokemon", move, rng, log) -> bool: #[par,slp,frz,brn,psn]
    "Check before attacking, pray for a second turn wake up :D"

    if user.status == "par":
        if rng.random() < 0.25:
            log.append(f"{user.pokemon.name} is paralyzed! It can't move!")
            return False
    
    if user.status == "slp":
        turns = user.vol.get("sleep_counter", 0)
        if turns > 0:
            log.append(f"{user.pokemon.name} is fast asleep.")
            user.vol["sleep_counter"] = turns - 1
            return False
        else:
            user.status = None
            log.append(f"{user.pokemon.name} woke up!")
    
    if user.status == "frz":
        if rng.random() < 0.20:
            user.status = None
            log.append(f"{user.pokemon.name} thawed out!")
        else:
            log.append(f"{user.pokemon.name} is frozen solid!")
            return False
    return True
def _end_of_turn_status(s, log):
    for bp in (x for x in s.p1.active + s.p2.active if x is not None and not x.is_fainted()):
        if bp.status == "brn":
            chip = max(1, (bp.pokemon.base_stats["hp"]) // 8)
            bp.take_damage(chip)
            log.append(f"{bp.pokemon.name} is hurt by its burn! ({chip})")
        elif bp.status == "psn":
            chip = max(1, (bp.pokemon.base_stats["hp"]) // 8)
            bp.take_damage(chip)
            log.append(f"{bp.pokemon.name} is hurt by poison! ({chip})")

def _stage_multiplier(stage: int)->float:
    stage=max(-6,min(6,stage))
    return(2+stage)/2 if stage>=0 else 2/(2-stage)
def _effective_speed(bp:"BattlePokemon")->float:
    if bp.status=="par":
        par_mult=0.75
    else:
        par_mult=1
    base=bp.pokemon.base_stats["speed"]
    mult=_stage_multiplier(bp.stat_stages.get("speed",0))
    return base*mult*par_mult
def _clone_bp(bp:"BattlePokemon")->"BattlePokemon":   #In order to maybe include a Monte Carlo Tree Search
    from src.battle_pokemon import BattlePokemon   
    nbp=BattlePokemon(bp.pokemon)
    nbp.current_hp = bp.current_hp
    nbp.status = bp.status
    nbp.stat_stages = dict(bp.stat_stages)
    nbp.vol["protect_streak"]=bp.vol.get("protect_streak",0) if hasattr(bp, "vol") else 0
    return nbp
def auto_replace_fainted(state):
    for side_idx in (0, 1):
        side = state.p1 if side_idx == 0 else state.p2
        for slot in (0, 1):
            if not _alive(side.active[slot]):
                for bi, bp in enumerate(side.bench):
                    if _alive(bp):
                        side.active[slot], side.bench[bi] = bp, side.active[slot]
                        #print(f"{side.active[slot]} Enters the Battle!")
                        break
    return state

def _alive(bp:Optional["BattlePokemon"])->bool:
    return (bp is not None) and (not bp.is_fainted())



def _ensure_turn_fields(bp:"BattlePokemon", fresh:bool=False):
    if not hasattr(bp,"vol") or fresh: #If the object has no vol we create it 
        bp.vol={}
    bp.vol.setdefault("protected",False)
    bp.vol.setdefault("protect_streak",0)
    bp.vol["used_protect_this_turn"]=False

def _is_damaging(move:"Move")->bool: 
    #Check if is a damaging move
    return (move.category in ("physical","special")) and (move.power or 0)>0



class ActionType(Enum): #assign a number to the possible move or switch
    USE_MOVE=auto()
    SWITCH=auto()


@dataclass(frozen=True)
class Action:
    kind: ActionType
    side:int #Whether player 1 or 2 (0,1)
    slot:int #Whether we are left or right (0,1)
    move_index: Optional[int]=None
    target: Optional[Tuple[int,int]]=None #(side,slot)
    bench_index: Optional[int]=None #for switch into team


@dataclass
class Side:
    active: List[Optional["BattlePokemon"]]
    bench: List["BattlePokemon"]

def _clone_side(side:"Side")-> "Side": #Montecarlo focused
    return Side(active=[_clone_bp(x) if x is not None else None for x in side.active], bench=[_clone_bp(x) for x in side.bench],)
def _side_alive(side:Side)->int:
    return sum(_alive(bp) for bp in side.active)+ sum(_alive(bp) for bp in side.bench)


@dataclass(frozen=True)
class BattleState: #dataclass is amazing :O it is generating an __init__(self,p1:Side,p2:side, turn:int ,... ) nice.
    p1:"Side"
    p2:"Side"
    turn:int
    rng_state:Tuple[int,...]

    def clone(self)-> "BattleState":
        return BattleState(p1=_clone_side(self.p1), p2=_clone_side(self.p2), turn=self.turn,rng_state=self.rng_state,)
    
    def is_terminal(self)->bool:
        return (_side_alive(self.p1)==0) or (_side_alive(self.p2)==0)
    def result(self)->float|None:
        if not self.is_terminal():
            return None
        a1,a2=_side_alive(self.p1),_side_alive(self.p2)
        return 1.0 if a2==0 else 0.0
    

#ENVIORMENT WHERE WE INITIALIZE THE BATTLE

class BattleEnv:
    def __init__(self,p1_active:List["BattlePokemon"],p1_bench:List["BattlePokemon"],p2_active:List["BattlePokemon"],p2_bench:List["BattlePokemon"], seed:int=42):
        
        a1=list(p1_active[:2])+[None,None]
        a2=list(p2_active[:2])+[None,None] #IN CASE 1VS2 HAPPENS

        self.rng=random.Random(seed)
        for bp in (x for x in a1[:2]+a2[:2] if x is not None):
            _ensure_turn_fields(bp)
        self.state = BattleState(
            p1=Side(active=a1[:2], bench=list(p1_bench)),
            p2=Side(active=a2[:2], bench=list(p2_bench)),
            turn=1,
            rng_state=self.rng.getstate(),)
        






    def legal_actions(self, side:int)->List[Action]:
        S=self.state.p1 if side==0 else self.state.p2
        actions:List[Action]=[]
        for slot in (0,1):
            if not _alive(S.active[slot]):
                continue
            for bi,bench_bp in enumerate(S.bench):
                if _alive(bench_bp):
                    actions.append(Action(ActionType.SWITCH,side,slot,bench_index=bi))
        
        opp=self.state.p2 if side==0 else self.state.p1
        foe_slots=[(1-side,i) for i in (0,1) if _alive(opp.active[i])]
        for slot in (0,1):
            bp=S.active[slot]
            if not _alive(bp):
                continue
            for mi,mv in enumerate(bp.pokemon.moves):
                if getattr(mv, "is_protect", False):
                    actions.append(Action(ActionType.USE_MOVE,side,slot,move_index=mi, target=(side,slot)))
                elif getattr(mv, "is_spread", False):
                    actions.append(Action(ActionType.USE_MOVE,side,slot,move_index=mi,target=None))    
                else:
                    for t in foe_slots:
                        actions.append(Action(ActionType.USE_MOVE,side,slot,move_index=mi,target=t))
        return actions
    
    
    
    def _turn_order(self,rng:random.Random):
        s1,s2=_effective_speed(self.state.p1), _effective_speed(self.state.p2)
        if s1>s2: return(0,1)
        if s2>s1: return(1,0)
        return (0,1) if rng.random()<0.5 else (1,0)#speedtie
    def _resolve_attack(self,attacker:"BattlePokemon", defender:"BattlePokemon", move, rng:random.Random, log:list[str])->bool:
        if move.accuracy is not None and rng.uniform(0,100)>move.accuracy:
            log.append(f"{attacker.pokemon.name} {move.name} missed!")
            return defender.is_fainted()
        dmg=max(1,int(damage_calc(attacker,defender,move)))
        defender.take_damage(dmg)
        log.append(f"{attacker.pokemon.name.title()} used {move.name}! "
            f"{defender.pokemon.name.title()} took {dmg} (HP {defender.current_hp})."
        )
        if defender.is_fainted():
            log.append(f"{defender.pokemon.name} fainted!")
            return True
        return False
    

    def step(self,actions_p1: List[Action], actions_p2:List[Action])->Tuple[BattleState, List[str]]:
        rng=random.Random();rng.setstate(self.state.rng_state)
        log:list[str]=[f"---Turn {self.state.turn}---"]
    
        s=self.state.clone() #Again for MCTS
        
        for bp in (x for x in s.p1.active+s.p2.active if x is not None):
            _ensure_turn_fields(bp)
            bp.vol["protected"]=False
            bp.vol["used_protect_this_turn"]=False
            redirector={0:None, 1:None}
        #SWITCHING HAS PRIORITY no pursuit for now
        switch_actions=[a for a in actions_p1+actions_p2 if a.kind is ActionType.SWITCH]
        def switch_speed_key(a:Action):
            side=s.p1 if a.side==0 else s.p2
            bp=side.active[a.slot]
            spd=_effective_speed(bp) if _alive(bp) else -1 
            return(-spd, rng.random())
        switch_actions.sort(key=switch_speed_key)
        for a in switch_actions:
            self._do_switch(s,a,log)
        #MOVES
        move_actions=[a for a in actions_p1+actions_p2 if a.kind is ActionType.USE_MOVE]
        enriched=[]
        for a in move_actions:
            user=(s.p1.active[a.slot] if a.side==0 else s.p2.active[a.slot])
            if not _alive(user):
                continue #user dead or None then out of THE FOR!!!!
            move=user.pokemon.moves[a.move_index]
            prio=getattr(move,"priority",0) or 0
            spd=_effective_speed(user)
            enriched.append((prio,spd,rng.random(),a)) #sorting priority, then speed
        enriched.sort(key=lambda t: (-t[0],-t[1], t[2]))

        for _,_,_,a in enriched:
            side=s.p1 if a.side==0 else s.p2
            user=side.active[a.slot]
            if not _alive(user): #ANOTHER CHECK
                continue
            move=user.pokemon.moves[a.move_index]
            if not _status_precheck(user,move,rng,log):
                continue
            if move.name in ("follow-me", "rage-powder"):
                redirector[a.side]=(a.slot,move.name)
                log.append(f"{user.pokemon.name} used {move.name}! It became the center of attention")
                continue
            if getattr(move, "is_protect", False):
                self._try_protect(user,rng,log)
                continue
            targets:List[Tuple[int,int]]=[]
            if getattr(move,"is_spread",False):
                opp=s.p2 if a.side==0 else s.p1
                for i in (0,1):
                    if _alive(opp.active[i]):
                        targets.append((1-a.side,i))
            else:
                if a.target is not None:
                    tside, tslot=a.target
                    if tside !=a.side:
                        red=redirector.get(tside)
                        if red is not None:
                            rslot,rname=red
                            rmon=(s.p1 if tside==0 else s.p2).active[rslot]
                            immune=(rname=="rage-powder") and ("grass" in user.pokemon.types)
                            if _alive(rmon) and not immune:
                                tslot=rslot #REDIRECTION
                    ts=s.p1 if tside==0 else s.p2
                    if _alive(ts.active[tslot]):
                        targets.append((tside,tslot))

            if not targets:
                log.append("NO VALID TARGET")
                continue

            if (move.accuracy is not None) and (rng.uniform(0,100)>move.accuracy):
                log.append(f"{user.pokemon.name} {move.name} missed!")
                continue
            spread_mult=0.75 if getattr(move, "is_spread",False) and len(targets)>=2 else 1.0
            for (tside,tslot) in targets:
                ts=s.p1 if tside==0 else s.p2
                defender=ts.active[tslot] #WE ARE IN TARGETS, thus this defender def
                if defender.is_fainted():
                    defender=ts.active[1-tslot] if _alive(ts.active[1-tslot]) else None
                if defender.is_fainted():
                    log.append("WTF?")
                    continue
                if defender.vol.get("protected",False) and _is_damaging(move):
                    log.append(f"{defender.pokemon.name} protected itself!")
                    continue
                dmg=max(1,int(damage_calc(user,defender,move)*spread_mult))
                secondary_effects(user,defender,move,rng,log)
                defender.take_damage(dmg)
                log.append(f"{user.pokemon.name.title()} used {move.name}! "
                    f"{defender.pokemon.name.title()} took {dmg} (HP {defender.current_hp}).")
                if defender.is_fainted():
                    log.append(f"{defender.pokemon.name} fainted!")
        for bp in (x for x in s.p1.active+s.p2.active if x is not None):
            if not bp.vol.get("used_protect_this_turn",False):
                bp.vol["protect_streak"]=0
        #Chip damage
        _end_of_turn_status(s,log)
        #Prepare next turn
        s=replace(s,turn=s.turn+1,rng_state=rng.getstate())
        self.state=s
        return s,log

        



#SWITCHING AND PROTECT DEFINITIONS
    def _do_switch(self, s:BattleState, a:Action, log:List[str]):
        side=s.p1 if a.side==0 else s.p2
        if not _alive(side.active[a.slot]):
            return
        if a.bench_index is None or a.bench_index<0 or a.bench_index>=len(side.bench):
            return
        out_pokemon=side.active[a.slot]
        out_pokemon.stat_stages={"attack": 0, "defense": 0, "special-attack": 0,
            "special-defense": 0, "speed": 0, "accuracy": 0, "evasion": 0
        }
        in_pokemon=side.bench[a.bench_index]
        side.active[a.slot],side.bench[a.bench_index]=in_pokemon,out_pokemon
        _ensure_turn_fields(side.active[a.slot])
        log.append(f"{out_pokemon.pokemon.name} switched out." f"{side.active[a.slot].pokemon.name} entered!")
    def _try_protect(self, bp: "BattlePokemon", rng:random.Random, log:List[str]):
        k=bp.vol.get("protect_streak",0)
        p=1.0 if k==0 else (1/3)**k
        if rng.random()<=p:
            bp.vol["protected"]=True
            bp.vol["protect_streak"]=k+1
            bp.vol["used_protect_this_turn"]=True
            log.append(f"{bp.pokemon.name} protected itself!")
        else:
            bp.vol["protected"]=False
            bp.vol["protect_streak"]=0
            bp.vol["used_protect_this_turn"]=True
            log.append(f"{bp.pokemon.name} tried to Protect but failed!")
        