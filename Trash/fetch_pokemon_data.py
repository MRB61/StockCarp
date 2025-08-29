import requests
import json
import os

def fetch_pokemon_data(pokemon_id,save_dir="data/raw/"):
    url=f"https://pokeapi.co/api/v2/pokemon/{pokemon_id}"
    print(f"Fetching data for {pokemon_id} from {url}")
    response=requests.get(url)
    if response.status_code==200:
        data=response.json()
        save_path=os.path.join(save_dir,f"{pokemon_id}.json")
        with open(save_path, "w") as f:
            json.dump(data,f,indent=2)
    else:
        print(f"Failed to download")
    
if __name__ == "__main__":
    #pokemon_list=["chien-pao", "flutter-mane","incineroar","miraidon","calyrex-shadow","zamazenta-crowned","urshifu-rapid-strike","calyrex-ice","rillaboom","raging-bolt","whimsicott","amoonguss","grimmsnarl","kyogre","volcarona","smeargle","landorus","tornadus","farigiraf","lunala","groudon","chi-yu","sneasler","koraidon","ogerpon-cornerstone","indeedee-f","iron-hands","ursaluna","terapagos","roaring-moon","zacian-crowned","walking-wake","ting-lu","torkoal"]
    pokemon_list=[]
    with open("data/clean/movesets_regI.json", "r", encoding="utf-8") as f:
        datusco=json.load(f)
    for id in datusco:
        pokemon_list.append(id)

    for name in pokemon_list:
        fetch_pokemon_data(name)