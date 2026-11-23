import com.sun.source.tree.*;
import com.sun.source.util.JavacTask;
import com.sun.source.util.TreeScanner;
import com.sun.source.util.Trees;
import javax.lang.model.element.Modifier;
import javax.tools.Diagnostic;
import javax.tools.DiagnosticCollector;
import javax.tools.JavaFileObject;
import javax.tools.ToolProvider;
import java.nio.charset.StandardCharsets;
import java.util.*;
import java.util.function.Predicate;

/** Parse explicit Java sources without attribution, annotation processing, or execution. */
class FinancialJavaScan {
    private static final Set<String> WRITES = Set.of("insert", "save", "update", "persist", "executeUpdate", "batchUpdate");
    private static final Set<String> LOOKUPS = Set.of("exists", "existsById", "findById", "findByKey", "lookup", "count");
    private static final Set<String> RESOURCES = Set.of("getConnection", "createStatement", "prepareStatement", "executeQuery");

    public static void main(String[] files) throws Exception {
        var compiler = ToolProvider.getSystemJavaCompiler();
        var diagnostics = new DiagnosticCollector<JavaFileObject>();
        try (var manager = compiler.getStandardFileManager(diagnostics, Locale.ROOT, StandardCharsets.UTF_8)) {
            String release = Runtime.version().feature() >= 21 ? "21" : "17";
            var task = (JavacTask) compiler.getTask(null, manager, diagnostics, List.of("-proc:none", "--release", release),
                null, manager.getJavaFileObjectsFromStrings(List.of(files)));
            var units = new ArrayList<CompilationUnitTree>();
            task.parse().forEach(units::add);
            if (diagnostics.getDiagnostics().stream().anyMatch(item -> item.getKind() == Diagnostic.Kind.ERROR)) {
                System.err.println("Java parse error in specified source");
                System.exit(2);
            }
            for (var unit : units) new Analyze(unit, Trees.instance(task)).scan(unit, null);
        }
    }

    private static String simple(String value) {
        return value.substring(value.lastIndexOf('.') + 1);
    }

    private static String name(ExpressionTree expression) {
        if (expression instanceof IdentifierTree id) return id.getName().toString();
        if (expression instanceof MemberSelectTree member) return member.getIdentifier().toString();
        return "";
    }

    private static boolean anyCall(Tree tree, Predicate<String> condition) {
        boolean[] matched = {false};
        new TreeScanner<Void, Void>() {
            @Override public Void visitMethodInvocation(MethodInvocationTree node, Void unused) {
                if (condition.test(name(node.getMethodSelect()))) matched[0] = true;
                return super.visitMethodInvocation(node, unused);
            }
            @Override public Void visitClass(ClassTree node, Void unused) { return null; }
            @Override public Void visitLambdaExpression(LambdaExpressionTree node, Void unused) { return null; }
        }.scan(tree, null);
        return matched[0];
    }

    private static AnnotationTree transaction(ModifiersTree modifiers) {
        return modifiers.getAnnotations().stream()
            .filter(annotation -> simple(annotation.getAnnotationType().toString()).equals("Transactional"))
            .findFirst().orElse(null);
    }

    private static ExpressionTree argument(AnnotationTree annotation, String name) {
        if (annotation != null) {
            for (var expression : annotation.getArguments()) {
                if (expression instanceof AssignmentTree pair && pair.getVariable().toString().equals(name)) {
                    return pair.getExpression();
                }
            }
        }
        return null;
    }

    private static boolean floating(ExpressionTree node) {
        if (node instanceof LiteralTree literal) return literal.getValue() instanceof Double || literal.getValue() instanceof Float;
        if (node instanceof UnaryTree unary) return floating(unary.getExpression());
        if (node instanceof ParenthesizedTree parens) return floating(parens.getExpression());
        return false;
    }

    private static class Analyze extends TreeScanner<Void, Void> {
        private final CompilationUnitTree unit;
        private final Trees trees;
        private ClassTree owner;

        Analyze(CompilationUnitTree unit, Trees trees) { this.unit = unit; this.trees = trees; }

        @Override public Void visitClass(ClassTree tree, Void unused) {
            var previous = owner;
            owner = tree;
            try { return super.visitClass(tree, unused); } finally { owner = previous; }
        }

        @Override public Void visitMethod(MethodTree method, Void unused) {
            if (method.getBody() == null || owner == null) return null;
            Set<String> siblingTransactions = new HashSet<>();
            for (var member : owner.getMembers()) {
                if (member instanceof MethodTree sibling && transaction(sibling.getModifiers()) != null) {
                    siblingTransactions.add(sibling.getName().toString());
                }
            }
            new MethodCheck(unit, trees, method, transaction(owner.getModifiers()), siblingTransactions).run();
            return null;
        }
    }

