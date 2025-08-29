import os, json, pickle, random
from typing import List, Tuple, Optional, Dict, Any
from fastapi import FastAPI, HTTPException, Query
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from src.battle_core import BattleEnv, Action, ActionType, auto_replace_fainted, _alive
from src.battle_pokemon import BattlePokemon
from src.team_selector import team_selecting_policy

APP = FastAPI()
APP.mount("/static", StaticFiles(directory="static"), name="static")

# ---------- TEAM LOADING ----------
TEAMS_DIR = "data/clean/teams"

def _list_team_files()->List[str]:
    if not os.path.isdir(TEAMS_DIR): return []
    out=[]
    for fn in os.listdir(TEAMS_DIR):
        if fn.lower().endswith((".pkl",".json")):
            out.append(os.path.splitext(fn)[0])       # no extension
    return sorted(out)

def _load_team_objects(team_name:str)->List[Any]:
    """Return list of 6  objects (BattlePokemon)."""
    base = os.path.join(TEAMS_DIR, team_name)
    if os.path.exists(base + ".pkl"):
        with open(base + ".pkl","rb") as f:
            return pickle.load(f)
    if os.path.exists(base + ".json"):
        with open(base + ".json","r",encoding="utf-8") as f:
            data=json.load(f)
        return data
    raise HTTPException(404, f"team '{team_name}' not found")

def _bp_from_obj(obj)->BattlePokemon:
    """Normalize: if given a BattlePokemon, clone a fresh BP from its Pokemon.
       If given a Pokemon-like object, wrap into BattlePokemon."""
    if hasattr(obj, "pokemon"):   # looks like BattlePokemon
        return BattlePokemon(obj.pokemon)
    return BattlePokemon(obj)      # assume 'obj' is Pokemon

def _bp_view(bp)->Dict:
    if not _alive(bp): return {"alive":False}
    mx=bp.pokemon.base_stats["hp"]
    return {
        "alive":True,"id":bp.pokemon.id,"name":bp.pokemon.name,
        "hp":bp.current_hp,"max_hp":mx,"status":bp.status,"types":bp.pokemon.types
    }

def _obj_meta(obj)->Dict:
    """Lightweight metadata for UI (for team preview)."""
    p = obj.pokemon if hasattr(obj,"pokemon") else obj
    return {"id": getattr(p,"id",0), "name": getattr(p,"name","unknown"), "types": getattr(p,"types",[])}

# ---------- EXISTING VIEW HELPERS ----------
def state_view(env:BattleEnv)->Dict:
    s=env.state
    return {
        "turn":s.turn,
        "p1":{"active":[_bp_view(x) for x in s.p1.active],"bench":[_bp_view(x) for x in s.p1.bench]},
        "p2":{"active":[_bp_view(x) for x in s.p2.active],"bench":[_bp_view(x) for x in s.p2.bench]},
        "terminal":s.is_terminal(),"result":s.result()
    }

def label_action(env,side,a:Action)->str:
    if a.kind==ActionType.SWITCH:
        b=(env.state.p1 if side==0 else env.state.p2).bench[a.bench_index]
        return f"slot {a.slot} SWITCH→{b.pokemon.name}"
    mv=(env.state.p1 if side==0 else env.state.p2).active[a.slot].pokemon.moves[a.move_index]
    if getattr(mv,"is_protect",False): return f"slot {a.slot} {mv.name}→self"
    if getattr(mv,"is_spread",False):  return f"slot {a.slot} {mv.name}→both"
    tside,tslot=a.target
    opp=(env.state.p1 if tside==0 else env.state.p2).active[tslot]
    tgt=opp.pokemon.name if _alive(opp) else "fainted"
    return f"slot {a.slot} {mv.name}→{tgt}"

def legal_by_slot(env,side,slot)->List[Action]:
    return [a for a in env.legal_actions(side) if a.slot==slot]

def pack_action(a:Action)->Dict:
    return {
        "kind":"SWITCH" if a.kind==ActionType.SWITCH else "MOVE",
        "slot":a.slot, "move_index":a.move_index,
        "bench_index":a.bench_index, "target":a.target
    }

def unpack_action(side:int,d:Dict)->Action:
    kind=ActionType.SWITCH if d["kind"]=="SWITCH" else ActionType.USE_MOVE
    tgt = tuple(d["target"]) if d.get("target") is not None else None
    return Action(kind,side,d["slot"],move_index=d.get("move_index"),target=tgt,bench_index=d.get("bench_index"))

