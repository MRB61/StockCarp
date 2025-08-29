import json,re ,sys, pathlib

def slug_move(name:str)->str:
    s=name.strip().lower()
    s=re.sub(r"[^a-z0-9]+", "-",s).strip("-")
    return re.sub(r"-{-2,}","-",s)
def main(in_path:str,out_path:str):
    data=json.loads(pathlib.Path(in_path).read_text(encoding="utf-8"))
    by_id={}
    for player in data:
        for mon in player.get("decklist",[]):
            sid=str(mon["id"])
            if sid in by_id:
                continue
            moves=mon.get("badges",[])[:4]
            by_id[sid]=[slug_move(m) for m in moves]
    pathlib.Path(out_path).parent.mkdir(parents=True,exist_ok=True)
    pathlib.Path(out_path).write_text(json.dumps(by_id,indent=2),encoding="utf-8")
    print (f"Wrote {out_path} with {len(by_id)} species.")
if __name__=="__main__":
    if len(sys.argv)!=3:
        print("Usage: python pokemon_movesets")
        sys.exit(1)
    main(sys.argv[1],sys.argv[2])
