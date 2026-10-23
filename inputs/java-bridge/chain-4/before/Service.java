// Owned, complete Java unit; Permission is the specified event primitive.
public final class Service {
    public void run() {
        this.step1();
    }
    private void step1() {
        this.step2();
    }
    private void step2() {
        this.step3();
    }
    private void step3() {
        Permission.enforce("P_A");
    }
    private void dormant() { Permission.enforce("P_B"); }
}
