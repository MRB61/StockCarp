class Pokemon:
    def __init__(self, name,types, stats,abilities, moves,id):
        self.name=name
        self.types=types
        self.base_stats=stats
        self.abilities=abilities
        self.moves=moves 
        self.id=id
    def __repr__(self):
        return f"{self.name.title()} (ID:{self.id})"
        