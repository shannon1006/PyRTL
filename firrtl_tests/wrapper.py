import pyrtl
from pyrtl import Input, Output, Register

# can specify if using sim_trace or sim_values for simulation values
# by using sim_trace, you can take a sim_trace directly from pyrtl simulation
# by using sim_values,  you can provide your own simulation value
# sim_values should be a dict where the key is the input/output/register name and the value is a list of simulation
# values.
def wrap_firrtl_test(working_block, firrtl_str, test_name, firrtl_test_path, sim_values=None, sim_trace=None):
    inputs = working_block.wirevector_subset(Input)
    outputs = working_block.wirevector_subset(Output)
    registers = working_block.wirevector_subset(Register)

    wrapper_str = "package firrtl_interpreter\n"
    wrapper_str += "import org.scalatest.{FlatSpec, Matchers}\n"
    wrapper_str += "class " + test_name + " extends FlatSpec with Matchers {\n"
    wrapper_str += "\tval firrtlStr: String =\n"
    wrapper_str += "\"\"\"\n"
    wrapper_str += firrtl_str
    wrapper_str += "\"\"\".stripMargin\n"
    wrapper_str += "\tit should \"run with InterpretedTester\" in {\n"

    wrapper_str += "\t\tval tester = new InterpretiveTester(firrtlStr)\n"
    wrapper_str += "\t\ttester.poke(\"reset\", 1)\n"
    wrapper_str += "\t\ttester.step(1)\n"
    wrapper_str += "\t\ttester.poke(\"reset\", 0)\n"

    for v in inputs.union(outputs).union(registers):
        if sim_trace != None:
            wrapper_str += "\t\tvar " + v.name + " = List(" + ",".join(
                [str(sim_trace.trace[v.name][i]) for i in range(len(sim_trace))]) + ")\n"
            wrapper_str += "\t\tfor (i <- 0 to " + str(len(sim_trace)) + " - 1) {\n"
        else:
            sim_length = len(sim_values[v.name])
            wrapper_str += "\t\tvar " + v.name + " = List(" + ",".join(
                [str(sim_values[v.name][i]) for i in range(sim_length)]) + ")\n"
            wrapper_str += "\t\tfor (i <- 0 to " + str(sim_length) + " - 1) {\n"

    wrapper_str += "\t\t\tprint(\"round \" + i + \"\\n\")\n"

    for i in inputs:
        wrapper_str += "\t\t\ttester.poke(\"" + i.name + "\", " + i.name + "(i))\n"

    for o in outputs:
        wrapper_str += "\t\t\ttester.expect(\"" + o.name + "\", " + o.name + "(i))\n"

    for r in registers:
        wrapper_str += "\t\t\ttester.expect(\"" + r.name + "\", " + r.name + "(i))\n"

    wrapper_str += "\t\t\ttester.step(1)\n"
    wrapper_str += "\t\t}\n"

    wrapper_str += "\t}\n"
    wrapper_str += "}\n"

    with open(firrtl_test_path + test_name + ".scala", "w") as f:
        f.write(wrapper_str)