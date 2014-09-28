"""
Helper functions for reading and writing hardware files.

Each of the functions in inputoutput take a block and a file descriptor.
The functions provided either read the file and update the Block
accordingly, or write information from the Block out to the file.
"""

import sys
import re
import collections
import pyparsing

import core
import wire
import helperfuncs


#-----------------------------------------------------------------
#            __       ___
#    | |\ | |__) |  |  |
#    | | \| |    \__/  |


def input_from_blif(blif, block=None, merge_io_vectors=True):
    """ Read an open blif file or string as input, updating the block appropriately

    Assumes the blif has been flattened and their is only a single module.
    Assumes that there is only one single shared clock and reset
    Assumes that output is generated by Yosys with formals in a particular order
    Ignores reset signal (which it assumes is input only to the flip flops)
    """

    from pyparsing import Word, Literal, infixNotation, OneOrMore, ZeroOrMore
    from pyparsing import oneOf, Suppress, Group, Optional, Keyword

    block = core.working_block(block)

    if isinstance(blif, file):
        blif_string = blif.read()
    elif isinstance(blif, basestring):
        blif_string = blif
    else:
        raise core.PyrtlError('input_blif expecting either open file or string')

    def SKeyword(x):
        return Suppress(Keyword(x))

    def SLiteral(x):
        return Suppress(Literal(x))

    def twire(x):
        """ find or make wire named x and return it """
        s = block.get_wirevector_by_name(x)
        if s is None:
            s = wire.WireVector(bitwidth=1, name=x)
        return s

    # Begin BLIF language definition
    signal_start = pyparsing.alphas + '$:[]_<>\\\/'
    signal_middle = pyparsing.alphas + pyparsing.nums + '$:[]_<>\\\/.'
    signal_id = Word(signal_start, signal_middle)
    header = SKeyword('.model') + signal_id('model_name')
    input_list = Group(SKeyword('.inputs') + OneOrMore(signal_id))('input_list')
    output_list = Group(SKeyword('.outputs') + OneOrMore(signal_id))('output_list')

    cover_atom = Word('01-')
    cover_list = Group(ZeroOrMore(cover_atom))('cover_list')
    namesignal_list = Group(OneOrMore(signal_id))('namesignal_list')
    name_def = Group(SKeyword('.names') + namesignal_list + cover_list)('name_def')

    # asynchronous Flip-flop
    dffas_formal = (SLiteral('C=') + signal_id('C')
                    + SLiteral('R=') + signal_id('R')
                    + SLiteral('D=') + signal_id('D')
                    + SLiteral('Q=') + signal_id('Q'))
    dffas_keyword = SKeyword('$_DFF_PN0_') | SKeyword('$_DFF_PP0_')
    dffas_def = Group(SKeyword('.subckt') + dffas_keyword + dffas_formal)('dffas_def')

    # synchronous Flip-flop
    dffs_def = Group(SKeyword('.latch')
                     + signal_id('D')
                     + signal_id('Q')
                     + SLiteral('re')
                     + signal_id('C'))('dffs_def')
    command_def = name_def | dffas_def | dffs_def
    command_list = Group(OneOrMore(command_def))('command_list')

    footer = SKeyword('.end')
    model_def = Group(header + input_list + output_list + command_list + footer)
    model_list = OneOrMore(model_def)
    parser = model_list.ignore(pyparsing.pythonStyleComment)

    # Begin actually reading and parsing the BLIF file
    result = parser.parseString(blif_string, parseAll=True)
    # Blif file with multiple models (currently only handles one flattened models)
    assert(len(result) == 1)
    clk_set = set([])
    ff_clk_set = set([])

    def extract_inputs(model):
        start_names = [re.sub(r'\[([0-9]+)\]$', '', x) for x in model['input_list']]
        name_counts = collections.Counter(start_names)
        for input_name in name_counts:
            bitwidth = name_counts[input_name]
            if input_name == 'clk':
                clk_set.add(input_name)
            elif not merge_io_vectors or bitwidth == 1:
                block.add_wirevector(wire.Input(bitwidth=1, name=input_name))
            else:
                wire_in = wire.Input(bitwidth=bitwidth, name=input_name, block=block)
                for i in range(bitwidth):
                    bit_name = input_name + '[' + str(i) + ']'
                    bit_wire = wire.WireVector(bitwidth=1, name=bit_name, block=block)
                    bit_wire <<= wire_in[i]

    def extract_outputs(model):
        start_names = [re.sub(r'\[([0-9]+)\]$', '', x) for x in model['output_list']]
        name_counts = collections.Counter(start_names)
        for output_name in name_counts:
            bitwidth = name_counts[output_name]
            if not merge_io_vectors or bitwidth == 1:
                block.add_wirevector(wire.Output(bitwidth=1, name=output_name))
            else:
                wire_out = wire.Output(bitwidth=bitwidth, name=output_name, block=block)
                bit_list = []
                for i in range(bitwidth):
                    bit_name = output_name + '[' + str(i) + ']'
                    bit_wire = wire.WireVector(bitwidth=1, name=bit_name, block=block)
                    bit_list.append(bit_wire)
                wire_out <<= helperfuncs.concat(*bit_list)

    def extract_commands(model):
        # for each "command" (dff or net) in the model
        for command in model['command_list']:
            # if it is a net (specified as a cover)
            if command.getName() == 'name_def':
                extract_cover(command)
            # else if the command is a d flop flop
            elif command.getName() == 'dffas_def' or command.getName() == 'dffs_def':
                extract_flop(command)
            else:
                raise core.PyrtlError('unknown command type')

    def extract_cover(command):
        netio = command['namesignal_list']
        if len(command['cover_list']) == 0:
            output_wire = twire(netio[0])
            output_wire <<= wire.Const(0, bitwidth=1, block=block)  # const "FALSE"
        elif command['cover_list'].asList() == ['1']:
            output_wire = twire(netio[0])
            output_wire <<= wire.Const(1, bitwidth=1, block=block)  # const "TRUE"
        elif command['cover_list'].asList() == ['1', '1']:
            #Populate clock list if one input is already a clock
            if(netio[1] in clk_set):
                clk_set.add(netio[0])
            elif(netio[0] in clk_set):
                clk_set.add(netio[1])
            else:
                output_wire = twire(netio[1])
                output_wire <<= twire(netio[0])  # simple wire
        elif command['cover_list'].asList() == ['0', '1']:
            output_wire = twire(netio[1])
            output_wire <<= ~ twire(netio[0])  # not gate
        elif command['cover_list'].asList() == ['11', '1']:
            output_wire = twire(netio[2])
            output_wire <<= twire(netio[0]) & twire(netio[1])  # and gate
        elif command['cover_list'].asList() == ['1-', '1', '-1', '1']:
            output_wire = twire(netio[2])
            output_wire <<= twire(netio[0]) | twire(netio[1])  # or gate
        elif command['cover_list'].asList() == ['10', '1', '01', '1']:
            output_wire = twire(netio[2])
            output_wire <<= twire(netio[0]) ^ twire(netio[1])  # xor gate
        elif command['cover_list'].asList() == ['1-0', '1', '-11', '1']:
            output_wire = twire(netio[3])
            output_wire <<= (twire(netio[0]) & ~ twire(netio[2])) \
                | (twire(netio[1]) & twire(netio[2]))   # mux
        else:
            raise core.PyrtlError('Blif file with unknown logic cover set '
                                  '(currently gates are hard coded)')

    def extract_flop(command):
        if(command['C'] not in ff_clk_set):
            ff_clk_set.add(command['C'])

        #Create register and assign next state to D and output to Q
        regname = command['Q'] + '_reg'
        flop = wire.Register(bitwidth=1, name=regname)
        flop.next <<= twire(command['D'])
        flop_output = twire(command['Q'])
        flop_output <<= flop

    for model in result:
        extract_inputs(model)
        extract_outputs(model)
        extract_commands(model)


