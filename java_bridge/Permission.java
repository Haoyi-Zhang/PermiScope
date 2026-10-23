/** Trusted event primitive for reviewed owned fixtures, not Android enforcement. */
final class Permission {
    static final java.util.SortedSet<String> observed=new java.util.TreeSet<>();
    static void enforce(String name) { observed.add(name); }
}
