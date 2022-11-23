from enum import Enum
class TimeCloseEnum(Enum):
	EARLY = 0
	READY = 1
	RIGHT = 2
	def __str__(self):
		return self.name