#-----------------------------------------------------------------
#    __       ___  __       ___
#   /  \ |  |  |  |__) |  |  |
#   \__/ \__/  |  |    \__/  |
#

def output_to_trivialgraph(file, block):
    """ Walk the block and output it in trivial graph format to the open file """

    nodes = {}
    edges = set([])
    edge_names = {}
    uid = [1]

    def add_node(x, label):
        nodes[x] = (uid[0], label)
        uid[0] = uid[0] + 1

    def add_edge(frm, to):
        if hasattr(frm, 'name') and not frm.name.startswith('tmp'):
            edge_label = frm.name
        else:
            edge_label = ''
        if frm not in nodes:
            frm = producer(frm)
        if to not in nodes:
            to = consumer(to)
        (frm_id, _) = nodes[frm]
        (to_id, _) = nodes[to]
        edges.add((frm_id, to_id))
        if edge_label:
            edge_names[(frm_id, to_id)] = edge_label

    def producer(w):
        """ return the node driving wire (or create it if undefined) """
        assert isinstance(w, wire.WireVector)
        for net in sorted(block.logic):
            for dest in sorted(net.dests):
                if dest == w:
                    return net
        add_node(w, '???')
        return w

    def consumer(w):
        """ return the node being driven by wire (or create it if undefined) """
        assert isinstance(w, wire.WireVector)
        for net in sorted(block.logic):
            for arg in sorted(net.args):
                if arg == w:
                    return net
        add_node(w, '???')
        return w

    # add all of the nodes
    for net in sorted(block.logic):
        label = str(net.op)
        label += str(net.op_param) if net.op_param is not None else ''
        add_node(net, label)
    for input in sorted(block.wirevector_subset(wire.Input)):
        label = 'in' if input.name is None else input.name
        add_node(input, label)
    for output in sorted(block.wirevector_subset(wire.Output)):
        label = 'out' if output.name is None else output.name
        add_node(output, label)
    for const in sorted(block.wirevector_subset(wire.Const)):
        label = str(const.val)
        add_node(const, label)

    # add all of the edges
    for net in sorted(block.logic):
        for arg in sorted(net.args):
            add_edge(arg, net)
        for dest in sorted(net.dests):
            add_edge(net, dest)

    # print the actual output to the file
    for (id, label) in sorted(nodes.values()):
        print >> file, id, label
    print >> file, '#'
    for (frm, to) in sorted(edges):
        print >> file, frm, to, edge_names.get((frm, to), '')

