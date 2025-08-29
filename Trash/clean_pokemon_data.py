import json
from src.pokemon import Pokemon
from src.move import Move
import requests
import numpy as np

with open("data/clean/movesets_regI.json", "r", encoding="utf-8") as f:
    MOVESETS = json.load(f)

SESSION = requests.Session()








def clean_info(data):
    name=data["name"]
    types=[t["type"]["name"] for t in data["types"]]
    stats={stat["stat"]["name"]: np.floor(0.01*(2*stat["base_stat"]+31)*50+50+10) for stat in data["stats"]} #You will have to excuse those 5 points
    abilities=[a["ability"]["name"] for a in data["abilities"]]
    id=data["id"]
    
    move_objs=[] 
    _PROTECT_NAMES = {
    "protect", "detect", "spiky-shield", "king-s-shield",
    "baneful-bunker", "silk-trap", "obstruct"}
    move_names=MOVESETS.get(str(id))
    if not move_names:
        move_names=[m["move"]["name"] for m in data["moves"][:4]]
    
    
    #move_names=[m["move"]["name"] for m in data["moves"][:4]] I started with the first 4, now we implement the NAIC moveset



    for move in move_names:
        url=f"https://pokeapi.co/api/v2/move/{move}"
        r=SESSION.get(url,timeout=15)
        mjson=r.json()
        move_objs.append(
            Move(
                name=mjson["name"],
                move_type=mjson["type"]["name"],
                power=mjson.get("power") or 0,
                accuracy=mjson.get("accuracy"),                 # None = always hits
                category=mjson["damage_class"]["name"],
                priority=mjson.get("priority", 0),
                is_protect=mjson["name"] in {
                    "protect","detect","spiky-shield","kings-shield",
                    "baneful-bunker","silk-trap","obstruct"
                },
                is_spread=mjson.get("target", {}).get("name") in {"all-opponents","all-other-pokemon"},
            )
        )
    return Pokemon(name,types,stats,abilities,move_objs,id)
