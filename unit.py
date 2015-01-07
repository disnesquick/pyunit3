import re
def combineDimensionLists(firstList, secondList, mul):
	""" This function combines two dimensional lists into one, ensuring
	    that there are no duplicate units in the list.
	"""
	newList = []
	iterSelf = iter(firstList)
	iterOther = iter(secondList)

	tickS = tickO = False
	try:
		curSType, curSExp = next(iterSelf)
		tickS = True
		curOType, curOExp = next(iterOther)
		tickO = True
		while True:
			if curSType.index > curOType.index:
				newList.append((curSType, curSExp))
				tickS = False
				curSType, curSExp = next(iterSelf)
				tickS = True
			elif curSType.index < curOType.index:
				newList.append((curOType, mul*curOExp))
				tickO = False
				curOType, curOExp = next(iterOther)
				tickO = True
			else:
				newExp = curSExp + mul*curOExp
				if newExp != 0:
					newList.append((curSType, newExp))
				tickS = tickO = False
				curOType, curOExp = next(iterOther)
				tickO = True
				curSType, curSExp = next(iterSelf)
				tickS = True
	except StopIteration:
		pass
	if tickS:
		newList.append((curSType, curSExp))
	if tickO:
		newList.append((curOType, mul*curOExp))

	for curSType, curSExp in iterSelf:
		newList.append((curSType, curSExp))
	for curOType, curOExp in iterOther:
		newList.append((curOType, mul*curOExp))
	return newList

def factorReduction(first, second):
	""" This function takes two integer arguments which are assumed to be
	    involved in a fraction, in some unspecified order, and, by factoring
	    finds the minimal representation of this fraction through these
	    two integers.
	"""
	#Cannot factor not integers
	if isinstance(first, float) or isinstance(second, float):
		return first, second
	def gcd(a,b):
		while b: a, b = b, a%b
		return a
	div = gcd(first, second)
	while div != 1:
		first //= div
		second //= div
		div = gcd(first, second)
	return first, second