#-----------------------------------------------------------------
#         ___  __          __   __
#   \  / |__  |__) | |    /  \ / _`
#    \/  |___ |  \ | |___ \__/ \__>
#


def _verilog_vector_decl(w):
    return '' if len(w) == 1 else '[%d:0]' % (len(w) - 1)


def _to_verilog_header(file, block):
    io_list = [w.name for w in block.wirevector_subset((wire.Input, wire.Output))]
    io_list.append('clk')
    io_list_str = ', '.join(io_list)
    print >> file, 'module toplevel(%s);' % io_list_str

    inputs = block.wirevector_subset(wire.Input)
    outputs = block.wirevector_subset(wire.Output)
    registers = block.wirevector_subset(wire.Register)
    wires = block.wirevector_subset() - (inputs | outputs | registers)
    for w in inputs:
        print >> file, '    input%s %s;' % (_verilog_vector_decl(w), w.name)
    for w in outputs:
        print >> file, '    output%s %s;' % (_verilog_vector_decl(w), w.name)
    print >> file, ''

    for w in registers:
        print >> file, '    reg%s %s;' % (_verilog_vector_decl(w), w.name)
    for w in wires:
        print >> file, '    wire%s %s;' % (_verilog_vector_decl(w), w.name)
    print >> file, ''


def _to_verilog_combinational(file, block):
    for const in block.wirevector_subset(wire.Const):
            print >> file, '    assign %s = %d;' % (const.name, const.val)

    for net in block.logic:
        if net.op in set('w~'):  # unary ops
            opstr = '' if net.op == 'w' else net.op
            t = (net.dests[0].name, opstr, net.args[0].name)
            print >> file, '    assign %s = %s%s;' % t
        elif net.op in '&|^+-*<>':  # binary ops
            t = (net.dests[0].name, net.args[0].name, net.op, net.args[1].name)
            print >> file, '    assign %s = %s %s %s;' % t
        elif net.op == '=':
            t = (net.dests[0].name, net.args[0].name, net.args[1].name)
            print >> file, '    assign %s = %s == %s;' % t
        elif net.op == 'x':
            # note that the argument order for 'x' is backwards from the ternary operator
            t = (net.dests[0].name, net.args[0].name, net.args[2].name, net.args[1].name)
            print >> file, '    assign %s = %s ? %s : %s;' % t
        elif net.op == 'c':
            catlist = ', '.join([w.name for w in net.args])
            t = (net.dests[0].name, catlist)
            print >> file, '    assign %s = {%s};' % t
        elif net.op == 's':
            catlist = ', '.join([net.args[0].name+'['+str(i)+']' for i in net.op_param])
            t = (net.dests[0].name, catlist)
            print >> file, '    assign %s = {%s};' % t
        elif net.op == 'r':
            pass  # do nothing for registers
        elif net.op == 'm':
            raise NotImplementedError('Memories are not supported by output_to_verilog currently')
        else:
            raise core.PyrtlInternalError
    print >> file, ''


def _to_verilog_sequential(file, block):
    print >> file, '    always @( posedge clk )'
    print >> file, '    begin'
    for net in block.logic:
        if net.op == 'r':
            t = (net.dests[0].name, net.args[0].name)
            print >> file, '        %s <= %s;' % t
    print >> file, '    end'


def _to_verilog_footer(file, block):
    print >> file, 'endmodule\n'


def output_to_verilog(file, block=None):
    """ Walk the block and output it in verilog format to the open file """

    block = core.working_block(block)
    _to_verilog_header(file, block)
    _to_verilog_combinational(file, block)
    _to_verilog_sequential(file, block)
    _to_verilog_footer(file, block)
