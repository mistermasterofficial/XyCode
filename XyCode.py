class Argument:
    STRING_TYPE = "string"
    NUM_TYPE = "num"
    NAME_TYPE = "name"

    def __init__(self, content, is_string):
        self.content = content
        self.type = self.STRING_TYPE if is_string else None

        if self.type != self.STRING_TYPE:
            match self.content[:2].lower():
                case "0b":
                    self.content = int(self.content[2:], base=2)
                    self.type = self.NUM_TYPE
                case "0o":
                    self.content = int(self.content[2:], base=8)
                    self.type = self.NUM_TYPE
                case "0x":
                    self.content = int(self.content[2:], base=16)
                    self.type = self.NUM_TYPE
            try:
                self.content = int(self.content)
                self.type = self.NUM_TYPE
            except Exception:
                pass

            if self.type != self.NUM_TYPE:
                self.type = self.NAME_TYPE
        elif len(self.content)==1:
            self.content = ord(self.content)
            self.type = self.NUM_TYPE

    def get_length(self):
        l = 1
        if self.type == self.STRING_TYPE:
            l += len(self.content)
        return l

class Instruction:
    def __init__(self, name, *args):
        self.name = name.lower()
        self.args = args
        if type(args) is tuple:
            self.args = [a for a in self.args]

    def get_length(self):
        return 1+sum([a.get_length() for a in self.args])

class XyCodeLexer:
    universal_separator = "043273fc-54dc-49ef-9ecc-bf231883a8a7-"
    separator_substitute = "b60d154b-f47e-4cbe-acde-8b7f4534bd68-"

    @classmethod
    def compile(cls, path):
        instructions = []

        code = ""
        with open(path, "r") as f:
            code = f.read()

        code = code.replace("\n","").replace("\r","").replace("\t"," ")
        
        code = code.replace("\\;", cls.separator_substitute)

        code = code.split(";")

        for c in range(len(code)):
            instruction = []
            code[c] = code[c].replace(cls.separator_substitute, ";")+" "
            while " " in code[c]:
                if code[c][0]=='"':
                    count = 0
                    content = ""
                    is_unicode = False
                    while code[c][count+1]!='"' or is_unicode:
                        if code[c][count+1]=="\\":
                            is_unicode = not is_unicode
                        else: 
                            is_unicode = False

                        if not is_unicode:
                            content += code[c][count+1]
                        count+=1
                    instruction.append(Argument(content, True))
                    code[c] = code[c][count+2:]
                else:
                    code[c] = code[c].replace(" ",cls.universal_separator,1).split(cls.universal_separator)
                    if len(code[c][0])>0 and len(instruction)==0: instruction.append(code[c][0])
                    elif len(code[c][0])>0: instruction.append(Argument(code[c][0], False))
                    code[c] = code[c][1]
            if len(instruction)>0:
                instructions.append(Instruction(instruction[0],*instruction[1:]))
            else:
                instructions.append(Instruction(code[c]))

        count = 0
        while count<len(instructions):
            if instructions[count].name == "" or "//" in instructions[count].name:
                instructions.pop(count)
            else:
                count+=1

        return instructions