# ---------- ROUTES ----------
@APP.get("/")
def index(): return FileResponse("static/index.html")

@APP.get("/api/teams")
def list_teams():
    """List available premade teams (filenames without extension)."""
    return {"teams": _list_team_files()}

@APP.get("/api/team")
def get_team(name: str = Query(..., description="team filename without extension")):
    """Return the 6 mons of a team for preview."""
    objs=_load_team_objects(name)
    if len(objs)!=6: raise HTTPException(400,"team must have 6 mons")
    return {"name":name, "mons":[_obj_meta(x) for x in objs]}

class NewGameTeamsReq(BaseModel):
    ai_team: str                 # AI team name (6 mons saved in data/clean/teams)
    you_team: str                # Human team name
    you_pick: List[int]          # 4 indices (0..5) in order: [active0, active1, bench0, bench1]
    ai_auto: bool = True         # if True, server auto-selects the AI's four
    ai_pick: Optional[List[int]] = None  # used only when ai_auto=False
    sims: int = 100              # simulations for the selector
    seed: int = 123
class ActReq(BaseModel):
    you_actions:List[Dict]
    ai_policy:str="mcts"
    sims:int=200
    seed:int=123

ENV: Optional[BattleEnv]=None

def _side_from_team(team_name:str, pick:List[int])->Tuple[List[BattlePokemon],List[BattlePokemon]]:
    objs=_load_team_objects(team_name)
    if len(objs)!=6: raise HTTPException(400,"team must have 6 mons")
    if len(pick)!=4: raise HTTPException(400,"pick exactly 4 indices")
    if any((i<0 or i>=6) for i in pick): raise HTTPException(400,"pick indices must be 0..5")
    chosen=[objs[i] for i in pick]          # keep order selected
    bps=[_bp_from_obj(x) for x in chosen]   # fresh BPs
    active=bps[:2]
    bench=bps[2:]
    return active, bench

@APP.post("/api/new_game_teams")
def new_game_teams(req: NewGameTeamsReq):
    global ENV

    # Load both full teams (6 mons each)
    ai_objs  = _load_team_objects(req.ai_team)
    you_objs = _load_team_objects(req.you_team)
    if len(ai_objs) != 6 or len(you_objs) != 6:
        raise HTTPException(400, "teams must have 6 mons")

    # Human side (player 2) from explicit picks
    p2a, p2b = _side_from_team(req.you_team, req.you_pick)

    # AI side (player 1): auto-pick or explicit
    if req.ai_auto:
        # fresh BPs for selector on full 6v6 preview
        ai_team  = [_bp_from_obj(x) for x in ai_objs]
        you_team = [_bp_from_obj(x) for x in you_objs]
        selection = team_selecting_policy(ai_team, you_team, sims=req.sims)
        p1a, p1b = [selection[0], selection[1]], [selection[2], selection[3]]
    else:
        if not req.ai_pick or len(req.ai_pick) != 4:
            raise HTTPException(400, "when ai_auto=false, provide ai_pick of length 4 (indices 0..5)")
        p1a, p1b = _side_from_team(req.ai_team, req.ai_pick)

    # Start the battle
    ENV = BattleEnv(p1a, p1b, p2a, p2b, seed=req.seed)
    return state_view(ENV)

@APP.get("/api/state")
def get_state():
    if ENV is None: raise HTTPException(400,"no game")
    return state_view(ENV)

@APP.get("/api/legal_actions")
def legal(side:int):
    if ENV is None: raise HTTPException(400,"no game")
    out={}
    for slot in (0,1):
        acts=legal_by_slot(ENV,side,slot)
        out[str(slot)]=[{"label":label_action(ENV,side,a),"payload":pack_action(a)} for a in acts]
    return out

@APP.post("/api/act")
def act(req:ActReq):
    if ENV is None: raise HTTPException(400,"no game")
    a_you=[unpack_action(1,p) for p in req.you_actions]
    if req.ai_policy=="mcts":
        from src.MCTS import MCTS_pick
        a_ai=MCTS_pick(ENV.state,side=0,sims=req.sims,seed=req.seed)
    elif req.ai_policy=="greedy":
        from src.MCTS import best_deterministic_move
        a_ai=best_deterministic_move(ENV,0,random.Random(req.seed))
    else:
        from src.MCTS import pick_random_per_slot
        a_ai=pick_random_per_slot(ENV,0,random.Random(req.seed))
    _,log=ENV.step(a_ai,a_you)
    ENV.state=auto_replace_fainted(ENV.state)
    return {"log":log,"state":state_view(ENV)}
