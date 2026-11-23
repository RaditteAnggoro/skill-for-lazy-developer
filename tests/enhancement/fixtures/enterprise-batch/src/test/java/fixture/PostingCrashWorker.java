package fixture;

import java.sql.DriverManager;

/** Separate synthetic JVM. The nonce must exist in the disposable database before writes. */
public class PostingCrashWorker {
    public static void main(String[] args) throws Exception {
        if (args.length != 3 || !(args[2].equals("before") || args[2].equals("after"))) {
            throw new IllegalArgumentException("expected fixture port, nonce and boundary");
        }
        int port = Integer.parseInt(args[0]);
        try (var connection = DriverManager.getConnection("jdbc:postgresql://127.0.0.1:" + port + "/postgres", "postgres", "")) {
            try (var guard = connection.prepareStatement("SELECT token FROM synthetic_fixture_guard WHERE token = ?")) {
                guard.setString(1, args[1]);
                try (var rows = guard.executeQuery()) {
                    if (!rows.next()) throw new IllegalStateException("fixture nonce mismatch");
                }
            }
            connection.setAutoCommit(false);
            try (var statement = connection.createStatement()) {
                statement.execute("SELECT post_financial_claim('crash', 'worker', 1, repeat('a', 64))");
                if (args[2].equals("before")) Runtime.getRuntime().halt(81);
                connection.commit();
                Runtime.getRuntime().halt(82);
            }
        }
    }
}