    private static class MethodCheck extends TreeScanner<Void, Void> {
        private final CompilationUnitTree unit;
        private final Trees trees;
        private final MethodTree method;
        private final AnnotationTree declaration, inherited;
        private final Set<String> siblings;
        private final Set<Tree> managed = new HashSet<>();
        private int writes;

        MethodCheck(CompilationUnitTree unit, Trees trees, MethodTree method, AnnotationTree inherited, Set<String> siblings) {
            this.unit = unit;
            this.trees = trees;
            this.method = method;
            this.declaration = transaction(method.getModifiers());
            this.inherited = inherited;
            this.siblings = siblings;
        }

        private void report(String rule, Tree tree) {
            long position = trees.getSourcePositions().getStartPosition(unit, tree);
            if (position < 0) return;
            long line = unit.getLineMap().getLineNumber(position);
            System.out.printf("%s\t%s\t%d\t%s%n", rule, unit.getSourceFile().toUri(), line, method.getName());
        }

        void run() {
            AnnotationTree effective = declaration == null ? inherited : declaration;
            var flags = method.getModifiers().getFlags();
            if (effective != null && (flags.contains(Modifier.PRIVATE) || flags.contains(Modifier.STATIC)
                || (declaration != null && flags.contains(Modifier.FINAL)))) report("JAVA_PROXY_VISIBILITY", method);
            if (effective != null && argument(effective, "rollbackFor") == null && argument(effective, "rollbackForClassName") == null
                && method.getThrows().stream()
                .anyMatch(type -> Set.of("IOException", "SQLException", "Exception").contains(simple(type.toString())))) {
                report("JAVA_CHECKED_ROLLBACK", method);
            }
            if (name(argument(effective, "propagation")).equals("REQUIRES_NEW")) {
                report("JAVA_REQUIRES_NEW", method);
            }
            scan(method.getBody(), null);
            if (effective == null && financialMethod() && writes > 1) report("JAVA_SPLIT_WRITES", method);
        }

        private boolean financialMethod() {
            return method.getName().toString().matches("(?i).*(write|post|process|persist|reconcile|claim).*");
        }

        @Override public Void visitMethodInvocation(MethodInvocationTree node, Void unused) {
            var select = node.getMethodSelect();
            String called = name(select);
            boolean self = select instanceof IdentifierTree || (select instanceof MemberSelectTree member
                && member.getExpression() instanceof IdentifierTree target && target.getName().contentEquals("this"));
            if (self && siblings.contains(called)) report("JAVA_SELF_INVOCATION", node);
            if (WRITES.contains(called)) writes++;
            boolean broadException = node.getArguments().stream().anyMatch(arg -> arg instanceof MemberSelectTree member
                && member.getIdentifier().contentEquals("class") && Set.of("Exception", "Throwable").contains(simple(member.getExpression().toString())));
            if (((called.equals("skip") || called.equals("retry")) && broadException) || called.equals("noRollback")) {
                report("JAVA_BATCH_POLICY", node);
            }
            if (financialMethod() && Set.of("findAll", "readAllBytes").contains(called) && node.getArguments().isEmpty()) {
                report("JAVA_UNBOUNDED_READ", node);
            }
            return super.visitMethodInvocation(node, unused);
        }

        @Override public Void visitIf(IfTree node, Void unused) {
            if (anyCall(node.getCondition(), LOOKUPS::contains)
                && (anyCall(node.getThenStatement(), WRITES::contains) || anyCall(node.getElseStatement(), WRITES::contains))) {
                report("JAVA_CHECK_INSERT", node);
            }
            return super.visitIf(node, unused);
        }

        @Override public Void visitCatch(CatchTree node, Void unused) {
            if ((financialMethod() || declaration != null) && node.getBlock().getStatements().stream()
                    .noneMatch(statement -> statement instanceof ThrowTree)) report("JAVA_SWALLOWED_WRITE", node);
            return super.visitCatch(node, unused);
        }

        @Override public Void visitNewClass(NewClassTree node, Void unused) {
            if (simple(node.getIdentifier().toString()).equals("BigDecimal") && !node.getArguments().isEmpty()
                    && floating(node.getArguments().get(0))) report("JAVA_DECIMAL_FLOAT", node);
            return super.visitNewClass(node, unused);
        }

        @Override public Void visitTry(TryTree node, Void unused) {
            managed.addAll(node.getResources());
            return super.visitTry(node, unused);
        }

        @Override public Void visitVariable(VariableTree node, Void unused) {
            if (!managed.contains(node) && node.getInitializer() instanceof MethodInvocationTree call
                    && RESOURCES.contains(name(call.getMethodSelect()))) report("JAVA_RESOURCE", node);
            return super.visitVariable(node, unused);
        }

        @Override public Void visitClass(ClassTree node, Void unused) { return null; }
        @Override public Void visitLambdaExpression(LambdaExpressionTree node, Void unused) { return null; }
    }
}
