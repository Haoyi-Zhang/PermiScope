import com.sun.source.tree.*;
import com.sun.source.util.*;
import java.nio.charset.StandardCharsets;
import java.nio.file.*;
import java.util.*;
import javax.lang.model.element.Modifier;
import javax.lang.model.type.TypeKind;
import javax.tools.*;

/**
 * Closed Java source profile for owned permission-reachability examples.
 * Parses the complete unit and checks types with the installed JDK compiler.
 * No supplied program is executed. Annotation processing is disabled.
 */
public final class JavaSubsetFront {
    static void require(boolean condition, String reason) {
        if (!condition) throw new IllegalArgumentException(reason);
    }
    static Map<String,Object> object(Object... pairs) {
        Map<String,Object> result = new LinkedHashMap<>();
        for (int i=0;i<pairs.length;i+=2) result.put((String)pairs[i],pairs[i+1]);
        return result;
    }
    static String json(Object value) {
        if (value==null) return "null";
        if (value instanceof String text) {
            StringBuilder out = new StringBuilder("\"");
            for (char c:text.toCharArray()) {
                switch(c) {
                    case '"': out.append("\\\""); break;
                    case '\\': out.append("\\\\"); break;
                    case '\n': out.append("\\n"); break;
                    case '\r': out.append("\\r"); break;
                    case '\t': out.append("\\t"); break;
                    default:
                        if (c<32 || c>126) out.append(String.format("\\u%04x",(int)c));
                        else out.append(c);
                }
            }
            return out.append('"').toString();
        }
        if (value instanceof Number || value instanceof Boolean) return value.toString();
        if (value instanceof Map<?,?> map) {
            List<String> parts = new ArrayList<>();
            for (var e:map.entrySet()) parts.add(json(e.getKey())+":"+json(e.getValue()));
            return "{"+String.join(",",parts)+"}";
        }
        if (value instanceof Collection<?> items) {
            List<String> parts = new ArrayList<>();
            for (Object item:items) parts.add(json(item));
            return "["+String.join(",",parts)+"]";
        }
        throw new IllegalArgumentException("unsupported serializer object");
    }
    static void modifiers(ModifiersTree mods, Set<Modifier> allowed) {
        require(mods.getAnnotations().isEmpty() && allowed.containsAll(mods.getFlags()),
                "unsupported modifiers or annotations");
    }
    static boolean word(String name) {
        return name.matches("[A-Za-z][A-Za-z0-9_]{0,31}");
    }
    static void acyclic(String name, Map<String,Set<String>> calls, Set<String> gray,
                        Set<String> black) {
        require(!gray.contains(name),"recursive call graph is outside profile");
        if (black.contains(name)) return;
        gray.add(name);
        for (String target:calls.get(name)) acyclic(target,calls,gray,black);
        gray.remove(name);
        black.add(name);
    }
    static Map<String,Object> translate(JavacTask task, CompilationUnitTree unit) {
        String sourceText;
        try { sourceText=unit.getSourceFile().getCharContent(true).toString(); }
        catch (java.io.IOException error) { throw new IllegalArgumentException("unreadable source"); }
        require(unit.getPackageName()==null && unit.getImports().isEmpty()
                && unit.getModule()==null && unit.getTypeDecls().size()==1,
                "one class, no package/import/module");
        require(unit.getTypeDecls().get(0) instanceof ClassTree,"class required");
        ClassTree cls = (ClassTree)unit.getTypeDecls().get(0);
        require(cls.getKind()==Tree.Kind.CLASS && cls.getSimpleName().contentEquals("Service")
                && cls.getExtendsClause()==null && cls.getImplementsClause().isEmpty()
                && cls.getTypeParameters().isEmpty() && cls.getPermitsClause().isEmpty(),
                "final Service class profile");
        modifiers(cls.getModifiers(),Set.of(Modifier.PUBLIC,Modifier.FINAL));
        require(cls.getModifiers().getFlags().containsAll(Set.of(Modifier.PUBLIC, Modifier.FINAL)),
                "public final class required");
        require(cls.getMembers().size()>=1 && cls.getMembers().size()<=128,
                "method count bound");
        Map<String,MethodTree> declarations = new LinkedHashMap<>();
        for (Tree member:cls.getMembers()) {
            require(member instanceof MethodTree,"fields, constructors and nested types unsupported");
            MethodTree method = (MethodTree)member;
            String name=method.getName().toString();
            require(word(name) && !declarations.containsKey(name),"unique simple method name");
            modifiers(method.getModifiers(),Set.of(Modifier.PUBLIC,Modifier.PRIVATE,Modifier.FINAL));
            require(method.getReturnType() instanceof PrimitiveTypeTree
                    && ((PrimitiveTypeTree)method.getReturnType()).getPrimitiveTypeKind()==TypeKind.VOID
                    && method.getParameters().isEmpty() && method.getTypeParameters().isEmpty()
                    && method.getReceiverParameter()==null && method.getThrows().isEmpty()
                    && method.getDefaultValue()==null && method.getBody()!=null,
                    "void zero-argument instance method required");
            declarations.put(name,method);
        }
        require(declarations.containsKey("run")
                && declarations.get("run").getModifiers().getFlags().contains(Modifier.PUBLIC),
                "public run entry required");
        SourcePositions positions=Trees.instance(task).getSourcePositions();
        Set<String> permissions=new TreeSet<>();
        Map<String,Set<String>> calls=new LinkedHashMap<>();
        List<Object> methods=new ArrayList<>();
        int statements=0;
        for (var declaration:declarations.entrySet()) {
            String name=declaration.getKey();
            MethodTree method=declaration.getValue();
            List<Object> body=new ArrayList<>();
            Set<String> edges=new TreeSet<>();
            calls.put(name,edges);
            List<? extends StatementTree> sourceBody=method.getBody().getStatements();
            for (int index=0;index<sourceBody.size();index++) {
                require(++statements<=1024,"statement count bound");
                StatementTree statement=sourceBody.get(index);
                Map<String,Object> effect;
                if (statement instanceof ReturnTree returned) {
                    require(returned.getExpression()==null && index==sourceBody.size()-1,
                            "only terminal void return supported");
                    effect=object("op","return","src",null);
                } else {
                    require(statement instanceof ExpressionStatementTree,
                            "unsupported statement kind");
                    ExpressionTree expression=((ExpressionStatementTree)statement).getExpression();
                    require(expression instanceof MethodInvocationTree,"only method calls supported");
                    MethodInvocationTree call=(MethodInvocationTree)expression;
                    require(call.getTypeArguments().isEmpty(),"generic calls unsupported");
                    ExpressionTree select=call.getMethodSelect();
                    if (select instanceof MemberSelectTree target
                            && target.getExpression() instanceof IdentifierTree owner
                            && owner.getName().contentEquals("Permission")
                            && target.getIdentifier().contentEquals("enforce")) {
                        require(call.getArguments().size()==1
                                && call.getArguments().get(0) instanceof LiteralTree,
                                "permission string literal required");
                        Object literal=((LiteralTree)call.getArguments().get(0)).getValue();
                        require(literal instanceof String && ((String)literal).matches("P_[A-Z0-9_]{1,24}"),
                                "permission literal profile");
                        Tree argument=call.getArguments().get(0);
                        long a=positions.getStartPosition(unit,argument);
                        long z=positions.getEndPosition(unit,argument);
                        require(a>=0 && z>a && z<=sourceText.length()
                                && sourceText.substring((int)a,(int)z).equals("\""+literal+"\""),
                                "single plain permission literal required");
                        permissions.add((String)literal);
                        effect=object("op","check","permission",literal);
                    } else {
                        String targetName;
                        if (select instanceof IdentifierTree target) targetName=target.getName().toString();
                        else {
                            require(select instanceof MemberSelectTree,"unsupported call target");
                            MemberSelectTree target=(MemberSelectTree)select;
                            require(target.getExpression() instanceof IdentifierTree
                                    && ((IdentifierTree)target.getExpression()).getName().contentEquals("this"),
                                    "only this receiver supported");
                            targetName=target.getIdentifier().toString();
                        }
                        require(call.getArguments().isEmpty() && declarations.containsKey(targetName),
                                "unknown or nonzero-argument method");
                        edges.add(targetName);
                        effect=object("op","invoke","dst",null,"recv","this",
                                      "selector",targetName,"args",List.of());
                    }
                }
                long start=positions.getStartPosition(unit,statement);
                long end=positions.getEndPosition(unit,statement);
                require(start>=0 && end>start,"source positions required");
                Map<String,Object> row=object("id","Service:"+name+":"+index,
                    "span",object("unit","Service.java",
                        "start_line",unit.getLineMap().getLineNumber(start),
                        "end_line",unit.getLineMap().getLineNumber(end-1)));
                row.putAll(effect);
                body.add(row);
            }
            methods.add(object("name",name,"params",List.of(),"returns",null,
                               "locals",List.of(),"body",body));
        }
        Set<String> black=new HashSet<>();
        for (String name:declarations.keySet()) acyclic(name,calls,new HashSet<>(),black);
        Map<String,Object> document=object("language","bfil-1","permissions",permissions,
            "classes",List.of(object("name","Service","super",null,"fields",List.of(),"methods",methods)),
            "services",List.of(object("name","service","declared_class","Service",
                                      "implementation_class","Service")),
            "entries",List.of(object("name","API","service","service","selector","run",
                                    "arg_classes",List.of())));
        return object("document",document,"inventory",object("methods",methods.size(),
                      "statements",statements,"method_names",declarations.keySet()));
    }
    public static void main(String[] args) throws Exception {
        try {
            require(args.length==2,"complete source and trusted Permission.java required");
            Path source=Path.of(args[0]);
            require(source.getFileName().toString().equals("Service.java"),"Service.java filename required");
            require(Files.size(source)<=32768,"source byte bound");
            String text=Files.readString(source,StandardCharsets.UTF_8);
            require(text.chars().allMatch(c->c<128) && !text.contains("\\u"),
                    "ASCII source without Unicode escapes required");
            JavaCompiler compiler=ToolProvider.getSystemJavaCompiler();
            require(compiler!=null,"JDK compiler required");
            DiagnosticCollector<JavaFileObject> diagnostics=new DiagnosticCollector<>();
            try (StandardJavaFileManager manager=compiler.getStandardFileManager(
                    diagnostics,Locale.ROOT,StandardCharsets.UTF_8)) {
                var files=manager.getJavaFileObjectsFromPaths(List.of(source,Path.of(args[1])));
                JavacTask task=(JavacTask)compiler.getTask(null,manager,diagnostics,
                    List.of("-proc:none","--release","17","-encoding","UTF-8"),null,files);
                CompilationUnitTree unit=null;
                for (CompilationUnitTree parsed:task.parse())
                    if (Path.of(parsed.getSourceFile().toUri()).equals(source.toAbsolutePath())) unit=parsed;
                require(unit!=null,"complete source unit not parsed");
                // Inspect original syntax before javac inserts a default constructor.
                Map<String,Object> output=translate(task,unit);
                task.analyze();
                for (Diagnostic<?> diagnostic:diagnostics.getDiagnostics())
                    require(diagnostic.getKind()!=Diagnostic.Kind.ERROR,"javac type/syntax error");
                System.out.println(json(output));
            }
        } catch (IllegalArgumentException error) {
            System.err.println("PROFILE_REJECT: "+error.getMessage());
            System.exit(2);
        }
    }
}
