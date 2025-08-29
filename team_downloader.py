import requests,json,os,pickle
from typing import List,Dict,Union,Optional,Tuple
from src.pokemon import Pokemon
from src.battle_pokemon import BattlePokemon
from src.move import Move
#FULL POKEAPI ORIENTED
SESSION=requests.Session()
STAT_KEYS = ["hp", "attack", "defense", "special-attack", "special-defense", "speed"]

def fetch_pokemon_data(pokemon_name, save_dir="data/raw/"):
    url = f"https://pokeapi.co/api/v2/pokemon/{pokemon_name}"
    r = SESSION.get(url, timeout=20)
    r.raise_for_status()
    data = r.json()
    os.makedirs(save_dir, exist_ok=True)
    with open(os.path.join(save_dir, f"{pokemon_name}.json"), "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    return data

def _fetch_move_by_name(name: str) -> Move:
    url = f"https://pokeapi.co/api/v2/move/{name}"
    r = SESSION.get(url, timeout=15); r.raise_for_status()
    m = r.json()
    return Move(
        name=m["name"],
        move_type=m["type"]["name"],
        power=m.get("power") or 0,
        accuracy=m.get("accuracy"),                     #None means always hits
        category=m["damage_class"]["name"],
        priority=m.get("priority", 0),
        is_protect=m["name"] in {
            "protect","detect","spiky-shield","kings-shield","baneful-bunker","silk-trap","obstruct"
        },
        is_spread=(m.get("target", {}) or {}).get("name") in {"all-opponents","all-other-pokemon"},
    )

def clean_info(data) -> Pokemon:
    name = data["name"]
    types = [t["type"]["name"] for t in data["types"]]
    stats = {s["stat"]["name"]: s["base_stat"] for s in data["stats"]}
    abilities = [a["ability"]["name"] for a in data["abilities"]]
    pid = data["id"]
    move_objs = []
    for m in data["moves"]:
        mname = m["move"]["name"]                 # <- this is the correct field
        move_objs.append(_fetch_move_by_name(mname))

    return Pokemon(name, types, stats, abilities, move_objs, pid)
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



def pokemon_build(pokemon: Pokemon,moveset: list[str],ability: str,item: str | None,EV: dict,level: int = 50, nature_mult: dict | None = None) -> BattlePokemon:

    norm = lambda s: s.strip().lower().replace(" ", "-") #PokeAPI already uses this format
    by_name = {norm(m.name): m for m in pokemon.moves}
    picked = []
    if pokemon.name=="smeargle": #The smeargle incident
        moves=[]
        for a in moveset:
            moves.append(_fetch_move_by_name(a))
        pokemon.moves=picked
        if ability not in pokemon.abilities:
            raise ValueError(f"Ability '{ability}' not in {pokemon.abilities}")
        final_stats = _calc_stats(pokemon.base_stats, EV, level=level, nature_mult=nature_mult)
        pokemon.base_stats = final_stats
        bp = BattlePokemon(pokemon)
        bp.current_hp = final_stats["hp"]
        bp.item = item
        bp.ability = ability
        return bp
    for n in moveset:
        key = norm(n)
        if key not in by_name:
            raise ValueError(f"Unknown move for {pokemon.name}: '{n}'")
        picked.append(by_name[key])
    pokemon.moves = picked
    if ability not in pokemon.abilities:
        raise ValueError(f"Ability '{ability}' not in {pokemon.abilities}")
    final_stats = _calc_stats(pokemon.base_stats, EV, level=level, nature_mult=nature_mult)
    pokemon.base_stats = final_stats
    bp = BattlePokemon(pokemon)
    bp.current_hp = final_stats["hp"]
    bp.item = item
    bp.ability = ability
    return bp

def team_downloader(team_name:str,ids:List[Union[int,str]],movesets:List[List[str]],EV:List[Dict[str,int]],abilities:List[str],items:List[Optional[str]],save_dir="data/clean/teams",level=50)->Tuple[str,str]:
    if not(len(ids)==len(movesets)==len(EV)==len(abilities)==len(items)):
        raise ValueError("Inputs must be same length")
    os.makedirs(save_dir,exist_ok=True)
    team_bps,team_json=[],[]
    for i,pid in enumerate(ids):
        raw=fetch_pokemon_data(pid);pk=clean_info(raw)
        bp=pokemon_build(pk,movesets[i],abilities[i],items[i],EV[i],level)
        team_bps.append(bp)
        team_json.append({
            "id":pk.id,"name":pk.name,"types":pk.types,"level":level,
            "ability":abilities[i],"item":items[i],"stats":pk.base_stats,
            "current_hp":bp.current_hp,"evs":EV[i],
            "moves":[m.name for m in pk.moves]
        })
    pkl_path,jsn_path=os.path.join(save_dir,f"{team_name}.pkl"),os.path.join(save_dir,f"{team_name}.json")
    with open(pkl_path,"wb") as f:pickle.dump(team_bps,f)
    with open(jsn_path,"w",encoding="utf-8") as f:json.dump(team_json,f,indent=2,ensure_ascii=False)
    return pkl_path,jsn_path




    