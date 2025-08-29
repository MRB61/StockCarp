
class BattlePokemon: #Class where data will be changig through battle
    def __init__(self,pokemon):
        self.pokemon=pokemon
        self.current_hp=pokemon.base_stats["hp"]
        self.status=None
        self.stat_stages={"attack": 0, "defense": 0, "special-attack": 0,
            "special-defense": 0, "speed": 0, "accuracy": 0, "evasion": 0
        }
        self.vol = {
            "protected": False,
            "protect_streak": 0,          # for consecutive Protect
            "used_protect_this_turn": False,
        }
        self.item=None
        self.ability=None
        self.turns_on_field=None
        self.turns_played=None
    def take_damage(self, dmg):
        self.current_hp=max(0,self.current_hp-dmg)
    def is_fainted(self):
        return self.current_hp<=0
    
    def __repr__(self):
        return f"Battle {self.pokemon.name.title()} HP:{self.current_hp}"
    
    