# Closed Java source bridge

The bridge consumes complete Service.java, not a producer-selected excerpt.
JavacTask parses every declaration and statement before type analysis inserts
an implicit constructor. The consumer reconstructs BFIL independently of the
submitted evidence and invokes the existing independent source checker.
Neither the frontend nor the checking CLI executes supplied Java.

The grammar is one public final Service class: no package, imports, fields,
nesting, initializers, explicit constructors, superclasses or interfaces.
Methods are zero-argument void instance methods with unique simple names and
no annotations, throws clauses or type parameters. Public run is the entry.
Bodies admit only literal Permission.enforce calls, declared same-receiver
calls, or terminal void return. The entire call graph must be acyclic,
including unreachable methods. Every other construct rejects rather than
silently disappearing. See JavaSubsetFront.java for the exact grammar.

Bounds are 32,768 ASCII bytes without Unicode escapes, 128 methods, 1,024
statements, plus unchanged core source and ground bounds. Original argument
spans must spell a simple permission literal, preventing JDK constant folding
from hiding unsupported concatenation. Empty methods are allowed; the core
schema requires a nonempty permission inventory. Source spans, unreachable
methods and zero-effect returns remain inventoried.

Under normal execution, each method's event set is the union of its literal
events and callees' sets. Acyclic induction relates Java execution to BFIL
reachable checks, as proved in the supplement. This does not model VM resource
failure, asynchronous interruption, event order/multiplicity or real Android
enforcement. The installed JDK parser/type checker, profile mapping and owned
Permission event primitive are trusted; none is claimed machine-verified.

## Reproduce and check

Use Python 3.12+ and an installed JDK 17+ through JAVA_HOME or PATH:

    python -B -m unittest discover -s tests/java_bridge -v
    python -B -O -m unittest discover -s tests/java_bridge -v
    python -B run_java_bridge.py --out /fresh/private/java-run --compare results/java-bridge
    python -B export_java_table.py

The native study compiles/runs only eight frozen owned Java fixtures, never
AOSP or arbitrary external code. Both revisions contain P_A and P_B literals;
a newly reachable call changes native events. Eight native runs agree with
direct BFIL and Horn projections; four old projections reject on revised
complete Java even though old-program proofs remain valid.
No speedup, real-framework coverage or production deployment follows.

The compressed records retain exact source text, projections, full evidence,
observed events and counters. The table consumer checks source/record/BFIL
consistency; only native replay re-executes the logger. CI explicitly runs both
JDK test modes, native comparison and the consumer. Existing gates remain.

To validate plain JSON BFIL evidence against a complete source without running
that source:

    python -B check_java_framework.py --source /path/Service.java --evidence /path/evidence.json

Exit 0 accepts, 1 rejects evidence, and 2 rejects profile/input or reports a
setup error. Parsing and each native subprocess have 30-second timeouts.
The checker itself trusts the core finite bounds and is not a hostile-input
service or a general Java verifier.

Primary API and language documentation:

- https://docs.oracle.com/en/java/javase/17/docs/api/jdk.compiler/com/sun/source/util/JavacTask.html
- https://docs.oracle.com/javase/specs/jls/se17/html/jls-15.html#jls-15.12.4
