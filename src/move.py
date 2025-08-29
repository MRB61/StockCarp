class Move: #Class for moves
    def __init__(self,name,move_type,power,accuracy,category,priority=0,is_protect=False, is_spread=False):
        self.name=name
        self.type=move_type
        self.power=power
        self.accuracy=accuracy
        self.category=category
        self.priority=priority
        self.is_protect=is_protect
        self.is_spread=is_spread

    def __repr__(self):
        return f"{self.name} ({self.type}, {self.category}) Pwr:{self.power} Acc:{self.accuracy}"