// Owned, complete Java unit; Permission is the specified event primitive.
public final class Service {
    public void run() {
        Permission.enforce("P_A");
    }
    private void dormant() { Permission.enforce("P_B"); }
}