class MetaUnits(type):
	""" This is the meta-class for the units type and will handle most of
	    the unit conversion. This allows united variables to be used in
	    a pythonic way. i.e. the units of the variable form its type rather
	    than the units being contained inside the object itself.
	"""
	# count is used to apply a unique index to each unit-type created
	count = 0
	# table to keep track of all units created
	tableOfUnits = {}

	def __init__(cls, name, bases, nameSpace):
		""" Initialize the name, create a new index for dimension-list
		    ordering and set-up a fresh dimension list if there isn't
		    supplied.
		"""
		mcls = type(cls)
		cls.index = type(cls).count
		mcls.count += 1
		if not "dimList" in nameSpace:
			cls.dimList = [(cls, 1)]

	def doMulDiv(cls, other, sign):
		if isinstance(other, MetaUnits):
			if sign > 0:
				botC, topC = cls.bottomConstant, cls.topConstant * other.topConstant**sign
			elif sign < 0:
				topC, botC = cls.topConstant, cls.bottomConstant * other.bottomConstant**(-sign)
			else:
				topC, botC = cls.topConstant, cls.bottomConstant
			order = cls.order + other.order*sign
			newList = combineDimensionLists(cls.dimList, other.dimList, sign)
			rType = float if newList == [] else MetaUnits("UnNamed", (Units,), {"dimList": newList, "topConstant":topC , "bottomConstant":botC, "order":order})
			return rType

		# Multiplication/division by a constant number, useful for creating a derived unit-type, which is a
		# set number of the parent type (e.g. Minutes = 60 * Seconds)
		elif isinstance(other, (float, int)):
			orderMod = 0
			while other % 10 == 0:
				other //= 10
				orderMod += 1
			
			# Depending on whether a multiply or a div was specified use a top or bottom heavy
			# fraction
			if sign >= 0:
				topC, botC = other**sign, 1
			else:
				topC, botC = 1, other**(-sign)

			if cls.symbol:
				# If the parent units has a symbol, then it is a registered type and the derived type
				# should specify its construction in terms of that type
				return MetaUnits("UnNamed", (Units,), {"dimList": [(cls,1)], "topConstant":topC , "bottomConstant":botC, "order":orderMod*sign})
			else:
				# Otherwise the derived type should specify itself in terms of the parents' types
				return MetaUnits("UnNamed", (Units,), {
				  "dimList": cls.dimList, "topConstant":cls.topConstant * topC,
				  "bottomConstant": cls.bottomConstant * botC, "order":cls.order+orderMod*sign})
		else:
			return cls


	def __mul__(cls, other):
		return cls.doMulDiv(other, 1)

	def __rmul__(cls, other):
		return cls * other
	
	def __truediv__(cls, other):
		return cls.doMulDiv(other, -1)
	
	def __pow__(cls, exponent):
		if isinstance(exponent, Units):
			raise(DimensionException("Cannot raise a Units object to a Units power"))
		if cls.symbol:
			return MetaUnits("UnNamed", (Units,), {"dimList": [(cls,exponent)]})
		else:	
			newList = []
			for t,e in cls.dimList:
				newList.append((t,e*exponent))
			return MetaUnits("UnNamed", (Units,),{ "dimList": newList, "topConstant":cls.topConstant**exponent, "bottomConstant":cls.bottomConstant**exponent, "order":cls.order*exponent})

	def __repr__(cls):
		if cls.symbol:
			return cls.basicRepresentation()
		constant = cls.topConstant / cls.bottomConstant
		if constant != 1:
			build = "%f"%constant
		elif cls.order != 0:
			build = "1"
		if cls.order != 0:
			build = build + "x10^%d"%cls.order
		if cls.order !=0 or constant!=1:
			build = "(%s)"%build
		else:
			build = ""
		return build + cls.basicRepresentation()

	def basicRepresentation(cls):
		if cls.symbol:
			return cls.symbol
		else:
			top = [repr(t) + ("%s"%e if e > 0 and e!=1 else " ") for t,e in cls.dimList if e > 0]
			bottom = [repr(t) + ("%s"%(-e) if e < 0 and e!=-1 else " " )for t,e in cls.dimList if e < 0]
			
			if top != [] and bottom != []:
				return "".join(top).strip()+"/"+"".join(bottom).strip()
			elif top != []:
				return "".join(top).strip()
			elif bottom != []:
				bottom = [t.symbol + "%s"%e for t,e in cls.dimList]
				return "".join(bottom)
			else:
				return ""

	def name(cls, symbol, fullName = None):
		cls.symbol = symbol
		if fullName:
			cls.__name__ = fullName
		cls.registerName()
		cls.register()
		return cls
	
	def registerName(cls):
		""" Method to register the unit-type by its symbol so that string
		    conversion can be used to extract unit objects from symbolic
		    suffices.
		""" 
		symbol = cls.symbol
		mcls = type(cls)
		if symbol in mcls.tableOfUnits:
			raise(Exception("Symbol conflict neonate: (%s - %s) with veteran: (%s - %s)"%(symbol, cls.__name__, symbol, mcls.tableOfUnits[symbol].__name__)))
		mcls.tableOfUnits[symbol] = cls


	def register(cls):
		topC = cls.topConstant
		botC = cls.bottomConstant
		order = cls.order
		conversionList = [(i,j) for i,j in cls.dimList]
		flag = True
		while flag == True:
			j = 0
			flag = False
			for tp, ex in conversionList:
				if tp.conversionList:
					conversionList = combineDimensionLists(conversionList[:j] + conversionList[j+1:], tp.conversionList, ex)
					if ex > 0:
						topC *= tp.conversionConstantTop**ex
						botC *= tp.conversionConstantBottom**ex
					elif ex < 0:
						botC *= tp.conversionConstantTop**(-ex)
						topC *= tp.conversionConstantBottom**(-ex)
					order += tp.conversionOrder*ex
					flag = True
					break
				j = j + 1
		if not isinstance(topC, int) or not isinstance(botC, int):
			raise(TypeError("Attempt to register a non-integral conversion"))
		cls.conversionList = conversionList
		topC, botC = factorReduction(topC, botC)
		cls.conversionConstantTop = topC
		cls.conversionConstantBottom = botC
		cls.conversionOrder = order
		cls.order = 0
		cls.topConstant = 1
		cls.bottomConstant = 1
		cls.dimList = [(cls, 1)]
		return cls

	def deriveOOM(cls, order):
		if cls.symbol:
			return MetaUnits("UnNamed", (Units,), {"dimList": [(cls,1)], "order":order})
		else:	
			return MetaUnits("UnNamed", (Units,), {"dimList": cls.dimList, "order":cls.order+order})

	def typeConversionConstant(cls, otherType):
		if isinstance(otherType, MetaUnits):
			topC = cls.topConstant * otherType.bottomConstant
			botC = cls.bottomConstant * otherType.topConstant
			order = cls.order - otherType.order
			conversionList = combineDimensionLists(cls.dimList, otherType.dimList, -1)
		elif issubclass(otherType, float):
			topC = cls.topConstant
			botC = cls.bottomConstant
			order = cls.order
			conversionList = cls.dimList

		while conversionList > []:
			tp, ex = conversionList[0]
			if tp.conversionList:
				conversionList = combineDimensionLists(conversionList[1:], tp.conversionList, ex)
				if ex > 0:
					topC *= tp.conversionConstantTop**ex
					botC *= tp.conversionConstantBottom**ex
				elif ex < 0:
					botC *= tp.conversionConstantTop**(-ex)
					topC *= tp.conversionConstantBottom**(-ex)
				order += tp.conversionOrder*ex
			else:
				raise(TypeError("Cannot convert %s into %s"%(cls, otherType)))
		topC, botC = factorReduction(topC, botC)
		return topC, botC, order