class XyCodeParser:
    used_paths = []
    operations = ["mnl","push","pop","add","sub","mul","div","inc","dec","and","or","xor","not","lshift","rshist","irshift","neg","more","less","equals","jmp","if","malloc","free","toheap","fromheap","func","return","try","endtry","syscall","revflag","reverse","call","double","throw","status","mnlarr","bool"
    ]
    stdlib_path = "\\".join(__file__.split("\\")[:-1])+"\\stdlib"

    @classmethod
    def include(cls, instructions, dirpath=""):
        instr = instructions
        count = 0
        while count<len(instr):
            if instr[count].name == "include":
                _path = instr[count].args[0].content.replace("/","\\")+".xy"
                _path = _path.replace("STDLIB",cls.stdlib_path)
                if dirpath!="":
                    _path = dirpath+"\\"+_path
                if not _path in cls.used_paths:
                    cls.used_paths.append(_path)
                    _dirpath = "\\".join(_path.split("\\")[:-1])
                    instr = instr[:count] + XyCodeParser.include(XyCodeLexer.compile(_path), _dirpath) + instr[count+1:]
                else:
                    instr.pop(count)
            else:
                count+=1
        return instr

    @classmethod
    def template(cls, instructions):
        instr = instructions
        count = 0

        templates = dict()
        for c in range(len(instr)):
            if instructions[c].name == "tmpl":
                templates[instructions[c].args[0].content] = c 

        while count<len(instr):
            if instr[count].name == ".":
                tmpl = []
                from_args = [a.content for a in instructions[templates[instr[count].args[0].content]].args[1:]]
                to_args = [a.content for a in instr[count].args[1:]]
                t = 0
                while instructions[templates[instr[count].args[0].content]+t+1].name!="endtmpl":
                    t+=1
                    tmpl.append(instructions[templates[instr[count].args[0].content]+t])
                    for a in range(len(tmpl[-1].args)):
                        if tmpl[-1].args[a].type == Argument.NAME_TYPE and tmpl[-1].args[a].content in from_args:
                            tmpl[-1].args[a].content = to_args[from_args.index(tmpl[-1].args[a].content)]
                instr = instr[:count] + tmpl + instr[count+1:]
            elif instr[count].name == "tmpl":
                while instr[count].name!="endtmpl":
                    count+=1
                count+=1
            else:
                count+=1

        count = 0
        while count<len(instr):
            if instr[count].name == "tmpl":
                while instr[count].name!="endtmpl":
                    instr.pop(count)
                instr.pop(count)
            else:
                count+=1
        
        return instr

    @classmethod
    def condition(cls, instructions):
        instr = instructions
        count = 0

        conditions = []
        while_loops = []
        do_while_loops = []

        while count<len(instr):
            if instr[count].name == "if":
                conditions.append(count)
            elif instr[count].name == "endif":
                instr[conditions[-1]].args = [Argument(str(count), False)]
                instr.pop(count)
                count-=1
                conditions.pop()

            elif instr[count].name == "while":
                while_loops.append(count)
                instr[count].name = "if"
            elif instr[count].name == "endwhile":
                instr[while_loops[-1]].args = [Argument(str(count+1), False)]
                instr[count] = Instruction("jmp", Argument(str(while_loops[-1]), False))
                count-=1
                while_loops.pop()

            elif instr[count].name == "do":
                do_while_loops.append(count)
                instr.pop(count)
                count-=1
            elif instr[count].name == "dowhile":
                instr[count].name = "if"
                instr[count].args = [Argument(str(count+2), False)]
                instr = instr[:count+1] + [Instruction("jmp",Argument(str(do_while_loops[-1]), False))] + instr[count+1:]
                do_while_loops.pop()

            count+=1

        return instr


    @classmethod
    def function(cls, instructions):
        instr = instructions
        count = 0

        functions = dict()
        functions_name = []
        functions_varnames = []
        cur_func = ""
        for c in range(len(instr)):
            if instructions[c].name == "func":
                cur_func = instructions[c].args[0].content
                functions[cur_func] = c
                functions_varnames.append([i.content for i in instructions[c].args[1:]])
                instr[c] = Instruction("func", Argument(str(len(functions_name)),False),
                    Argument(str(len(instructions[c].args)-1),False),
                    Argument("0",False))
                functions_name.append(cur_func)
            elif instructions[c].name == "var":
                for a in instructions[c].args:
                    if a.content not in functions_varnames[-1]:
                        functions_varnames[-1].append(a.content)
                instr[functions[cur_func]].args[1].content += len(instructions[c].args)
            elif instructions[c].name == "endfunc":
                instr[functions[cur_func]].args[2].content = c-functions[cur_func]
                instr[c].name = "return"
                cur_func = ""
        
        while count<len(instr):
            if instr[count].name == "var":
                instr.pop(count)
            else:
                count+=1

        for i in range(len(instr)):
            if instr[i].name == "call":
                instr[i].args[0] = Argument(str(functions_name.index(instr[i].args[0].content)),False)

        cur_func_num = 0
        for c in range(len(instr)):
            if instr[c].name == "func":
                cur_func_num = instr[c].args[0].content
                continue

            for a in range(len(instr[c].args)):
                if instr[c].args[a].type == Argument.NAME_TYPE:
                    instr[c].args[a].type = Argument.NUM_TYPE
                    instr[c].args[a].content = functions_varnames[cur_func_num].index(instr[c].args[a].content)

        return instr

    @classmethod
    def parse(cls, instructions):
        instr = instructions
        instr = cls.include(instr)
        instr = cls.template(instr)
        instr = cls.function(instr)
        instr = cls.condition(instr)

        lengths = [i.get_length() for i in instr]

        for i in range(len(instr)):
            if instr[i].name in ["jmp","if"]:
                if len(lengths[:instr[i].args[0].content])>0:
                    instr[i].args[0].content = sum(lengths[:instr[i].args[0].content])
                else:
                    instr[i].args[0].content = 1
            elif instr[i].name == "func":
                instr[i].args[2].content = sum(lengths[i+1:i+1+instr[i].args[2].content])
            elif instr[i].name == "mnlarr" and instr[i].args[0].type == Argument.NUM_TYPE and len(instr[i].args)==1:
                instr[i].name = "mnl"

        for i in range(len(instr)):
            print(sum(lengths[:i]), recursive_vars(instr)[i])

        int_codes = []
        for i in range(len(instr)):
            int_codes.append(cls.operations.index(instr[i].name))
            for a in range(len(instr[i].args)):
                if instr[i].args[a].type == Argument.NUM_TYPE:
                    int_codes.append(instr[i].args[a].content)
                elif instr[i].args[a].type == Argument.STRING_TYPE:
                    int_codes.append(len(instr[i].args[a].content))
                    for c in instr[i].args[a].content:
                        int_codes.append(ord(c))

        return int_codes

def recursive_vars(obj):
    # Если это базовый тип (число, строка, bool, None), возвращаем как есть
    if isinstance(obj, (int, float, str, bool, type(None))):
        return obj
    
    # Если это список, кортеж или множество, обрабатываем каждый элемент
    if isinstance(obj, (list, tuple, set)):
        return type(obj)(recursive_vars(item) for item in obj)
    
    # Если это словарь, рекурсивно обрабатываем ключи и значения
    if isinstance(obj, dict):
        return {k: recursive_vars(v) for k, v in obj.items()}
    
    # Если у объекта есть атрибут __dict__ (кастомные классы)
    if hasattr(obj, '__dict__'):
        return {k: recursive_vars(v) for k, v in vars(obj).items()}
    
    # Для всех остальных типов (например, функции или системные объекты)
    return obj

if __name__=="__main__":
    import sys

    source = sys.argv[1]
    dest = sys.argv[2]

    instr = XyCodeLexer.compile(source)
    int_codes = XyCodeParser.parse(instr)

    with open(dest, "wb") as f:
        for i in int_codes:
            f.write(i.to_bytes(4,sys.byteorder)[::-1])
