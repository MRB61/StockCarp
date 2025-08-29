import pickle
from src.battle_pokemon import BattlePokemon
def team_selection(id_ordered):
    with open("data/clean/pokemon_objects.pkl", "rb") as f:
        pokemon_list=pickle.load(f)
    
    active=[BattlePokemon(x) for x in pokemon_list if x.id==id_ordered[0] or x.id==id_ordered[1]]
    bench=[BattlePokemon(x) for x in pokemon_list if x.id==id_ordered[2] or x.id==id_ordered[3]]
    if not active or not bench:
        print("Currently we do not have a pokemon you asked for")
    return active, bench
