import random
import numpy as np
import src.battle_pokemon
from src.damage_calc import damage_calc
def turn_order(battle_pokemon1,battle_pokemon2):
    if battle_pokemon1.pokemon.base_stats["speed"]>battle_pokemon2.pokemon.base_stats["speed"]:
        turn=0
    elif battle_pokemon1.pokemon.base_stats["speed"]==battle_pokemon2.pokemon.base_stats["speed"]:
        turn=round(random.uniform(0,1))
    else:turn=1
    return turn
def select_move(battle_pokemon1):
    powers=[]
    for move in battle_pokemon1.pokemon.moves:
        powers.append(move.power)
    powers=[0 if x is None else x for x in powers]
    index=np.argmax(powers)
    move=battle_pokemon1.pokemon.moves[index]
    return move
        

def start(team1,team2):
    battle_pokemon1=team1#For now just select the first
    battle_pokemon2=team2

    turn_counter=0
    while battle_pokemon1.current_hp>0 and battle_pokemon2.current_hp>0:
        turn=turn_order(battle_pokemon1,battle_pokemon2)
        if turn==0:
            move=select_move(battle_pokemon1)
            dmg=damage_calc(battle_pokemon1,battle_pokemon2,move)
            battle_pokemon2.take_damage(dmg)
            print(f"Pokemon {battle_pokemon2.pokemon.name} took {dmg}, current HP is {battle_pokemon2.current_hp}")
            if battle_pokemon2.is_fainted():
                print(f"{battle_pokemon1} Wins")
                break #I would like to stop the code here
            else:
                move=select_move(battle_pokemon2)
                dmg=damage_calc(battle_pokemon2,battle_pokemon1,move)
                battle_pokemon1.take_damage(dmg)
                print(f"Pokemon {battle_pokemon1.pokemon.name} took {dmg}, current HP is {battle_pokemon1.current_hp}")
                if battle_pokemon1.is_fainted():
                    print(f"{battle_pokemon2} Wins")
                    break
                else:
                    turn_counter+=1
        else:
            move=select_move(battle_pokemon2)
            dmg=damage_calc(battle_pokemon2,battle_pokemon1,move)
            battle_pokemon1.take_damage(dmg)
            print(f"Pokemon {battle_pokemon1.pokemon.name} took {dmg}, current HP is {battle_pokemon1.current_hp}")
            if battle_pokemon1.is_fainted():
                print(f"{battle_pokemon2} Wins")
                break
            else:
                move=select_move(battle_pokemon1)
                dmg=damage_calc(battle_pokemon1,battle_pokemon2,move)
                battle_pokemon2.take_damage(dmg)
                print(f"Pokemon {battle_pokemon2.pokemon.name} took {dmg}, current HP is {battle_pokemon2.current_hp}")
                if battle_pokemon2.is_fainted():
                    print(f"{battle_pokemon1} Wins")
                    break
                else:
                    turn_counter+=1
    return "Battle have finished"


            




    