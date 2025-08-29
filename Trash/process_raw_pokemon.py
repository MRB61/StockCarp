import os
import pickle
import json
from clean_pokemon_data import clean_info
pokemon_objects=[]
pokemon_json=[]
for filename in os.listdir("data/raw"):
    if filename.endswith(".json"):
        with open(os.path.join("data/raw", filename), encoding="utf-8") as f:
            raw_data=json.load(f)
        pokemon=clean_info(raw_data)
        pokemon_objects.append(pokemon)

        pokemon_json.append({"name": pokemon.name,
            "types": pokemon.types,
            "base_stats": pokemon.base_stats,
            "abilities": pokemon.abilities,
            "moves": [vars(m) for m in pokemon.moves],
            "id": pokemon.id
        })
with open(os.path.join("data/clean","pokemon_objects.pkl"),"wb") as f:
    pickle.dump(pokemon_objects,f)
print(f"Saved {len(pokemon_objects)} Pokemon.")
with open(os.path.join("data/clean","pokemon_json"),"w",encoding="utf-8") as f:
    json.dump(pokemon_json,f, indent=2)
print(f"Saved {len(pokemon_json)} Pokemon")