class Units(float, metaclass = MetaUnits):
	topConstant = 1
	bottomConstant = 1
	conversionList = None
	order = 0
	symbol = None
	def __pow__(self, exponent):
		return (type(self)**exponent)(super().__pow__(exponent))

	def __mul__(self, other):
		return (type(self)*type(other))(super().__mul__(other))

	def __rmul__(self, other):
		return self.__mul__(other)

	def __truediv__(self, other):
		return (type(self)/type(other))(super().__truediv__(other))

	def __rtruediv__(self, other):
		return ((~type(self))*type(other))(super().__rtruediv__(other))

	def __add__(self, other):
		return type(self)(super().__add__(self.checkConvert(other)))

	def __sub__(self, other):
		return type(self)(super().__sub__(self.checkConvert(other)))

	def __eq__(self, other):
		return super().__eq__(self.checkConvert(other))

	def __gt__(self, other):
		return super().__gt__(self.checkConvert(other))

	def __lt__(self, other):
		return super().__lt__(self.checkConvert(other))

	def __gte__(self, other):
		return super().__gte__(self.checkConvert(other))

	def __lte__(self, other):
		return super().__lte__(self.checkConvert(other))

	def checkConvert(self, other):
		if type(self) != type(other):
			topConstant, bottomConstant, order = type(other).typeConversionConstant(type(self))
			value = float(other) * topConstant * 10**order / bottomConstant
			return value
		else:
			return other

	def to(self, otherType):
		topC, botC, order = type(self).typeConversionConstant(otherType)
		value = float(self) * topC
		value /= botC
		value *= 10**order
		return otherType(value)

	def simplify(self):
		cls = type(self)
		raise(Exception("TODO: This function will reduce all non-symbolic units (i.e. unnamed derived types in the dimension list)"))
	
	def __str__(self):
		if "symbol" in type(self).__dict__:
			val = float(self)
		else:
			val = float(self) * self.topConstant / self.bottomConstant * 10**self.order
		typeRepr = type(self).basicRepresentation()
		return repr(val) + "["+ typeRepr+"]"

	def __repr__(self):
		return str(self)

unitsFromStringPattern=re.compile("[^ 0-9]+(?:[0-9]+| )")
def unitsFromString(string):
	try:
		top,bottom = string.split("/")
	except ValueError:
		top,bottom = string, ""
	top = top+" "
	bottom = bottom+" "
	unitsTop = unitsFromStringPattern.findall(top)
	unitsBottom = unitsFromStringPattern.findall(top)


