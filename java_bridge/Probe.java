/** Executes only reviewed owned Service fixtures selected by the study driver. */
public final class Probe {
    public static void main(String[] args) {
        new Service().run();
        for (String name:Permission.observed) System.out.println(name);
    }
}