def buildPrefixed(symbol, name = None):
	""" Helper function to create the basic unit types. Will either take
	    a single Units class (i.e. a MetaUnits object) or two strings.
	"""

	#Helper function to create a single prefixed symbol
	fullPrefixTable = "Yotta","Zetta","Exa","Peta","Tera","Giga","Mega","Kilo","Hecto","Deca","Deci","Centi","Milli","Micro","Nano","Pico","Femto","Atto","Zepto","Yocto"
	prefixTable = "Y","Z","E","P","T","G","M","k","h","da","d","c","m","u","n","p","f","a","z","y"
	def makeOnePrefixed(nameIdx, cls, mul):
		name = fullPrefixTable[nameIdx]
		symbol = prefixTable[nameIdx] + cls.symbol
		newName = name + cls.__name__.lower()
		globals()[newName] = cls.deriveOOM(mul).name(symbol, newName)

	if isinstance(symbol, MetaUnits) and name is None:
		cls = symbol
	elif isinstance(symbol, str) and isinstance(name, str):
		cls = MetaUnits(name, (Units,), {"symbol" : symbol})
	else:
		raise(SyntaxError("buildPrefixed must either be supplied with a single Units class or two strings (symbol and name)"))
	multiplier = 24
	j = 0
	while multiplier > 3:
		makeOnePrefixed(j, cls, multiplier)
		j+= 1
		multiplier -=3
	while multiplier >= 1:
		makeOnePrefixed(j, cls, multiplier)
		j+= 1
		multiplier -=1	
	multiplier += 1
	while multiplier < 3:
		makeOnePrefixed(j, cls, -multiplier)
		j+= 1
		multiplier += 1
	while multiplier <= 24:
		makeOnePrefixed(j, cls, -multiplier)
		j+= 1
		multiplier += 3
	return cls

class Radians(Units):
	symbol = "rad"

Grams = buildPrefixed("g","Grams")
Metres = buildPrefixed("m","Metres")
Coulombs = buildPrefixed("C","Coulombs")
Seconds = buildPrefixed("s","Seconds")
Moles = buildPrefixed("mol","Moles")
Kelvins = buildPrefixed("K","Kelvins")

#Derived time units
Minutes = (Seconds*60).name("min","Minutes")
Hours = (Minutes*60).name("h","Hours")
Days = (Hours*24).name("d","Days")

#Imperial Mass
Pounds = (453592370 * Nanograms).name("lb","Pounds")
Ounces = (Pounds / 16).name("oz","Ounces")

#Imperial Length
Feet = (304800 * Micrometres).name("'","Feet")
Yards = (3 * Feet).name("yds","Yards")
Inches = (Feet / 12).name("\"","Inches")
Mils = (Inches.deriveOOM(-3)).name("mil","Mils")
Chains = (22 * Yards).name("ch","Chains")
Furlongs = (10 * Chains).name("fur","Furlongs")
Miles = (8 * Furlongs).name("mi","Miles")
Leagues = (3 * Miles).name("lea","Leagues")

#Imperial Area
Acres = (Furlongs * Chains).name("ac","Acres")

#Imperial Temperature
Rankines = (5 * Kelvins / 9).name("R", "Rankines")

#SI Derived units
Hectares = (Hectometres * Hectometres).name("ha","Hectares")
Hertz = buildPrefixed((Seconds**-1).name("Hz","Hertz"))
Newtons = buildPrefixed((Kilograms * Metres / Seconds**2).name("N","Newtons"))
Pascals = buildPrefixed((Newtons / Metres**2).name("Pa","Pascals"))
Joules = buildPrefixed((Newtons * Metres).name("J","Joules"))
Watts = buildPrefixed((Joules / Seconds).name("W","Watts"))
Amperes = buildPrefixed((Coulombs/Seconds).name("A","Amperes"))
Volts = buildPrefixed((Joules / Coulombs).name("V","Volts"))
Farads = buildPrefixed((Coulombs / Volts).name("F","Farads"))
Ohms = buildPrefixed((Volts / Amperes).name("ohm", "Ohms"))
Siemens = buildPrefixed((Ohms**-1).name("S","Siemens"))
Webers = buildPrefixed((Joules / Amperes).name("Wb","Webers"))
Teslas = buildPrefixed((Webers / Metres**2).name("T","Teslas"))
Henries = buildPrefixed((Ohms * Seconds).name("H","Henries"))


if __name__ == "__main__":
	a = Minutes(1) / 30
	print("Testing basic units")
	print(a)
	print(type(a).__name__)

	print("\nTesting derived units")
	b = Minutes / 30
	c = b(1)
	print(c)
	print(type(c))
	print(type(c).__name__)
	d = c.to(Seconds)
	print(d)
	print(type(d).__name__)
	print(str(c**2))
